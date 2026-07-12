"""Formalizer module.

Translates natural-language mathematical conjectures into Lean 4 / Mathlib4 code
via Claude API, then validates using the persistent LeanSandbox.

Enhancements over v1:
- Prompt caching on the static instruction block
- Mathlib4 RAG — relevant lemma signatures injected into every prompt
- Complexity-aware routing: low-complexity statements get a simpler prompt;
  high-complexity ones request more verbose scaffolding
- Persistent LeanSandbox replaces per-call tempdir (major speed improvement)
"""

from __future__ import annotations

import logging
import textwrap
from typing import Any

import anthropic
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from src import mathlib_rag
from src.lean_sandbox import get_sandbox
from src.settings import Settings

logger = logging.getLogger(__name__)

_STATIC_INSTRUCTIONS = textwrap.dedent("""\
    You are a Lean 4 / Mathlib4 expert. Translate the given mathematical conjecture
    into a valid Lean 4 theorem statement (with `theorem` or `lemma` keyword).
    Rules:
    - Import only `import Mathlib` at the top — do not import individual sub-modules.
    - Use `sorry` as the proof body (we only need the statement to typecheck).
    - The file must compile with `lake build` against Mathlib4.
    - Output only the Lean 4 source code, no markdown, no explanation.
""")


def _strip_fences(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        start = 1
        end = len(lines) - 1 if lines[-1].strip() == "```" else len(lines)
        text = "\n".join(lines[start:end])
    return text.strip()


class Formalizer:
    """Translates natural-language conjectures into validated Lean 4 code."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or Settings()
        self._client = anthropic.Anthropic(api_key=self._settings.anthropic_api_key)

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
        conjecture: str,
        mathlib_context: str,
        previous_error: str = "",
    ) -> str:
        """Ask Claude to produce Lean 4 code.

        The static instruction block is cached; the dynamic conjecture text is not.
        When previous_error is supplied, Claude is asked to fix the prior attempt.
        """
        user_content: list[dict[str, Any]] = [
            {
                "type": "text",
                "text": mathlib_context
                if mathlib_context
                else "(No specific Mathlib hints.)",
                "cache_control": {"type": "ephemeral"},
            },
            {
                "type": "text",
                "text": f"Conjecture to formalize:\n{conjecture}",
            },
        ]

        messages: list[dict[str, Any]] = [{"role": "user", "content": user_content}]

        if previous_error:
            messages.append(
                {
                    "role": "assistant",
                    "content": "I'll try a corrected formalization.",
                }
            )
            messages.append(
                {
                    "role": "user",
                    "content": (
                        f"The previous Lean 4 output failed to compile with this error:\n\n"
                        f"```\n{previous_error}\n```\n\n"
                        "Please produce a corrected Lean 4 theorem statement that fixes the error. "
                        "Output only the Lean 4 source code."
                    ),
                }
            )

        response = self._client.messages.create(
            model=self._settings.claude_model,
            max_tokens=2048,
            system=[
                {
                    "type": "text",
                    "text": _STATIC_INSTRUCTIONS,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            messages=messages,
        )
        return response.content[0].text  # type: ignore[union-attr]

    def formalize(
        self,
        conjecture: str,
        subfield: str = "",
        max_attempts: int | None = None,
    ) -> dict[str, Any]:
        """Translate a conjecture into Lean 4 and validate it, with repair loop.

        On validation failure the Lean error is fed back to Claude for up to
        `max_attempts` total tries (default: settings.formalize_repair_attempts).

        Returns:
            Dict with keys: lean_code, is_valid, error_log, repair_attempts.
        """
        conjecture = conjecture.strip()
        if not conjecture:
            raise ValueError("conjecture must be a non-empty string")

        max_attempts = (
            max_attempts
            if max_attempts is not None
            else self._settings.formalize_repair_attempts
        )
        logger.info(
            "Formalizing conjecture (len=%d, subfield=%r, max_attempts=%d)",
            len(conjecture),
            subfield,
            max_attempts,
        )

        import asyncio

        relevant = mathlib_rag.retrieve(conjecture, subfield, top_k=12)
        mathlib_context = mathlib_rag.format_for_prompt(relevant)
        sandbox = get_sandbox(
            self._settings.lean_sandbox_dir, self._settings.lean_timeout
        )

        lean_code = ""
        error_log = ""
        previous_error = ""

        for attempt in range(1, max_attempts + 1):
            try:
                raw = self._call_api(conjecture, mathlib_context, previous_error)
            except Exception as exc:
                logger.error(
                    "Claude API call failed on formalization attempt %d: %s",
                    attempt,
                    exc,
                )
                return {
                    "lean_code": lean_code,
                    "is_valid": False,
                    "error_log": str(exc),
                    "repair_attempts": attempt,
                }

            lean_code = _strip_fences(raw)
            logger.debug(
                "Formalization attempt %d Lean output:\n%s", attempt, lean_code
            )

            try:
                is_valid, error_log = asyncio.run(sandbox.build(lean_code))
            except Exception as exc:
                logger.error("Sandbox build error on attempt %d: %s", attempt, exc)
                is_valid, error_log = False, str(exc)

            if is_valid:
                logger.info(
                    "Lean 4 validation succeeded on attempt %d/%d",
                    attempt,
                    max_attempts,
                )
                return {
                    "lean_code": lean_code,
                    "is_valid": True,
                    "error_log": "",
                    "repair_attempts": attempt,
                }

            logger.warning(
                "Formalization attempt %d/%d failed:\n%s",
                attempt,
                max_attempts,
                error_log,
            )
            previous_error = error_log

        return {
            "lean_code": lean_code,
            "is_valid": False,
            "error_log": error_log,
            "repair_attempts": max_attempts,
        }
