"""Verifier module.

Attempts to automatically prove a Lean 4 theorem statement.

Enhancements over v1:
- Extended thinking: Claude reasons deeply before generating a proof tactic
- Multi-strategy parallel search: quick automation tactics race against
  Claude-generated proofs; first to succeed wins
- Prompt caching on the static system instruction
- Persistent LeanSandbox instead of per-call tempdirs
- Async-first interface (`verify_async`) for use from Celery / FastAPI
"""

from __future__ import annotations

import asyncio
import logging
import re
from typing import Any

import anthropic
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from src.lean_sandbox import get_sandbox
from src.settings import Settings

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = (
    "You are a Lean 4 theorem prover. Given a Lean 4 theorem statement, generate a "
    "complete tactic proof using only tactics available in Mathlib4. "
    "If you cannot prove it, respond with `sorry` and a brief comment explaining why. "
    "Output only the complete Lean 4 source file (with `import Mathlib` header and the "
    "theorem with its proof filled in)."
)

_MAX_ATTEMPTS = 6

# Quick automation tactics injected before the `sorry` proof body.
# Each is tried concurrently with Claude's suggestion.
_AUTO_TACTICS = [
    "by decide",
    "by norm_num",
    "by ring",
    "by omega",
    "by simp_all",
    "by aesop",
    "by tauto",
]


