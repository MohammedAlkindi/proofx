"""Formalizer module.

Translates natural-language mathematical conjectures into Lean 4 / Mathlib4 code
via Claude API, then validates the code by running `lake build` in a sandbox.
"""

from __future__ import annotations

import logging
import os
import subprocess
import tempfile
import textwrap
from pathlib import Path
from typing import Any

import anthropic
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from src.settings import Settings

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = (
    "You are a Lean 4 expert. Translate the following mathematical "
    "conjecture into valid Lean 4 code using Mathlib4. Output only the "
    "Lean 4 code block, no explanation. The code must compile with "
    "`lake build`. Conjecture: {conjecture}"
)

_LAKE_TOML = textwrap.dedent("""\
    import Lake
    open Lake DSL

    package germinal_check where
      name := "germinal_check"

    require mathlib from git
      "https://github.com/leanprover-community/mathlib4" @ "master"

    lean_lib GerminalCheck where
      roots := #[`GerminalCheck]
""")


def _strip_fences(text: str) -> str:
    """Remove leading/trailing markdown code fences from a code block."""
    text = text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        start = 1
        end = len(lines) - 1 if lines[-1].strip() == "```" else len(lines)
        text = "\n".join(lines[start:end])
    return text.strip()


def _write_lean_project(workdir: Path, lean_code: str) -> None:
    """Scaffold a minimal Lake project containing the conjecture code."""
    (workdir / "lakefile.toml").write_text(_LAKE_TOML, encoding="utf-8")
    lean_src = workdir / "GerminalCheck.lean"
    lean_src.write_text(lean_code, encoding="utf-8")


def _run_lake_build(workdir: Path, timeout: int) -> tuple[bool, str]:
    """Run `lake build` in *workdir* and return (success, combined_output)."""
    try:
        result = subprocess.run(
            ["lake", "build"],
            cwd=str(workdir),
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        combined = result.stdout + result.stderr
        return result.returncode == 0, combined
    except subprocess.TimeoutExpired:
        return False, f"lake build timed out after {timeout}s"
    except FileNotFoundError:
        return False, "lake executable not found — is Lean 4 installed?"


class Formalizer:
    """Translates natural-language conjectures into verified Lean 4 code."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or Settings()
        self._client = anthropic.Anthropic(api_key=self._settings.anthropic_api_key)

    @retry(
        retry=retry_if_exception_type((anthropic.RateLimitError, anthropic.APIConnectionError)),
        wait=wait_exponential(multiplier=1, min=2, max=60),
        stop=stop_after_attempt(5),
        reraise=True,
    )
    def _call_api(self, conjecture: str) -> str:
        """Ask Claude to produce Lean 4 code for a natural-language conjecture."""
        response = self._client.messages.create(
            model=self._settings.claude_model,
            max_tokens=2048,
            messages=[
                {
                    "role": "user",
                    "content": _SYSTEM_PROMPT.format(conjecture=conjecture),
                }
            ],
        )
        return response.content[0].text  # type: ignore[union-attr]

    def formalize(self, conjecture: str) -> dict[str, Any]:
        """Translate a conjecture into Lean 4 and validate it via lake build.

        Args:
            conjecture: Natural-language mathematical conjecture.

        Returns:
            Dict with keys:
            - lean_code (str): Generated Lean 4 source.
            - is_valid (bool): Whether `lake build` succeeded.
            - error_log (str): Compiler output (empty on success).
        """
        conjecture = conjecture.strip()
        if not conjecture:
            raise ValueError("conjecture must be a non-empty string")

        logger.info("Formalizing conjecture (length=%d)", len(conjecture))

        try:
            raw = self._call_api(conjecture)
        except Exception as exc:
            logger.error("Claude API call failed during formalization: %s", exc)
            return {"lean_code": "", "is_valid": False, "error_log": str(exc)}

        lean_code = _strip_fences(raw)
        logger.debug("Raw Lean 4 output:\n%s", lean_code)

        is_valid, error_log = self._validate_lean(lean_code)
        if is_valid:
            logger.info("Lean 4 validation succeeded")
        else:
            logger.warning("Lean 4 validation failed:\n%s", error_log)

        return {"lean_code": lean_code, "is_valid": is_valid, "error_log": error_log}

    def _validate_lean(self, lean_code: str) -> tuple[bool, str]:
        """Write code to a temp Lake project and run lake build."""
        with tempfile.TemporaryDirectory(prefix="germinal_lean_") as tmpdir:
            workdir = Path(tmpdir)
            _write_lean_project(workdir, lean_code)
            return _run_lake_build(workdir, self._settings.lean_timeout)
