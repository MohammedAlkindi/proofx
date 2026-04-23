"""Failure registry — tracks which subfields consistently fail formalization/proof.

Persisted in Redis when available; falls back to in-process dict so the system
works without Redis in dev mode.
"""

from __future__ import annotations

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)

_REDIS_KEY = "germinal:failure_registry"
_AVOID_THRESHOLD = 5  # subfields with >= this many failures are flagged


class FailureRegistry:
    """Tracks formalization / proof failure counts per subfield.

    Thread-safe enough for our single-worker use-case (each Celery worker has
    its own instance; Redis is the source of truth when available).
    """

    def __init__(self, redis_url: str = "") -> None:
        self._local: dict[str, int] = {}
        self._redis: Any = None
        if redis_url:
            try:
                import redis

                self._redis = redis.from_url(redis_url, decode_responses=True)
                self._redis.ping()
                logger.info("FailureRegistry: using Redis at %s", redis_url)
            except Exception as exc:
                logger.warning("FailureRegistry: Redis unavailable (%s), using local dict", exc)
                self._redis = None

    # ------------------------------------------------------------------

    def record_failure(self, subfield: str, stage: str = "formalize") -> None:
        """Increment failure count for *subfield*."""
        key = f"{subfield}:{stage}"
        if self._redis:
            try:
                self._redis.hincrby(_REDIS_KEY, key, 1)
                return
            except Exception:
                pass
        self._local[key] = self._local.get(key, 0) + 1

    def record_success(self, subfield: str, stage: str = "formalize") -> None:
        """Decrement failure count on success (floors at 0)."""
        key = f"{subfield}:{stage}"
        if self._redis:
            try:
                current = int(self._redis.hget(_REDIS_KEY, key) or 0)
                if current > 0:
                    self._redis.hset(_REDIS_KEY, key, max(0, current - 1))
                return
            except Exception:
                pass
        self._local[key] = max(0, self._local.get(key, 0) - 1)

    def get_count(self, subfield: str, stage: str = "formalize") -> int:
        key = f"{subfield}:{stage}"
        if self._redis:
            try:
                return int(self._redis.hget(_REDIS_KEY, key) or 0)
            except Exception:
                pass
        return self._local.get(key, 0)

    def problematic_subfields(self, stage: str = "formalize") -> list[str]:
        """Return subfields that have exceeded the failure threshold."""
        data = self._all_counts()
        return [
            k.split(":")[0]
            for k, v in data.items()
            if k.endswith(f":{stage}") and v >= _AVOID_THRESHOLD
        ]

    def build_avoidance_hint(self) -> str:
        """Return a prompt hint telling Claude which subfields to avoid."""
        bad_formalize = self.problematic_subfields("formalize")
        bad_verify = self.problematic_subfields("verify")
        parts = []
        if bad_formalize:
            parts.append(
                f"Avoid conjectures in these subfields (consistently fail formalization): "
                f"{', '.join(bad_formalize)}."
            )
        if bad_verify:
            parts.append(
                f"Prefer simpler statements in these subfields (proofs never succeed automatically): "
                f"{', '.join(bad_verify)}."
            )
        return " ".join(parts)

    def all_stats(self) -> dict[str, Any]:
        """Return all failure counts as a dict for /stats endpoint."""
        raw = self._all_counts()
        result: dict[str, Any] = {}
        for k, v in raw.items():
            parts = k.rsplit(":", 1)
            if len(parts) == 2:
                subfield, stage = parts
                result.setdefault(subfield, {})[stage] = v
        return result

    # ------------------------------------------------------------------

    def _all_counts(self) -> dict[str, int]:
        if self._redis:
            try:
                raw = self._redis.hgetall(_REDIS_KEY)
                return {k: int(v) for k, v in raw.items()}
            except Exception:
                pass
        return dict(self._local)
