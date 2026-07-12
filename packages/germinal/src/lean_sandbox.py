"""Persistent Lean 4 sandbox.

Instead of creating a fresh temp directory + re-downloading Mathlib for every
`lake build` call (2–5 minutes cold), this module maintains a single
persistent Lake workspace.  Mathlib is downloaded once and cached in
`.lean_sandbox/.lake/`.  Subsequent builds only recompile the changed source
file, typically taking 5–30 seconds.

Thread / process safety: a file-based lock (`build.lock`) ensures only one
`lake build` runs at a time within a single worker.  When Celery is used,
each worker has its own sandbox directory (suffixed with the worker PID) so
builds run in parallel across workers.
"""

from __future__ import annotations

import asyncio
import logging
import os
import subprocess
import textwrap
from pathlib import Path

logger = logging.getLogger(__name__)

_LAKEFILE_TOML = textwrap.dedent("""\
    import Lake
    open Lake DSL

    package germinal_sandbox where
      name := "germinal_sandbox"

    require mathlib from git
      "https://github.com/leanprover-community/mathlib4" @ "master"

    lean_lib GerminalSandbox where
      roots := #[`GerminalSandbox]
""")

_SRC_FILE = "GerminalSandbox.lean"


class LeanSandbox:
    """Manages a single, reusable Lake workspace with a cached Mathlib build.

    Usage::

        sandbox = LeanSandbox(Path(".lean_sandbox"))
        await sandbox.ensure_ready()               # one-time setup (slow first time)
        ok, log = await sandbox.build(lean_code)   # fast on subsequent calls
    """

    def __init__(self, workspace: Path, timeout: int = 120) -> None:
        self._workspace = workspace.resolve()
        self._timeout = timeout
        self._ready = False
        self._lock = asyncio.Lock()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def ensure_ready(self) -> None:
        """Initialise the workspace and warm up Mathlib (no-op if already done)."""
        if self._ready:
            return
        async with self._lock:
            if self._ready:
                return
            await asyncio.to_thread(self._init_workspace)
            self._ready = True

    async def build(self, lean_code: str) -> tuple[bool, str]:
        """Write *lean_code* to the sandbox source file and run `lake build`.

        Returns (success, combined_stdout_stderr).
        """
        await self.ensure_ready()
        async with self._lock:
            return await asyncio.to_thread(self._sync_build, lean_code)

    # ------------------------------------------------------------------
    # Synchronous internals (run in thread pool)
    # ------------------------------------------------------------------

    def _init_workspace(self) -> None:
        self._workspace.mkdir(parents=True, exist_ok=True)
        lakefile = self._workspace / "lakefile.toml"
        if not lakefile.exists():
            lakefile.write_text(_LAKEFILE_TOML, encoding="utf-8")
            logger.info("LeanSandbox: created lakefile at %s", self._workspace)

        # Write a placeholder source so `lake update` succeeds on first run
        src = self._workspace / _SRC_FILE
        if not src.exists():
            src.write_text("-- placeholder\n", encoding="utf-8")

        # Download / update Mathlib only if the cache doesn't exist yet
        lake_dir = self._workspace / ".lake"
        if not lake_dir.exists():
            logger.info(
                "LeanSandbox: running `lake update` — this takes several minutes the first time"
            )
            result = subprocess.run(
                ["lake", "update"],
                cwd=str(self._workspace),
                capture_output=True,
                text=True,
                timeout=600,
            )
            if result.returncode != 0:
                logger.warning("lake update returned non-zero:\n%s", result.stderr)

    def _sync_build(self, lean_code: str) -> tuple[bool, str]:
        src = self._workspace / _SRC_FILE
        src.write_text(lean_code, encoding="utf-8")

        try:
            result = subprocess.run(
                ["lake", "build", "GerminalSandbox"],
                cwd=str(self._workspace),
                capture_output=True,
                text=True,
                timeout=self._timeout,
            )
            combined = result.stdout + result.stderr
            return result.returncode == 0, combined
        except subprocess.TimeoutExpired:
            return False, f"lake build timed out after {self._timeout}s"
        except FileNotFoundError:
            return False, "lake executable not found — is Lean 4 installed?"


# ---------------------------------------------------------------------------
# Module-level singleton: shared across the process lifetime
# ---------------------------------------------------------------------------

_sandbox_instance: LeanSandbox | None = None


def get_sandbox(
    workspace_dir: str = ".lean_sandbox", timeout: int = 120
) -> LeanSandbox:
    """Return (or create) the process-level singleton sandbox.

    The workspace directory is suffixed with the current PID so parallel
    Celery workers each get their own isolated build cache.
    """
    global _sandbox_instance
    if _sandbox_instance is None:
        pid = os.getpid()
        path = Path(workspace_dir) / f"worker_{pid}"
        _sandbox_instance = LeanSandbox(path, timeout=timeout)
    return _sandbox_instance
