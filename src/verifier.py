"""Verifier module.

Attempts to automatically prove a Lean 4 theorem statement by asking Claude to
generate tactic proofs, then running each attempt through Lean 4.
"""

from __future__ import annotations

import logging
import re
import subprocess
import tempfile
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
    "You are a Lean 4 theorem prover. Given the following unproven "
    "Lean 4 statement, generate a complete tactic proof. Use only tactics "
    "available in Mathlib4. If you cannot prove it, respond with `sorry` "
    "and explain why in a comment. Output only Lean 4 code."
)

_MAX_ATTEMPTS = 3

_LAKE_TOML = """\
import Lake
open Lake DSL

package germinal_verify where
  name := "germinal_verify"

require mathlib from git
  "https://github.com/leanprover-community/mathlib4" @ "master"

lean_lib GerminalVerify where
  roots := #[`GerminalVerify]
"""


def _strip_fences(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        start = 1
        end = len(lines) - 1 if lines[-1].strip() == "```" else len(lines)
        text = "\n".join(lines[start:end])
    return text.strip()


def _uses_sorry(lean_code: str) -> bool:
    """Return True if the code contains a `sorry` tactic (incomplete proof)."""
    return bool(re.search(r"\bsorry\b", lean_code))


def _write_verify_project(workdir: Path, lean_code: str) -> None:
    (workdir / "lakefile.toml").write_text(_LAKE_TOML, encoding="utf-8")
    (workdir / "GerminalVerify.lean").write_text(lean_code, encoding="utf-8")


def _run_lake_build(workdir: Path, timeout: int) -> tuple[bool, str]:
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


class Verifier:
    """Attempts automated proof of a Lean 4 theorem via Claude tactic suggestions."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or Settings()
        self._client = anthropic.Anthropic(api_key=self._settings.anthropic_api_key)

    @retry(
        retry=retry_if_exception_type((anthropic.RateLimitError, anthropic.APIConnectionError)),
        wait=wait_exponential(multiplier=1, min=2, max=60),
        stop=stop_after_attempt(5),
        reraise=True,
    )
    def _call_api(self, lean_statement: str, previous_errors: list[str]) -> str:
        """Ask Claude to generate a tactic proof, optionally with prior error context."""
        messages: list[dict[str, str]] = [
            {"role": "user", "content": f"{_SYSTEM_PROMPT}\n\n{lean_statement}"}
        ]
        if previous_errors:
            error_context = "\n\n".join(
                f"Previous attempt {i+1} failed with:\n{err}"
                for i, err in enumerate(previous_errors)
            )
            messages.append({"role": "assistant", "content": "I'll try again."})
            messages.append(
                {
                    "role": "user",
                    "content": (
                        f"That didn't work. Here are the errors so far:\n{error_context}\n"
                        "Please try a different approach."
                    ),
                }
            )

        response = self._client.messages.create(
            model=self._settings.claude_model,
            max_tokens=2048,
            messages=messages,
        )
        return response.content[0].text  # type: ignore[union-attr]

    def verify(self, lean_code: str) -> dict[str, Any]:
        """Attempt to prove a Lean 4 theorem statement.

        Runs up to _MAX_ATTEMPTS rounds: each round asks Claude for a tactic
        proof, then validates it with `lake build`. Stops early if proof succeeds.

        Args:
            lean_code: A valid Lean 4 source file containing the theorem statement.

        Returns:
            Dict with keys:
            - proved (bool): True if a complete proof was found.
            - attempts (list[dict]): Each attempt's generated code and error output.
            - final_proof (str | None): The first successful proof, or None.
            - failure_reason (str | None): Summary if all attempts failed.
        """
        lean_code = lean_code.strip()
        if not lean_code:
            raise ValueError("lean_code must be a non-empty string")

        logger.info("Starting proof verification (%d max attempts)", _MAX_ATTEMPTS)

        attempts: list[dict[str, Any]] = []
        previous_errors: list[str] = []

        for attempt_num in range(1, _MAX_ATTEMPTS + 1):
            logger.info("Proof attempt %d/%d", attempt_num, _MAX_ATTEMPTS)

            try:
                raw = self._call_api(lean_code, previous_errors)
            except Exception as exc:
                logger.error("Claude API call failed on attempt %d: %s", attempt_num, exc)
                attempts.append(
                    {"attempt": attempt_num, "lean_code": "", "error": str(exc), "success": False}
                )
                previous_errors.append(str(exc))
                continue

            candidate = _strip_fences(raw)

            if _uses_sorry(candidate):
                logger.warning("Attempt %d uses sorry — skipping validation", attempt_num)
                attempts.append(
                    {
                        "attempt": attempt_num,
                        "lean_code": candidate,
                        "error": "Proof uses sorry (incomplete)",
                        "success": False,
                    }
                )
                previous_errors.append("Model responded with sorry — proof incomplete")
                continue

            success, error_log = self._validate_attempt(candidate)

            attempts.append(
                {
                    "attempt": attempt_num,
                    "lean_code": candidate,
                    "error": "" if success else error_log,
                    "success": success,
                }
            )

            if success:
                logger.info("Proof succeeded on attempt %d", attempt_num)
                return {
                    "proved": True,
                    "attempts": attempts,
                    "final_proof": candidate,
                    "failure_reason": None,
                }

            previous_errors.append(error_log)
            logger.warning("Attempt %d failed:\n%s", attempt_num, error_log)

        failure_reason = (
            f"All {_MAX_ATTEMPTS} proof attempts failed. "
            "The theorem may require more advanced tactics or be unprovable automatically."
        )
        logger.info("Verification failed: %s", failure_reason)
        return {
            "proved": False,
            "attempts": attempts,
            "final_proof": None,
            "failure_reason": failure_reason,
        }

    def _validate_attempt(self, lean_code: str) -> tuple[bool, str]:
        """Write candidate proof to a temp Lake project and run lake build."""
        with tempfile.TemporaryDirectory(prefix="germinal_verify_") as tmpdir:
            workdir = Path(tmpdir)
            _write_verify_project(workdir, lean_code)
            return _run_lake_build(workdir, self._settings.lean_timeout)
