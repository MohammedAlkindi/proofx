#!/usr/bin/env python3
"""Enumerate Goldbach prime partitions for one even integer."""

from __future__ import annotations

import argparse
import json
import sys
import time
from typing import Any

try:
    import numpy as np  # type: ignore

    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False


def discover() -> dict[str, str]:
    """Return component discovery metadata."""
    return {"component": "PartitionEnumerator"}


def metadata() -> dict[str, Any]:
    """Return component metadata."""
    return {
        "version": "1.0.0",
        "author": "GoldbachX Team",
        "description": "Enumerates prime pairs summing to n",
        "dependencies": {"numpy": "optional"},
    }


def filters_signature() -> dict[str, tuple[str, type, object]]:
    """Return supported filters and their metadata."""
    return {
        "allow_equal": ("Allow p=q pairs", bool, True),
        "exclude_twins": ("Exclude twin primes", bool, False),
        "unique": ("Return unique pairs only", bool, True),
    }


def _is_prime_trial(candidate: int) -> bool:
    """Small deterministic primality check for validating sieve completeness."""
    if candidate < 2:
        return False
    if candidate == 2:
        return True
    if candidate % 2 == 0:
        return False

    factor = 3
    while factor * factor <= candidate:
        if candidate % factor == 0:
            return False
        factor += 2
    return True


def _validate_input(n: int, primes: list[int]) -> None:
    """Validate that ``primes`` is a sorted sieve covering every prime up to ``n``."""
    if n < 4 or n % 2 != 0:
        raise ValueError("n must be an even integer >= 4")
    if not primes:
        raise ValueError("Primes list cannot be empty")
    if primes[0] < 2:
        raise ValueError("Primes must be >= 2")
    if not all(p < q for p, q in zip(primes, primes[1:], strict=False)):
        raise ValueError("Primes must be sorted and unique")

    primes_up_to_n = [p for p in primes if p <= n]
    expected = [p for p in range(2, n + 1) if _is_prime_trial(p)]
    if primes_up_to_n != expected:
        raise ValueError("Primes must contain every prime <= n")


def _is_twin_prime(p: int, q: int, primes_set: set[int]) -> bool:
    """Return whether ``p`` and ``q`` are twin-prime neighbors."""
    return abs(p - q) == 2 and (p + 2 in primes_set or q + 2 in primes_set)


def enumerate_partitions(
    n: int,
    primes: list[int],
    *,
    allow_equal: bool = True,
    exclude_twins: bool = False,
    unique: bool = True,
) -> list[tuple[int, int]]:
    """Enumerate prime pairs ``(p, q)`` with ``p + q = n``.

    ``primes`` may extend beyond ``n`` when it comes from a larger sieve; those
    extra values are ignored after validation.
    """
    _validate_input(n, primes)

    bounded_primes = [p for p in primes if p <= n]
    primes_set = set(bounded_primes)
    result: list[tuple[int, int]] = []
    seen: set[tuple[int, int]] = set()

    if HAS_NUMPY:
        primes_arr = np.array(bounded_primes)
        complements = n - primes_arr
        valid_mask = np.isin(complements, primes_arr)
        candidates = primes_arr[valid_mask].tolist()
    else:
        candidates = [p for p in bounded_primes if (n - p) in primes_set]

    for p in candidates:
        q = n - p

        if not allow_equal and p == q:
            continue
        if exclude_twins and _is_twin_prime(p, q, primes_set):
            continue

        pair = (p, q) if not unique or p <= q else (q, p)
        if unique and pair in seen:
            continue

        seen.add(pair)
        result.append(pair)

    result.sort()
    return result


def count_partitions(n: int, primes: list[int], **filters: Any) -> int:
    """Count prime pairs summing to ``n`` with optional filters."""
    return len(enumerate_partitions(n, primes, **filters))


def _primes_up_to(limit: int) -> list[int]:
    """Generate primes up to ``limit`` for the command-line interface."""
    if limit < 2:
        return []

    sieve = [True] * (limit + 1)
    sieve[0] = sieve[1] = False
    for i in range(2, int(limit**0.5) + 1):
        if sieve[i]:
            sieve[i * i :: i] = [False] * len(sieve[i * i :: i])
    return [i for i, is_prime in enumerate(sieve) if is_prime]


def _cli() -> None:
    """Command-line interface."""
    parser = argparse.ArgumentParser(description="Goldbach partition enumerator")
    parser.add_argument("--n", type=int, required=True, help="Target even number >= 4")
    parser.add_argument(
        "--allow-equal",
        type=int,
        choices=[0, 1],
        default=1,
        help="Allow p=q pairs (default 1)",
    )
    parser.add_argument(
        "--exclude-twins",
        type=int,
        choices=[0, 1],
        default=0,
        help="Exclude twin primes (default 0)",
    )
    args = parser.parse_args()

    start_time = time.time()
    primes = _primes_up_to(args.n)

    try:
        pairs = enumerate_partitions(
            args.n,
            primes,
            allow_equal=bool(args.allow_equal),
            exclude_twins=bool(args.exclude_twins),
            unique=True,
        )
    except ValueError as exc:
        print(json.dumps({"error": str(exc)}), file=sys.stderr)
        sys.exit(1)

    output = {
        "n": args.n,
        "pairs": pairs,
        "count": len(pairs),
        "metrics": {
            "primes_count": len(primes),
            "elapsed_ms": int((time.time() - start_time) * 1000),
        },
    }
    print(json.dumps(output))


if __name__ == "__main__":
    _cli()
