"""Conjecture generator module.

Calls Claude API to propose original mathematical conjectures for a given domain.
Enhancements over v1:
- Prompt caching on the static system prompt (reduces cost ~80% on repeat calls)
- arXiv paper context injected into generation prompt
- Failure-registry avoidance hint steers Claude away from historically hard subfields
- Structured JSON output with novelty_score populated by caller
"""

from __future__ import annotations

import json
import logging
import uuid
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
    "You are a mathematical research assistant. Given a domain, propose "
    "{n} original, non-trivial conjectures that are plausible but unproven. "
    "For each, provide: (1) a precise natural language statement, "
    "(2) the sub-field it belongs to, (3) why it is interesting, "
    "(4) a rough confidence it is true (0.0–1.0). "
    "Respond only in valid JSON matching this schema: "
    '[{{ "statement": "...", "subfield": "...", "motivation": "...", "confidence": 0.0 }}]'
)


def _build_system_prompt(n: int) -> str:
    return _SYSTEM_PROMPT.format(n=n)


def _parse_response(raw: str, domain: str) -> list[dict[str, Any]]:
    text = raw.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])

    data: list[dict[str, Any]] = json.loads(text)

    results: list[dict[str, Any]] = []
    for item in data:
        results.append(
            {
                "id": str(uuid.uuid4()),
                "domain": domain,
                "statement": str(item.get("statement", "")),
                "subfield": str(item.get("subfield", domain)),
                "motivation": str(item.get("motivation", "")),
                "confidence_estimate": float(item.get("confidence", 0.5)),
                "tags": _derive_tags(item),
            }
        )
    return results


def _derive_tags(item: dict[str, Any]) -> list[str]:
    tags: list[str] = []
    subfield = str(item.get("subfield", "")).lower()
    for keyword in (
        "prime",
        "graph",
        "topology",
        "algebra",
        "number",
        "combinatorics",
        "geometry",
    ):
        if keyword in subfield or keyword in str(item.get("statement", "")).lower():
            tags.append(keyword)
    confidence = float(item.get("confidence", 0.5))
    if confidence >= 0.8:
        tags.append("high-confidence")
    elif confidence <= 0.3:
        tags.append("speculative")
    return list(set(tags))


class ConjectureGenerator:
    """Generates candidate mathematical conjectures via Claude API."""

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
        domain: str,
        n: int,
        arxiv_context: str = "",
        avoidance_hint: str = "",
    ) -> str:
        """Call Claude API with prompt caching on the system prompt."""
        user_parts: list[dict[str, Any]] = []

        # Static context block — cached after first call
        if arxiv_context:
            user_parts.append(
                {
                    "type": "text",
                    "text": arxiv_context,
                    "cache_control": {"type": "ephemeral"},
                }
            )

        # Dynamic per-request block — never cached
        dynamic = f"Domain: {domain}. Propose {n} conjectures."
        if avoidance_hint:
            dynamic += f"\n\n{avoidance_hint}"
        user_parts.append({"type": "text", "text": dynamic})

        response = self._client.messages.create(
            model=self._settings.claude_model,
            max_tokens=4096,
            system=[
                {
                    "type": "text",
                    "text": _build_system_prompt(n),
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            messages=[{"role": "user", "content": user_parts}],
        )
        return response.content[0].text  # type: ignore[union-attr]

    def generate(
        self,
        domain: str,
        n: int = 5,
        arxiv_context: list[dict[str, Any]] | None = None,
        avoidance_hint: str = "",
    ) -> list[dict[str, Any]]:
        """Generate N mathematical conjectures for the given domain.

        Args:
            domain: Mathematical domain, e.g. "number theory".
            n: Number of conjectures to generate (1–20).
            arxiv_context: Recent arXiv papers formatted by arxiv_client.
            avoidance_hint: Failure-registry hint about subfields to avoid.

        Returns:
            List of conjecture dicts with keys:
            id, domain, statement, subfield, motivation, confidence_estimate, tags.
        """
        domain = domain.strip()
        if not domain:
            raise ValueError("domain must be a non-empty string")
        if not 1 <= n <= 20:
            raise ValueError("n must be between 1 and 20")

        from src.arxiv_client import format_papers_for_prompt

        arxiv_str = format_papers_for_prompt(arxiv_context or [])

        logger.info("Generating %d conjecture(s) for domain=%r", n, domain)
        raw = self._call_api(
            domain, n, arxiv_context=arxiv_str, avoidance_hint=avoidance_hint
        )
        logger.debug("Raw Claude response: %s", raw)

        try:
            conjectures = _parse_response(raw, domain)
        except (json.JSONDecodeError, KeyError, TypeError) as exc:
            logger.error("Failed to parse Claude response: %s\nRaw: %s", exc, raw)
            raise

        logger.info("Generated %d conjecture(s)", len(conjectures))
        return conjectures
