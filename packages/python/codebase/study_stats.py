"""Exact moments for ordered-bucket sampling and Monte Carlo diagnostics."""

from __future__ import annotations

import math
import statistics
from collections.abc import Sequence
from dataclasses import dataclass
from fractions import Fraction


@dataclass(frozen=True)
class Moments:
    mean: Fraction
    variance: Fraction


def bucket_moments(buckets: Sequence[tuple[int, int]], quota: int) -> Moments:
    """Moments of target hits when ordered buckets are sampled without replacement.

    Each pair is (population size, target count). Complete buckets are selected
    deterministically; at most one boundary bucket is sampled uniformly.
    """
    if type(quota) is not int or not 0 <= quota <= sum(n for n, _ in buckets):
        raise ValueError("quota must be an integer within the population")
    mean, variance = Fraction(0), Fraction(0)
    remaining = quota
    for n, k in buckets:
        if type(n) is not int or type(k) is not int or not 0 <= k <= n:
            raise ValueError("bucket sizes and target counts must be nonnegative integers")
        q = min(remaining, n)
        if n:
            mean += Fraction(q * k, n)
            if n > 1:
                variance += Fraction(q * k * (n - k) * (n - q), n * n * (n - 1))
        remaining -= q
    return Moments(mean, variance)


def simultaneous_interval(
    differences: Sequence[float], comparisons: int, alpha: float = 0.05
) -> tuple[float, float]:
    """Paired empirical Bernstein bound for differences in [-1, 1].

    Maurer--Pontil (2009), Theorem 4, transformed from [0,1], with a union
    bound over two tails and every declared comparison. Assumes iid replicates.
    """
    if len(differences) < 2 or any(not -1 <= d <= 1 for d in differences):
        raise ValueError("need at least two finite differences in [-1, 1]")
    if type(comparisons) is not int or comparisons < 1 or not 0 < alpha < 1:
        raise ValueError("invalid comparison count or alpha")
    count = len(differences)
    log_term = math.log(4 * comparisons / alpha)
    radius = math.sqrt(2 * statistics.variance(differences) * log_term / count)
    radius += 14 * log_term / (3 * (count - 1))
    mean = statistics.mean(differences)
    return max(-1.0, mean - radius), min(1.0, mean + radius)
