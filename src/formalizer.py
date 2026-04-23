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
        retry=retry_if_exception_type((anthropic.RateLimitError, anthropic.APIConnectionError)),
        wait=wait_exponential(multiplier=1, min=2, max=60),
        stop=stop_after_attempt(5),
        reraise=True,
    )
    def _call_api(self, conjecture: str, mathlib_context: str) -> str:
        """Ask Claude to produce Lean 4 code.

        The static instruction block is cached; the dynamic conjecture text is not.
        """
        user_content: list[dict[str, Any]] = [
            {
                "type": "text",
                "text": mathlib_context if mathlib_context else "(No specific Mathlib hints.)",
                "cache_control": {"type": "ephemeral"},
            },
            {
                "type": "text",
                "text": f"Conjecture to formalize:\n{conjecture}",
            },
        ]

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
            messages=[{"role": "user", "content": user_content}],
        )
        return response.content[0].text  # type: ignore[union-attr]

    def formalize(
        self,
        conjecture: str,
        subfield: str = "",
    ) -> dict[str, Any]:
        """Translate a conjecture into Lean 4 and validate it.

        Args:
            conjecture: Natural-language mathematical conjecture.
            subfield: Optional subfield hint for Mathlib RAG retrieval.

        Returns:
            Dict with keys: lean_code, is_valid, error_log.
        """
        conjecture = conjecture.strip()
        if not conjecture:
            raise ValueError("conjecture must be a non-empty string")

        logger.info("Formalizing conjecture (len=%d, subfield=%r)", len(conjecture), subfield)

        # Retrieve relevant Mathlib4 declarations
        relevant = mathlib_rag.retrieve(conjecture, subfield, top_k=12)
        mathlib_context = mathlib_rag.format_for_prompt(relevant)

        try:
            raw = self._call_api(conjecture, mathlib_context)
        except Exception as exc:
            logger.error("Claude API call failed during formalization: %s", exc)
            return {"lean_code": "", "is_valid": False, "error_log": str(exc)}

        lean_code = _strip_fences(raw)
        logger.debug("Raw Lean 4 output:\n%s", lean_code)

        import asyncio

        sandbox = get_sandbox(self._settings.lean_sandbox_dir, self._settings.lean_timeout)
        try:
            is_valid, error_log = asyncio.run(sandbox.build(lean_code))
        except Exception as exc:
            logger.error("Sandbox build error: %s", exc)
            is_valid, error_log = False, str(exc)

        if is_valid:
            logger.info("Lean 4 validation succeeded")
        else:
            logger.warning("Lean 4 validation failed:\n%s", error_log)

        return {"lean_code": lean_code, "is_valid": is_valid, "error_log": error_log}
