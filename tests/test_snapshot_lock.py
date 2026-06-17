"""Tests for the threading.Lock in src/snapshot.py's _commit_to_branch.

Uses a real temporary git repository — mocking git.Repo would defeat the
purpose of verifying that concurrent symbolic_ref swaps do not corrupt HEAD.
No Anthropic API or Lean install is required.

Windows note: gitpython holds file handles on the .git directory until the Repo
object is explicitly closed.  Each test closes all Repo handles before the
TemporaryDirectory context exits.  ignore_cleanup_errors=True is also set so
that any residual lock-file races do not fail the test.
"""

from __future__ import annotations

import tempfile
import threading
from pathlib import Path
from unittest.mock import MagicMock

import git

from src.snapshot import SnapshotManager


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _init_repo(tmpdir: str) -> git.Repo:
    """Initialise a git repo with a single commit so branches can be created."""
    repo = git.Repo.init(tmpdir)
    readme = Path(tmpdir) / "README.md"
    readme.write_text("init", encoding="utf-8")
    repo.index.add(["README.md"])
    repo.index.commit(
        "initial commit",
        author=git.Actor("test", "test@test.com"),
        committer=git.Actor("test", "test@test.com"),
    )
    return repo


def _mock_settings(branch: str = "experiments") -> MagicMock:
    s = MagicMock()
    s.git_experiments_branch = branch
    return s


def _commit(manager: SnapshotManager, exp_id: str, results: list, errors: list) -> None:
    try:
        sha = manager.commit_experiment(
            experiment_id=exp_id,
            domain="algebra",
            conjecture="test conjecture",
            lean_code="import Mathlib\ntheorem test : True := sorry",
            is_valid=True,
            proved=False,
            final_proof=None,
            model_used="claude-test",
            duration_ms=100,
        )
        results.append(sha)
    except Exception as exc:  # noqa: BLE001
        errors.append(exc)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestSnapshotLock:
    def test_concurrent_commits_both_complete(self):
        """Two threads calling commit_experiment() concurrently both succeed."""
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
            init_repo = _init_repo(tmpdir)
            manager = SnapshotManager(tmpdir, _mock_settings())

            results: list[str] = []
            errors: list[Exception] = []

            t1 = threading.Thread(
                target=_commit, args=(manager, "exp-001", results, errors)
            )
            t2 = threading.Thread(
                target=_commit, args=(manager, "exp-002", results, errors)
            )
            t1.start()
            t2.start()
            t1.join()
            t2.join()

            assert not errors, f"Unexpected errors during concurrent commits: {errors}"
            assert len(results) == 2

            # Release git file handles before temp dir cleanup (Windows compatibility).
            manager._repo.close()
            init_repo.close()

    def test_concurrent_commits_produce_distinct_shas(self):
        """Each concurrent commit produces a unique git SHA."""
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
            init_repo = _init_repo(tmpdir)
            manager = SnapshotManager(tmpdir, _mock_settings())

            results: list[str] = []
            errors: list[Exception] = []

            t1 = threading.Thread(
                target=_commit, args=(manager, "exp-003", results, errors)
            )
            t2 = threading.Thread(
                target=_commit, args=(manager, "exp-004", results, errors)
            )
            t1.start()
            t2.start()
            t1.join()
            t2.join()

            assert not errors
            assert len(set(results)) == 2, "Both commits must have distinct SHAs"

            manager._repo.close()
            init_repo.close()

    def test_head_restored_to_original_branch_after_concurrent_commits(self):
        """After both commits finish, HEAD points back to the branch it was on before."""
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
            repo = _init_repo(tmpdir)
            original_branch = repo.active_branch.name
            manager = SnapshotManager(tmpdir, _mock_settings())

            results: list[str] = []
            errors: list[Exception] = []

            t1 = threading.Thread(
                target=_commit, args=(manager, "exp-005", results, errors)
            )
            t2 = threading.Thread(
                target=_commit, args=(manager, "exp-006", results, errors)
            )
            t1.start()
            t2.start()
            t1.join()
            t2.join()

            assert not errors
            assert repo.active_branch.name == original_branch, (
                f"HEAD was left on '{repo.active_branch.name}' instead of '{original_branch}'"
            )

            # Release git handles before temp dir cleanup.
            manager._repo.close()
            repo.close()