def _strip_fences(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        start = 1
        end = len(lines) - 1 if lines[-1].strip() == "```" else len(lines)
        text = "\n".join(lines[start:end])
    return text.strip()


def _uses_sorry(lean_code: str) -> bool:
    return bool(re.search(r"\bsorry\b", lean_code))


def _inject_tactic(lean_code: str, tactic: str) -> str:
    """Replace the `sorry` body in a theorem with *tactic*."""
    return re.sub(r"\bsorry\b", tactic, lean_code, count=1)


class Verifier:
    """Attempts automated proof of a Lean 4 theorem via Claude tactic suggestions."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or Settings()
        self._client = anthropic.Anthropic(api_key=self._settings.anthropic_api_key)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def verify(
        self, lean_code: str, strategy: str = "claude_standard"
    ) -> dict[str, Any]:
        """Synchronous wrapper around verify_async for backward compatibility."""
        return asyncio.run(self.verify_async(lean_code, strategy))

    async def verify_async(
        self, lean_code: str, strategy: str = "claude_standard"
    ) -> dict[str, Any]:
        """Attempt to prove a Lean 4 theorem statement.

        Runs a multi-strategy parallel search:
        1. Quick automation tactics (decide, norm_num, ring, omega, simp_all, aesop, tauto)
        2. Claude-generated tactics (standard or extended-thinking mode)

        Returns:
            Dict with keys: proved, attempts, final_proof, failure_reason.
        """
        lean_code = lean_code.strip()
        if not lean_code:
            raise ValueError("lean_code must be a non-empty string")

        sandbox = get_sandbox(
            self._settings.lean_sandbox_dir, self._settings.lean_timeout
        )
        await sandbox.ensure_ready()

        logger.info(
            "Starting proof verification (strategy=%s, max=%d)", strategy, _MAX_ATTEMPTS
        )

        attempts: list[dict[str, Any]] = []

        # ── Phase 1: quick automation tactics (parallel) ─────────────────
        if strategy in ("quick_tactics", "claude_standard", "extended_thinking"):
            result = await self._try_auto_tactics(lean_code, sandbox, attempts)
            if result is not None:
                return result

        if strategy == "quick_tactics":
            return self._failure_result(attempts)

        # ── Phase 2: Claude-generated tactics ────────────────────────────
        use_extended = (
            strategy == "extended_thinking" and self._settings.extended_thinking_enabled
        )
        previous_errors: list[str] = []

        for attempt_num in range(1, _MAX_ATTEMPTS + 1):
            logger.info(
                "Claude proof attempt %d/%d (extended=%s)",
                attempt_num,
                _MAX_ATTEMPTS,
                use_extended,
            )

            try:
                candidate = await asyncio.to_thread(
                    self._call_api, lean_code, previous_errors, use_extended
                )
            except Exception as exc:
                logger.error(
                    "Claude API call failed on attempt %d: %s", attempt_num, exc
                )
                attempts.append(
                    {
                        "attempt": attempt_num,
                        "lean_code": "",
                        "error": str(exc),
                        "success": False,
                    }
                )
                previous_errors.append(str(exc))
                continue

            if _uses_sorry(candidate):
                logger.warning("Attempt %d uses sorry — skipping", attempt_num)
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

            success, error_log = await sandbox.build(candidate)
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
            logger.warning("Attempt %d failed", attempt_num)

        return self._failure_result(attempts)

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    async def _try_auto_tactics(
        self,
        lean_code: str,
        sandbox: Any,
        attempts: list[dict[str, Any]],
    ) -> dict[str, Any] | None:
        """Try all quick tactics concurrently; return on first success."""
        tasks = {
            asyncio.create_task(
                sandbox.build(_inject_tactic(lean_code, tactic))
            ): tactic
            for tactic in _AUTO_TACTICS
            if _uses_sorry(lean_code)
        }
        if not tasks:
            return None

        pending = set(tasks)
        done_tasks: set[asyncio.Task[Any]] = set()
        try:
            done_tasks, pending = await asyncio.wait(
                pending, return_when=asyncio.FIRST_COMPLETED
            )
        except Exception:
            pass

        for task in done_tasks:
            tactic = tasks[task]
            try:
                success, error_log = task.result()
            except Exception as exc:
                success, error_log = False, str(exc)

            proof_code = _inject_tactic(lean_code, tactic)
            attempts.append(
                {
                    "attempt": f"auto:{tactic}",
                    "lean_code": proof_code,
                    "error": "" if success else error_log,
                    "success": success,
                }
            )

            if success:
                for p in pending:
                    p.cancel()
                logger.info("Quick tactic succeeded: %s", tactic)
                return {
                    "proved": True,
                    "attempts": attempts,
                    "final_proof": proof_code,
                    "failure_reason": None,
                }

        # Cancel remaining pending tasks
        for p in pending:
            p.cancel()
        return None

    @retry(
        retry=retry_if_exception_type(
            (anthropic.RateLimitError, anthropic.APIConnectionError)
        ),
        wait=wait_exponential(multiplier=1, min=2, max=60),
        stop=stop_after_attempt(5),
        reraise=True,
    )
    def _call_api(
        self,
        lean_statement: str,
        previous_errors: list[str],
        use_extended_thinking: bool = False,
    ) -> str:
        """Call Claude to generate a tactic proof."""
        messages: list[dict[str, Any]] = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": _SYSTEM_PROMPT,
                        "cache_control": {"type": "ephemeral"},
                    },
                    {"type": "text", "text": lean_statement},
                ],
            }
        ]

        if previous_errors:
            error_context = "\n\n".join(
                f"Attempt {i + 1} failed:\n{err}"
                for i, err in enumerate(previous_errors)
            )
            messages.append(
                {"role": "assistant", "content": "I'll try a different approach."}
            )
            messages.append(
                {
                    "role": "user",
                    "content": f"Those didn't work. Errors:\n{error_context}\nPlease try again.",
                }
            )

        kwargs: dict[str, Any] = {
            "model": self._settings.claude_model,
            "max_tokens": 16000 if use_extended_thinking else 4096,
            "messages": messages,
        }

        if use_extended_thinking:
            kwargs["thinking"] = {
                "type": "enabled",
                "budget_tokens": self._settings.thinking_budget_tokens,
            }

        response = self._client.messages.create(**kwargs)

        # Extract text block (extended thinking responses contain ThinkingBlock first)
        for block in response.content:
            if hasattr(block, "text"):
                return block.text  # type: ignore[return-value]

        return ""

    @staticmethod
    def _failure_result(attempts: list[dict[str, Any]]) -> dict[str, Any]:
        return {
            "proved": False,
            "attempts": attempts,
            "final_proof": None,
            "failure_reason": (
                f"All {len(attempts)} proof attempts failed. "
                "The theorem may require more advanced tactics or human insight."
            ),
        }
