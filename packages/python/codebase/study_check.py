"""Independent GB-002 arithmetic check, using trial division and indicators.

No imports from the generator or its moment implementation. Policy replay is
handled separately: this checks reference arithmetic and exact marginal moments.
"""

from __future__ import annotations

import json
import math
from fractions import Fraction
from pathlib import Path


def is_prime(n: int) -> bool:
    return n >= 2 and all(n % d for d in range(2, math.isqrt(n) + 1))


def check_arithmetic(directory: Path) -> None:
    config = json.loads((directory / "protocol.json").read_text(encoding="utf-8"))
    reference = json.loads((directory / "reference.json").read_text(encoding="utf-8"))
    report = json.loads((directory / "analysis.json").read_text(encoding="utf-8"))
    limit = max(upper for _, upper in config["intervals"])
    primes = {n for n in range(2, limit + 1) if is_prime(n)}
    ratios: dict[int, float] = {}
    for row in reference:
        n = row["candidate"]
        pairs = [(p, n - p) for p in range(2, n // 2 + 1) if p in primes and n - p in primes]
        if row["count"] != len(pairs) or row["witness"] != (list(pairs[0]) if pairs else None):
            raise ValueError(f"independent pair enumeration failed at {n}")
        residue, correction = n, 1.0
        while residue % 2 == 0:
            residue //= 2
        divisor = 3
        while divisor * divisor <= residue:
            if residue % divisor == 0:
                correction *= (divisor - 1) / (divisor - 2)
                while residue % divisor == 0:
                    residue //= divisor
            divisor += 2
        if residue > 1:
            correction *= (residue - 1) / (residue - 2)
        expected = 0.6601618158 * n / math.log(n) ** 2 * correction
        ratios[n] = len(pairs) / expected
        if not math.isclose(row["expected"], expected, rel_tol=1e-13) or not math.isclose(
            row["ratio"], ratios[n], rel_tol=1e-13
        ):
            raise ValueError(f"independent factorization failed at {n}")

    exact: dict[tuple[int, str, int], tuple[Fraction, Fraction]] = {}
    for lower, upper in config["intervals"]:
        domains = [
            list(range(start, start + config["stratum_width"], 2))
            for start in range(lower, upper + 1, config["stratum_width"])
        ]
        targets = [
            {
                n
                for n in domain
                if ratios[n]
                <= sorted(ratios[m] for m in domain)[
                    math.ceil(config["target_fraction"] * len(domain)) - 1
                ]
            }
            for domain in domains
        ]
        total = sum(map(len, targets))
        for policy in config["policies"]:
            for budget in config["budgets"]:
                mean, variance = Fraction(0), Fraction(0)
                for domain, target in zip(domains, targets, strict=True):
                    ranks: dict[int, int] = {}
                    for n in domain:
                        if policy == "uniform":
                            ranks[n] = 0
                        elif policy == "ascending":
                            ranks[n] = n
                        else:
                            flags = [
                                n > 0 and n & (n - 1) == 0,
                                n // 2 in primes,
                                n % 30 == 2,
                                n % 6 == 2,
                            ]
                            ranks[n] = min(
                                (
                                    i
                                    for i in range(4)
                                    if flags[i] and policy != "without_" + config["family_order"][i]
                                ),
                                default=4,
                            )
                    remaining = budget // len(domains)
                    for rank in sorted(set(ranks.values())):
                        group = {n for n in domain if ranks[n] == rank}
                        size, hits = len(group), len(group & target)
                        take = min(remaining, size)
                        remaining -= take
                        inclusion = Fraction(take, size)
                        mean += hits * inclusion
                        variance += hits * inclusion * (1 - inclusion)
                        if size > 1:
                            joint = Fraction(take * (take - 1), size * (size - 1))
                            variance += hits * (hits - 1) * (joint - inclusion**2)
                exact[lower, policy, budget] = mean / total, variance / total**2
    for row in report["policies"]:
        moments = exact[row["lower"], row["policy"], row["budget"]]
        for index, key in enumerate(("expected_recall", "recall_variance")):
            value = row[key]
            if moments[index] != Fraction(value["numerator"], value["denominator"]):
                raise ValueError(f"independent inclusion-indicator {key} check failed")
    for row in report["contrasts"]:
        delta = (
            exact[row["lower"], "priority", row["budget"]][0]
            - exact[row["lower"], row["comparison"], row["budget"]][0]
        )
        value = row["exact_difference"]
        if delta != Fraction(value["numerator"], value["denominator"]):
            raise ValueError("independent contrast check failed")
