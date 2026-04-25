"""Counterexample finder module.

When automated proof search fails, asks Claude to attempt to construct a concrete
counterexample. This distinguishes "false conjecture" from "hard to prove conjecture",
which is a critical distinction for directing human research effort.
"""

from __future__ import annotations

import logging
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

_SYSTEM_PROMPT = """\
You are a mathematical expert. Given a conjecture, attempt to find a concrete
counterexample that disproves it.

Instructions:
- Think carefully about whether the conjecture is likely true or false.
- If you can find a counterexample, provide it explicitly and verify it satisfies
  all conditions while violating the conclusion.
- If the conjecture appears true and you cannot find a counterexample, say so clearly.
- Be rigorous: do not guess. Only claim a counterexample if you can verify it concretely.

Respond in JSON with this schema:
{
  "found": true | false,
  "counterexample": "concrete counterexample description or null",
  "reasoning": "your reasoning process"
}
"""


class CounterexampleFinder:
    """Asks Claude to find a concrete counterexample for a failed conjecture."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or Settings()
        self._client = anthropic.Anthropic(api_key=self._settings.anthropic_api_key)

    @retry(
        retry=retry_if_exception_type((anthropic.RateLimitError, anthropic.APIConnectionError)),
        wait=wait_exponential(multiplier=1, min=2, max=60),
        stop=stop_after_attempt(4),
        reraise=True,
    )
    def _call_api(self, conjecture: str, subfield: str) -> str:
        context = f"Subfield: {subfield}\n\n" if subfield else ""
        response = self._client.messages.create(
            model=self._settings.claude_model,
            max_tokens=2048,
            system=[
                {
                    "type": "text",
                    "text": _SYSTEM_PROMPT,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            messages=[
                {
                    "role": "user",
                    "content": f"{context}Conjecture:\n{conjecture}",
                }
            ],
        )
        return response.content[0].text  # type: ignore[union-attr]

    def search(self, conjecture: str, subfield: str = "") -> dict[str, Any]:
        """Search for a counterexample to the given conjecture.

        Returns:
            Dict with keys: found (bool), counterexample (str | None), reasoning (str).
        """
        conjecture = conjecture.strip()
        if not conjecture:
            raise ValueError("conjecture must be non-empty")

        logger.info("Searching for counterexample (subfield=%r)", subfield)

        try:
            raw = self._call_api(conjecture, subfield)
        except Exception as exc:
            logger.error("Counterexample API call failed: %s", exc)
            return {"found": False, "counterexample": None, "reasoning": f"API error: {exc}"}

        import json
        text = raw.strip()
        if text.startswith("```"):
            lines = text.splitlines()
            text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])

        try:
            data = json.loads(text)
            found = bool(data.get("found", False))
            counterexample = data.get("counterexample") or None
            reasoning = str(data.get("reasoning", ""))
            if found and not counterexample:
                found = False
            logger.info("Counterexample search result: found=%s", found)
            return {"found": found, "counterexample": counterexample, "reasoning": reasoning}
        except (json.JSONDecodeError, KeyError) as exc:
            logger.warning("Could not parse counterexample response: %s\nRaw: %s", exc, raw)
            return {"found": False, "counterexample": None, "reasoning": raw}
