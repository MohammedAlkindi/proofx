"""Conjecture complexity estimator.

A lightweight Claude API call that scores each conjecture before Lean work
starts, so we can route: easy → auto-verify, hard → extended thinking,
very hard → flag for human review.
"""

from __future__ import annotations

import json
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

_SYSTEM = (
    "You are a mathematical complexity analyser. Given a conjecture, output a JSON object "
    "with exactly these keys:\n"
    '  "formalizability": integer 1–5  (1=trivial, 5=requires deep Mathlib expertise)\n'
    '  "proof_difficulty": integer 1–5  (1=decidable/`decide`, 5=open research problem)\n'
    '  "recommended_strategy": one of "quick_tactics", "claude_standard", "extended_thinking", "human_review"\n'
    '  "rationale": string, one sentence\n'
    "Output only the JSON object, no markdown."
)

_STRATEGY_MAP = {
    (1, 1): "quick_tactics",
    (1, 2): "quick_tactics",
    (2, 1): "quick_tactics",
    (2, 2): "claude_standard",
    (3, 3): "claude_standard",
}


def _strategy_from_scores(f: int, p: int) -> str:
    if f <= 2 and p <= 2:
        return "quick_tactics"
    if f >= 5 or p >= 5:
        return "human_review"
    if p >= 4:
        return "extended_thinking"
    return "claude_standard"


class ComplexityEstimator:
    """Estimates formalizability and proof difficulty before Lean work starts."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or Settings()
        self._client = anthropic.Anthropic(api_key=self._settings.anthropic_api_key)

    @retry(
        retry=retry_if_exception_type(
            (anthropic.RateLimitError, anthropic.APIConnectionError)
        ),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        stop=stop_after_attempt(3),
        reraise=True,
    )
    def estimate(self, statement: str) -> dict[str, Any]:
        """Return a complexity estimate dict for *statement*.

        Keys: formalizability (1–5), proof_difficulty (1–5),
              recommended_strategy, rationale.

        Falls back to a safe default on any error.
        """
        try:
            response = self._client.messages.create(
                model=self._settings.claude_model,
                max_tokens=256,
                system=[
                    {
                        "type": "text",
                        "text": _SYSTEM,
                        "cache_control": {"type": "ephemeral"},
                    }
                ],
                messages=[{"role": "user", "content": f"Conjecture: {statement}"}],
            )
            raw = response.content[0].text.strip()  # type: ignore[union-attr]
            if raw.startswith("```"):
                lines = raw.splitlines()
                raw = "\n".join(
                    lines[1:-1] if lines[-1].strip() == "```" else lines[1:]
                )
            data: dict[str, Any] = json.loads(raw)
            f = int(data.get("formalizability", 3))
            p = int(data.get("proof_difficulty", 3))
            data["recommended_strategy"] = data.get(
                "recommended_strategy", _strategy_from_scores(f, p)
            )
            return data
        except Exception as exc:
            logger.warning("Complexity estimation failed: %s — using defaults", exc)
            return {
                "formalizability": 3,
                "proof_difficulty": 3,
                "recommended_strategy": "claude_standard",
                "rationale": "Could not estimate complexity.",
            }
