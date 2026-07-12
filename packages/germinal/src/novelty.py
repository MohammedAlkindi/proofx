"""Novelty detection for generated conjectures.

Uses Jaccard similarity on word-level tokens to detect near-duplicate
conjectures before they are committed as new experiments.
"""

from __future__ import annotations

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)


def _tokenize(text: str) -> frozenset[str]:
    return frozenset(re.findall(r"[a-zA-Z0-9]+", text.lower()))


def jaccard(a: str, b: str) -> float:
    sa, sb = _tokenize(a), _tokenize(b)
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)


class NoveltyChecker:
    """Detects near-duplicate conjectures against a rolling history."""

    def __init__(self, threshold: float = 0.55) -> None:
        self._threshold = threshold
        self._seen: list[str] = []

    def is_novel(self, statement: str) -> tuple[bool, float]:
        """Return (is_novel, max_similarity_to_any_previous_conjecture).

        A conjecture is not novel if its Jaccard similarity to any previously
        seen statement exceeds the threshold.
        """
        if not self._seen:
            self._register(statement)
            return True, 0.0

        max_sim = max(jaccard(statement, prev) for prev in self._seen)
        novel = max_sim < self._threshold
        if novel:
            self._register(statement)
        else:
            logger.info(
                "Conjecture rejected as near-duplicate (sim=%.3f ≥ %.3f): %.80s",
                max_sim,
                self._threshold,
                statement,
            )
        return novel, max_sim

    def filter_novel(
        self, conjectures: list[dict[str, Any]]
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        """Partition conjectures into (novel, duplicates).

        Each conjecture dict gains a ``novelty_score`` key (1 − max_similarity).
        """
        novel, duplicates = [], []
        for c in conjectures:
            ok, sim = self.is_novel(c["statement"])
            c = {**c, "novelty_score": round(1.0 - sim, 4)}
            (novel if ok else duplicates).append(c)
        return novel, duplicates

    def seed_from_experiments(self, experiments: list[dict[str, Any]]) -> None:
        """Pre-populate history from existing experiment records."""
        for exp in experiments:
            stmt = exp.get("conjecture", "")
            if stmt:
                self._seen.append(stmt)
        logger.info(
            "NoveltyChecker seeded with %d existing statements", len(self._seen)
        )

    def _register(self, statement: str) -> None:
        self._seen.append(statement)
        if len(self._seen) > 2000:
            self._seen = self._seen[-2000:]
