"""Snapshot module.

Commits each full pipeline experiment (generate → formalize → verify) as a
deterministic, replayable Git commit on a dedicated branch.  Every experiment
gets its own directory under `experiments/<id>/` containing:
  - experiment.json  — full metadata
  - conjecture.txt   — natural-language statement
  - conjecture.lean  — Lean 4 source (if formalized)
  - proof.lean       — final proof (if proved)
"""

from __future__ import annotations

import json
import logging
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import git

from src.settings import Settings

# Module-level lock serializes the symbolic_ref HEAD swap across all threads in
# this process.  Celery runs workers as separate processes, so this protects the
# --concurrency=2 threads within a single worker.
_COMMIT_LOCK = threading.Lock()

logger = logging.getLogger(__name__)


def _utc_now_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


class SnapshotManager:
    """Manages Git-based experiment snapshots for full reproducibility."""

    def __init__(
        self,
        repo_path: str | Path = ".",
        settings: Settings | None = None,
    ) -> None:
        self._settings = settings or Settings()
        self._repo_path = Path(repo_path).resolve()
        self._repo = git.Repo(str(self._repo_path))
        self._branch_name = self._settings.git_experiments_branch
        self._experiments_dir = self._repo_path / "experiments"
        self._experiments_dir.mkdir(exist_ok=True)
        self._ensure_branch()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def commit_experiment(
        self,
        experiment_id: str,
        domain: str,
        conjecture: str,
        lean_code: str,
        is_valid: bool,
        proved: bool,
        final_proof: str | None,
        model_used: str,
        duration_ms: int,
        extra: dict[str, Any] | None = None,
    ) -> str:
        """Persist a full experiment as a Git commit.

        Args:
            experiment_id: Unique experiment identifier (UUID).
            domain: Mathematical domain.
            conjecture: Natural-language conjecture statement.
            lean_code: Lean 4 source produced by the formalizer.
            is_valid: Whether the Lean 4 code compiled successfully.
            proved: Whether an automated proof was found.
            final_proof: The successful proof code, or None.
            model_used: Claude model identifier used for this run.
            duration_ms: Total pipeline duration in milliseconds.
            extra: Optional additional metadata to merge into experiment.json.

        Returns:
            The hex SHA of the created Git commit.
        """
        timestamp = _utc_now_iso()
        metadata: dict[str, Any] = {
            "id": experiment_id,
            "timestamp": timestamp,
            "model_used": model_used,
            "domain": domain,
            "conjecture": conjecture,
            "lean_code": lean_code,
            "is_valid": is_valid,
            "proved": proved,
            "final_proof": final_proof,
            "duration_ms": duration_ms,
        }
        if extra:
            metadata.update(extra)

        exp_dir = self._experiments_dir / experiment_id
        exp_dir.mkdir(parents=True, exist_ok=True)

        self._write_experiment_files(exp_dir, metadata)
        sha = self._commit_to_branch(experiment_id, timestamp)

        logger.info(
            "Experiment %s committed as %s on branch %s",
            experiment_id,
            sha,
            self._branch_name,
        )
        return sha

    def list_experiments(self) -> list[dict[str, Any]]:
        """Return metadata for all committed experiments, newest first."""
        results: list[dict[str, Any]] = []
        if not self._experiments_dir.exists():
            return results
        for json_path in sorted(
            self._experiments_dir.glob("*/experiment.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        ):
            try:
                data = json.loads(json_path.read_text(encoding="utf-8"))
                results.append(data)
            except (json.JSONDecodeError, OSError) as exc:
                logger.warning("Could not read %s: %s", json_path, exc)
        return results

    def get_experiment(self, experiment_id: str) -> dict[str, Any] | None:
        """Return full metadata for a single experiment, or None if not found."""
        json_path = self._experiments_dir / experiment_id / "experiment.json"
        if not json_path.exists():
            return None
        try:
            return json.loads(json_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            logger.error("Could not read experiment %s: %s", experiment_id, exc)
            return None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _ensure_branch(self) -> None:
        """Create the experiments branch if it does not already exist."""
        try:
            self._repo.git.rev_parse("--verify", self._branch_name)
            logger.debug("Branch %s already exists", self._branch_name)
        except git.GitCommandError:
            logger.info("Creating branch %s", self._branch_name)
            self._repo.git.branch(self._branch_name)

    def _write_experiment_files(self, exp_dir: Path, metadata: dict[str, Any]) -> None:
        (exp_dir / "experiment.json").write_text(
            json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        (exp_dir / "conjecture.txt").write_text(
            metadata.get("conjecture", ""), encoding="utf-8"
        )
        lean_code = metadata.get("lean_code", "")
        if lean_code:
            (exp_dir / "conjecture.lean").write_text(lean_code, encoding="utf-8")
        final_proof = metadata.get("final_proof")
        if final_proof:
            (exp_dir / "proof.lean").write_text(final_proof, encoding="utf-8")

    def _commit_to_branch(self, experiment_id: str, timestamp: str) -> str:
        """Stage experiment files and create a commit on the experiments branch.

        The symbolic_ref swap and commit are wrapped in _COMMIT_LOCK so that
        concurrent calls from Celery worker threads never interleave their HEAD
        manipulations and corrupt which branch HEAD points to.
        """
        with _COMMIT_LOCK:
            rel_dir = Path("experiments") / experiment_id
            self._repo.index.add([str(rel_dir)])

            current_branch = self._repo.active_branch.name
            try:
                self._repo.git.symbolic_ref("HEAD", f"refs/heads/{self._branch_name}")
                commit = self._repo.index.commit(
                    f"experiment({experiment_id}): {timestamp}",
                    author=git.Actor("Germinal", "germinal@localhost"),
                    committer=git.Actor("Germinal", "germinal@localhost"),
                )
                sha = commit.hexsha
            finally:
                self._repo.git.symbolic_ref("HEAD", f"refs/heads/{current_branch}")

        return sha
