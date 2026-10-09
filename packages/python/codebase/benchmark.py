"""Bounded Goldbach policy comparisons and independent artifact verification.

The exhaustive reference is an evaluation oracle, never an input to a policy.
Importing this module does not import the search engine or its ML dependencies.
"""

from __future__ import annotations

import hashlib
import json
import math
import platform
import statistics
import subprocess
import time
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any

SCHEMA = "proofx.goldbach_benchmark.v1"
POLICIES = ("directed", "uniform", "sequential")
ROOT = Path(__file__).resolve().parents[3]


@dataclass(frozen=True)
class BenchmarkConfig:
    max_n: int = 10_000
    budget: int = 64
    seeds: tuple[int, ...] = (0, 1, 2)

    def validate(self) -> None:
        if type(self.max_n) is not int or not 4 <= self.max_n <= 20_000 or self.max_n % 2:
            raise ValueError(
                "max_n must be an even integer in [4, 20000] for this bounded protocol"
            )
        if type(self.budget) is not int or not 1 <= self.budget <= self.max_n // 2 - 1:
            raise ValueError("budget must be positive and no larger than the finite domain")
        if not self.seeds or len(set(self.seeds)) != len(self.seeds):
            raise ValueError("seeds must be nonempty and distinct")
        if any(type(seed) is not int or seed < 0 for seed in self.seeds):
            raise ValueError("seeds must be non-negative integers")


def _json(data: Any) -> str:
    return json.dumps(data, sort_keys=True, allow_nan=False)


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_rows(path: Path, rows: list[dict[str, Any]]) -> str:
    path.write_text("".join(_json(row) + "\n" for row in rows), encoding="utf-8", newline="\n")
    return _digest(path)


def _git(*args: str) -> str | None:
    try:
        return subprocess.check_output(
            ["git", "-C", str(ROOT), *args],
            encoding="utf-8",
            errors="replace",
            stderr=subprocess.DEVNULL,
            timeout=10,
        ).strip()
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return None


def provenance() -> dict[str, Any]:
    dependencies: dict[str, str | None] = {}
    for name in ("numpy", "sympy", "scipy", "pandas", "scikit-learn", "mpmath", "numba"):
        try:
            dependencies[name] = version(name)
        except PackageNotFoundError:
            dependencies[name] = None
    status = _git("status", "--porcelain", "--untracked-files=no")
    sources = {
        path.relative_to(ROOT).as_posix(): _digest(path)
        for path in sorted((ROOT / "packages/python/codebase").rglob("*.py"))
    }
    return {
        "commit": _git("rev-parse", "HEAD"),
        "tracked_tree_dirty": bool(status) if status is not None else None,
        "python": platform.python_version(),
        "platform": platform.platform(),
        "machine": platform.machine(),
        "dependencies": dependencies,
        "source_sha256": sources,
    }


def select_candidates(policy: str, config: BenchmarkConfig, seed: int, engine: Any) -> list[int]:
    """Select without consulting reference counts or the outcome metric."""
    import numpy as np

    config.validate()
    rng = np.random.default_rng(seed)
    domain = list(range(4, config.max_n + 1, 2))
    if policy == "sequential":
        return domain[: config.budget]
    if policy == "uniform":
        return [int(n) for n in rng.choice(domain, size=config.budget, replace=False)]
    if policy != "directed":
        raise ValueError(f"Unknown policy: {policy}")
    selected = list(engine._generate_sparse_candidates(config.budget, rng, max_n=config.max_n))
    # Some bounded domains exhaust the engine's structural families. Make the
    # completion rule explicit so all policies get exactly the same budget.
    seen = set(selected)
    remaining = [n for n in domain if n not in seen]
    rng.shuffle(remaining)
    return (selected + remaining)[: config.budget]


def rare_candidates(reference: list[dict[str, Any]]) -> set[int]:
    """Bottom 5% by observed / asymptotic count, including boundary ties."""
    ratios = sorted(row["ratio"] for row in reference)
    threshold = ratios[max(0, math.ceil(0.05 * len(ratios)) - 1)]
    return {row["candidate"] for row in reference if row["ratio"] <= threshold}


