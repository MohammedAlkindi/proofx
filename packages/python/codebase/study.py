"""GB-002: fixed-domain, size-stratified Goldbach policy study.

Run with ``python -m codebase.study run OUTPUT``; check with ``verify OUTPUT``.
The frozen protocol is deliberately separate from results and implementation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import platform
import statistics
import subprocess
from collections.abc import Iterator
from fractions import Fraction
from importlib.resources import files
from pathlib import Path

import numpy as np

from codebase.study_stats import bucket_moments, simultaneous_interval

FAMILIES = ("power_two", "twice_prime", "mod30", "mod6")
POLICIES = ("uniform", "ascending", "priority", *(f"without_{f}" for f in FAMILIES))
INTERVALS = ((10002, 12000), (15002, 17000), (18002, 20000))
BUDGETS = (20, 50, 100)
REPLICATES = 2048


def encode(value: object) -> str:
    return json.dumps(value, sort_keys=True, allow_nan=False, separators=(",", ":")) + "\n"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def protocol_text() -> str:
    return files("codebase").joinpath("protocols/gb-002-v1.json").read_text(encoding="utf-8")


def validate_protocol() -> None:
    expected = {
        "schema_version": "proofx.controlled_goldbach.v1",
        "experiment_id": "GB-002",
        "version": 1,
        "intervals": [list(pair) for pair in INTERVALS],
        "stratum_width": 200,
        "budgets": list(BUDGETS),
        "replicates": REPLICATES,
        "seed_start": 0,
        "alpha": 0.05,
        "target_fraction": 0.05,
        "family_order": list(FAMILIES),
        "policies": list(POLICIES),
        "rng": "Generator(PCG64DXSM(SeedSequence([seed,lower,upper,stratum_lower]))).random(N)",
        "endpoint": "recall_of_within_stratum_low_ratio_targets",
        "primary_analysis": "exact_finite_population_policy_expectation_and_variance",
        "interval_method": "paired_empirical_bernstein_bonferroni_two_sided",
        "stopping_rule": "fixed_replicates_no_optional_stopping",
    }
    if encode(json.loads(protocol_text())) != encode(expected):
        raise ValueError("implementation and packaged protocol disagree")


def prime_set(limit: int, *, independent: bool = False) -> set[int]:
    if independent:
        return {n for n in range(2, limit + 1) if all(n % d for d in range(2, math.isqrt(n) + 1))}
    sieve = bytearray(b"\x01") * (limit + 1)
    sieve[:2] = b"\x00\x00"
    for p in range(2, math.isqrt(limit) + 1):
        if sieve[p]:
            sieve[p * p :: p] = b"\x00" * ((limit - p * p) // p + 1)
    return {n for n, flag in enumerate(sieve) if flag}


def family_memberships(n: int, primes: set[int]) -> tuple[bool, ...]:
    return (n & (n - 1) == 0, n // 2 in primes, n % 30 == 2, n % 6 == 2)


def buckets(domain: list[int], policy: str, primes: set[int]) -> list[list[int]]:
    """Selection receives no oracle counts or target labels."""
    if policy not in POLICIES:
        raise ValueError("unknown policy")
    if policy == "ascending":
        return [[n] for n in domain]
    if policy == "uniform":
        return [domain]
    groups: list[list[int]] = [[] for _ in range(len(FAMILIES) + 1)]
    for n in domain:
        group = next(
            (
                i
                for i, member in enumerate(family_memberships(n, primes))
                if member and policy != f"without_{FAMILIES[i]}"
            ),
            len(FAMILIES),
        )
        groups[group].append(n)
    return groups


def ranking(
    groups: list[list[int]], domain: list[int], seed: int, lower: int, upper: int
) -> list[int]:
    rng = np.random.Generator(
        np.random.PCG64DXSM(np.random.SeedSequence([seed, lower, upper, domain[0]]))
    )
    keys = dict(zip(domain, rng.random(len(domain)), strict=True))
    return [n for group in groups for n in sorted(group, key=lambda n: (keys[n], n))]


def reference_rows(primes: set[int]) -> list[dict[str, object]]:
    ordered = sorted(primes)
    rows: list[dict[str, object]] = []
    for lower, upper in INTERVALS:
        for n in range(lower, upper + 1, 2):
            witnesses = [p for p in ordered if p <= n // 2 and n - p in primes]
            correction = math.prod((p - 1) / (p - 2) for p in ordered if p > 2 and n % p == 0)
            expected = 0.6601618158 * n / math.log(n) ** 2 * correction
            rows.append(
                {
                    "candidate": n,
                    "count": len(witnesses),
                    "witness": [witnesses[0], n - witnesses[0]] if witnesses else None,
                    "expected": expected,
                    "ratio": len(witnesses) / expected,
                }
            )
    return rows


def strata(lower: int, upper: int) -> Iterator[list[int]]:
    for start in range(lower, upper + 1, 200):
        yield list(range(start, start + 200, 2))


def target_sets(reference: list[dict[str, object]]) -> dict[int, set[int]]:
    ratios = {int(str(row["candidate"])): float(str(row["ratio"])) for row in reference}
    result = {}
    for lower, upper in INTERVALS:
        for domain in strata(lower, upper):
            threshold = sorted(ratios[n] for n in domain)[4]
            result[domain[0]] = {n for n in domain if ratios[n] <= threshold}
    return result


def rational(value: Fraction) -> dict[str, int | float]:
    return {"numerator": value.numerator, "denominator": value.denominator, "value": float(value)}


def selections(primes: set[int]) -> Iterator[dict[str, object]]:
    for lower, upper in INTERVALS:
        domains = list(strata(lower, upper))
        groups = {
            policy: [buckets(domain, policy, primes) for domain in domains] for policy in POLICIES
        }
        for seed in range(REPLICATES):
            for policy in POLICIES:
                selected = [
                    ranking(group, domain, seed, lower, upper)[:10]
                    for group, domain in zip(groups[policy], domains, strict=True)
                ]
                yield {
                    "lower": lower,
                    "upper": upper,
                    "seed": seed,
                    "policy": policy,
                    "strata": selected,
                }


def analysis(
    reference: list[dict[str, object]], ledger: Path, primes: set[int]
) -> dict[str, object]:
    targets = target_sets(reference)
    recalls: dict[tuple[int, str, int], list[float]] = {
        (lower, policy, budget): []
        for lower, _ in INTERVALS
        for policy in POLICIES
        for budget in BUDGETS
    }
    identical = {
        (lower, policy, budget): 0
        for lower, _ in INTERVALS
        for policy in POLICIES
        for budget in BUDGETS
    }
    paired: dict[tuple[int, int], list[list[int]]] = {}
    with ledger.open(encoding="utf-8") as stream:
        for line in stream:
            row = json.loads(line)
            lower, policy, seed = row["lower"], row["policy"], row["seed"]
            domains = list(strata(lower, row["upper"]))
            total = sum(len(targets[d[0]]) for d in domains)
            selected = row["strata"]
            if policy == "priority":
                paired[lower, seed] = selected
            for budget in BUDGETS:
                q = budget // 10
                hits = sum(
                    sum(n in targets[d[0]] for n in selection[:q])
                    for d, selection in zip(domains, selected, strict=True)
                )
                recalls[lower, policy, budget].append(hits / total)
                if policy.startswith("without_"):
                    identical[lower, policy, budget] += all(
                        set(a[:q]) == set(b[:q])
                        for a, b in zip(selected, paired[lower, seed], strict=True)
                    )
    summaries = []
    exact: dict[tuple[int, str, int], Fraction] = {}
    for lower, upper in INTERVALS:
        domains = list(strata(lower, upper))
        total = sum(len(targets[d[0]]) for d in domains)
        for policy in POLICIES:
            for budget in BUDGETS:
                moments = [
                    bucket_moments(
                        [(len(g), len(set(g) & targets[d[0]])) for g in buckets(d, policy, primes)],
                        budget // 10,
                    )
                    for d in domains
                ]
                mean = sum((m.mean for m in moments), Fraction(0)) / total
                variance = sum((m.variance for m in moments), Fraction(0)) / total**2
                exact[lower, policy, budget] = mean
                samples = recalls[lower, policy, budget]
                summaries.append(
                    {
                        "lower": lower,
                        "upper": upper,
                        "policy": policy,
                        "budget": budget,
                        "targets": total,
                        "expected_recall": rational(mean),
                        "recall_variance": rational(variance),
                        "sample_mean": statistics.mean(samples),
                        "sample_sd": statistics.stdev(samples),
                        "identical_to_priority": identical[lower, policy, budget] / REPLICATES
                        if policy.startswith("without_")
                        else None,
                    }
                )
    contrasts = []
    for lower, upper in INTERVALS:
        for budget in BUDGETS:
            for policy in POLICIES:
                if policy == "priority":
                    continue
                difference = exact[lower, "priority", budget] - exact[lower, policy, budget]
                samples = [
                    a - b
                    for a, b in zip(
                        recalls[lower, "priority", budget],
                        recalls[lower, policy, budget],
                        strict=True,
                    )
                ]
                lo, hi = simultaneous_interval(samples, 54)
                contrasts.append(
                    {
                        "lower": lower,
                        "upper": upper,
                        "budget": budget,
                        "comparison": policy,
                        "exact_difference": rational(difference),
                        "monte_carlo_interval": [lo, hi],
                        "contains_exact": lo <= float(difference) <= hi,
                    }
                )
    support = [
        {
            "lower": d[0],
            "upper": d[-1],
            "targets": sorted(targets[d[0]]),
            "target_count": len(targets[d[0]]),
            "threshold": sorted(
                float(str(row["ratio"]))
                for row in reference
                if d[0] <= int(str(row["candidate"])) <= d[-1]
            )[4],
            "family_support": {
                family: sum(family_memberships(n, primes)[i] for n in d)
                for i, family in enumerate(FAMILIES)
            },
        }
        for lower, upper in INTERVALS
        for d in strata(lower, upper)
    ]
    return {
        "policies": summaries,
        "contrasts": contrasts,
        "strata": support,
        "scope": "Exact expectations on fixed integers under ideal random bucket orderings; simulation bounds are conditional diagnostics, not generalization guarantees.",
    }


def run(output: Path) -> None:
    validate_protocol()
    sources = {
        name: Path(__file__).with_name(name).read_bytes()
        for name in ("study.py", "study_stats.py", "study_check.py")
    }
    provenance = source_revision()
    output.mkdir(parents=True, exist_ok=False)
    (output / "protocol.json").write_text(protocol_text(), encoding="utf-8", newline="\n")
    primes = prime_set(20000)
    reference = reference_rows(primes)
    (output / "reference.json").write_text(encode(reference), encoding="utf-8", newline="\n")
    with (output / "selections.jsonl").open("w", encoding="utf-8", newline="\n") as stream:
        for row in selections(primes):
            stream.write(encode(row))
    (output / "analysis.json").write_text(
        encode(analysis(reference, output / "selections.jsonl", primes)),
        encoding="utf-8",
        newline="\n",
    )
    for name, content in sources.items():
        if Path(__file__).with_name(name).read_bytes() != content:
            raise ValueError("source changed during execution; rerun in a stable checkout")
        (output / name).write_bytes(content)
    artifacts = {p.name: digest(p) for p in sorted(output.iterdir())}
    (output / "manifest.json").write_text(
        encode(
            {
                "experiment": "GB-002",
                "version": 1,
                "python": platform.python_version(),
                "numpy": np.__version__,
                "source": provenance,
                "artifacts": artifacts,
            }
        ),
        encoding="utf-8",
        newline="\n",
    )


def source_revision() -> dict[str, str | bool | None]:
    root = Path(__file__).resolve().parents[3]
    # Installed wheels have no repository provenance; never label them with the
    # caller's unrelated current working directory or an enclosing repository.
    if not (root / "pyproject.toml").is_file() or not (root / ".git").exists():
        return {"commit": None, "dirty": None}
    try:
        commit = subprocess.check_output(
            ["git", "-C", str(root), "rev-parse", "HEAD"], text=True, timeout=10
        ).strip()
        status = subprocess.check_output(
            ["git", "-C", str(root), "status", "--porcelain", "--", "packages/python/codebase"],
            text=True,
            timeout=10,
        ).strip()
        return {"commit": commit, "dirty": bool(status)}
    except (OSError, subprocess.SubprocessError):
        return {"commit": None, "dirty": None}


def verify(output: Path) -> dict[str, int]:
    validate_protocol()
    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    expected_files = {
        "protocol.json",
        "reference.json",
        "selections.jsonl",
        "analysis.json",
        "study.py",
        "study_stats.py",
        "study_check.py",
    }
    if (
        manifest.get("experiment") != "GB-002"
        or manifest.get("version") != 1
        or set(manifest["artifacts"]) != expected_files
    ):
        raise ValueError("unexpected experiment or artifact set")
    for name in expected_files:
        path = output / name
        if path.is_symlink() or digest(path) != manifest["artifacts"][name]:
            raise ValueError(f"checksum mismatch: {name}")
    if (output / "protocol.json").read_text(encoding="utf-8") != protocol_text():
        raise ValueError("protocol differs from frozen GB-002 v1")
    reference = json.loads((output / "reference.json").read_text(encoding="utf-8"))
    primes = prime_set(20000, independent=True)
    if encode(reference) != encode(reference_rows(primes)):
        raise ValueError("independent reference recount failed")
    count = 0
    with (output / "selections.jsonl").open(encoding="utf-8") as stream:
        for actual, expected in zip(stream, selections(primes), strict=True):
            if encode(json.loads(actual)) != encode(expected):
                raise ValueError("policy replay failed")
            count += 1
    observed = json.loads((output / "analysis.json").read_text(encoding="utf-8"))
    if encode(observed) != encode(analysis(reference, output / "selections.jsonl", primes)):
        raise ValueError("analysis recomputation failed")
    from codebase.study_check import check_arithmetic

    check_arithmetic(output)
    return {"reference_inputs": len(reference), "policy_replicates": count, "contrasts": 54}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("run", "verify"))
    parser.add_argument("directory", type=Path)
    args = parser.parse_args()
    if args.action == "run":
        run(args.directory)
    else:
        print(encode(verify(args.directory)), end="")


if __name__ == "__main__":
    main()