def summarize(rows: list[dict[str, Any]], rare: set[int]) -> dict[str, Any]:
    hits = sum(row["candidate"] in rare for row in rows)
    return {
        "evaluated": len(rows),
        "rare_hits": hits,
        "rare_recall": hits / len(rare),
        "min_ratio": min(row["ratio"] for row in rows),
        "median_ratio": statistics.median(row["ratio"] for row in rows),
        "median_candidate": statistics.median(row["candidate"] for row in rows),
        "zero_partition_count": sum(row["actual_partitions"] == 0 for row in rows),
    }


def run_benchmark(config: BenchmarkConfig, output: Path) -> dict[str, Any]:
    from codebase.FalsificationEngine.FalsificationEngine import GoldbachFalsifier

    config.validate()
    # Never overwrite a published run. A failed run leaves a directory without
    # a manifest; only the final manifest marks a complete bundle.
    output.mkdir(parents=True, exist_ok=False)
    started = time.perf_counter()
    engine = GoldbachFalsifier(sieve_limit=config.max_n)
    sieve_seconds = time.perf_counter() - started
    started = time.perf_counter()
    reference = []
    for n in range(4, config.max_n + 1, 2):
        actual, witness = engine._partition_count_and_witness(n)
        expected = engine._hardy_littlewood_expected(n)
        reference.append(
            {
                "candidate": n,
                "actual_partitions": actual,
                "expected_partitions": expected,
                "ratio": actual / expected,
                "witness": list(witness) if witness else None,
            }
        )
    reference_seconds = time.perf_counter() - started
    reference_by_n = {row["candidate"]: row for row in reference}
    rare = rare_candidates(reference)
    artifacts = {"reference.jsonl": _write_rows(output / "reference.jsonl", reference)}
    runs = []
    for seed in config.seeds:
        for policy in POLICIES:
            started = time.perf_counter()
            candidates = select_candidates(policy, config, seed, engine)
            rows = []
            for n in candidates:
                # Re-evaluate selected candidates. The oracle is not used to
                # supply the count, so timing includes actual partition work.
                actual, witness = engine._partition_count_and_witness(n)
                expected = engine._hardy_littlewood_expected(n)
                rows.append(
                    {
                        "candidate": n,
                        "actual_partitions": actual,
                        "expected_partitions": expected,
                        "ratio": actual / expected,
                        "witness": list(witness) if witness else None,
                    }
                )
            elapsed = time.perf_counter() - started
            if any(row != reference_by_n[row["candidate"]] for row in rows):
                raise ValueError("Selected-candidate evaluation disagrees with reference")
            filename = f"{policy}-{seed}.jsonl"
            artifacts[filename] = _write_rows(output / filename, rows)
            runs.append(
                {
                    "policy": policy,
                    "seed": seed,
                    "ledger": filename,
                    "elapsed_s": elapsed,
                    **summarize(rows, rare),
                }
            )
    manifest = {
        "schema_version": SCHEMA,
        "created_at": datetime.now(UTC).isoformat(),
        "config": asdict(config),
        "provenance": provenance(),
        "protocol": "docs/experiments/goldbach-policy-comparison.md",
        "claim_level": "bounded_policy_comparison",
        "metric": "recall of bottom 5% observed/asymptotic unordered partition ratios; ties included",
        "reference_size": len(reference),
        "rare_set_size": len(rare),
        "sieve_seconds": sieve_seconds,
        "reference_seconds": reference_seconds,
        "timing_scope": "selection plus exact counts and ratios; excludes shared sieve, oracle and file I/O",
        "reproduce": (
            "python -m codebase.cli benchmark goldbach "
            f"--max-n {config.max_n} --budget {config.budget} "
            f"--seeds {' '.join(map(str, config.seeds))} --output-dir results/reproduction"
        ),
        "runs": runs,
        "artifacts": artifacts,
    }
    (output / "manifest.json").write_text(_json(manifest) + "\n", encoding="utf-8")
    return manifest


def _trial_primes(limit: int) -> list[int]:
    """Independent reference checker: trial division, no engine sieve imports."""
    return [n for n in range(2, limit + 1) if all(n % d for d in range(2, math.isqrt(n) + 1))]


def verify_bundle(directory: Path) -> dict[str, int]:
    """Recount every reference value and check ledgers, budgets and summaries.

    Checksums detect corruption, not authorship. This is a Python cross-check,
    not a Lean certificate or a proof of an unbounded conjecture.
    """
    manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    if manifest.get("schema_version") != SCHEMA:
        raise ValueError("Unsupported benchmark schema")
    config = BenchmarkConfig(**{**manifest["config"], "seeds": tuple(manifest["config"]["seeds"])})
    config.validate()
    expected_files = {"reference.jsonl"} | {
        f"{policy}-{seed}.jsonl" for policy in POLICIES for seed in config.seeds
    }
    if set(manifest["artifacts"]) != expected_files:
        raise ValueError("Artifact set does not match the protocol")
    data = {}
    for name in sorted(expected_files):
        path = directory / name
        if path.resolve().parent != directory.resolve() or path.is_symlink():
            raise ValueError("Artifact must be a local regular file")
        if _digest(path) != manifest["artifacts"][name]:
            raise ValueError(f"Checksum mismatch: {name}")
        data[name] = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    reference = data["reference.jsonl"]
    if [row["candidate"] for row in reference] != list(range(4, config.max_n + 1, 2)):
        raise ValueError("Reference does not cover the exact domain")
    primes = _trial_primes(config.max_n)
    prime_set = set(primes)
    for row in reference:
        n = row["candidate"]
        pairs = [(p, n - p) for p in primes if p <= n // 2 and n - p in prime_set]
        if row["actual_partitions"] != len(pairs) or row["witness"] != (
            list(pairs[0]) if pairs else None
        ):
            raise ValueError(f"Independent partition count/witness mismatch at {n}")
        correction = math.prod((p - 1) / (p - 2) for p in primes if p > 2 and n % p == 0)
        expected = 0.6601618158 * correction * n / math.log(n) ** 2
        if not math.isclose(row["expected_partitions"], expected, rel_tol=1e-12):
            raise ValueError(f"Expected-count mismatch at {n}")
        if not math.isclose(row["ratio"], len(pairs) / expected, rel_tol=1e-12):
            raise ValueError(f"Ratio mismatch at {n}")
    rare = rare_candidates(reference)
    if manifest["reference_size"] != len(reference) or manifest["rare_set_size"] != len(rare):
        raise ValueError("Reference summary mismatch")
    by_n = {row["candidate"]: row for row in reference}
    expected_runs = {(policy, seed) for policy in POLICIES for seed in config.seeds}
    seen = set()
    for run in manifest["runs"]:
        key = (run["policy"], run["seed"])
        if key not in expected_runs or key in seen:
            raise ValueError("Unexpected or duplicate run")
        seen.add(key)
        if run["ledger"] != f"{key[0]}-{key[1]}.jsonl":
            raise ValueError("Run points to the wrong ledger")
        rows = data[run["ledger"]]
        if len(rows) != config.budget or len({row["candidate"] for row in rows}) != config.budget:
            raise ValueError("Ledger violates the unique evaluation budget")
        if any(row != by_n.get(row["candidate"]) for row in rows):
            raise ValueError("Ledger disagrees with independent reference")
        if any(run.get(k) != v for k, v in summarize(rows, rare).items()):
            raise ValueError("Run summary disagrees with ledger")
    if seen != expected_runs:
        raise ValueError("Missing runs")
    return {
        "reference_candidates": len(reference),
        "runs": len(seen),
        "evaluations": config.budget * len(seen),
    }
