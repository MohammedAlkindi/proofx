"""Verified run artifact helpers for small, reproducible ProofX checks.

These routines intentionally run small deterministic inspections. They are not
full engine replacements; they produce compact artifacts that bind a claim level,
input bound, seed, dependency versions, and result summary to the public site.
"""

from __future__ import annotations

import json
import math
import os
import platform
import subprocess
import time
from datetime import UTC, datetime
from importlib import metadata
from pathlib import Path
from typing import Any

# v2 replaced null dependency versions with an explicit dependencies_unresolved
# list plus a dependencies_complete flag, so a degraded build environment can no
# longer masquerade as a complete provenance snapshot.
SCHEMA_VERSION = "proofx.verified_run.v2"
DEFAULT_DEPENDENCIES = (
    "mpmath",
    "numpy",
    "sympy",
    "scipy",
    "pandas",
    "scikit-learn",
    "numba",
)


def build_verified_run_bundle(
    *,
    engines: tuple[str, ...] = ("collatz", "goldbach", "riemann"),
    seed: int = 42,
    collatz_start: int = 1,
    collatz_end: int = 128,
    collatz_fuel: int = 10_000,
    goldbach_start: int = 4,
    goldbach_end: int = 256,
    riemann_limit: int = 10_000,
) -> dict[str, Any]:
    """Build a bundle of deterministic run artifacts."""
    normalized = tuple(engine.lower() for engine in engines)
    unknown = sorted(set(normalized) - {"collatz", "goldbach", "riemann"})
    if unknown:
        raise ValueError(f"Unknown engine(s): {', '.join(unknown)}")

    environment = _environment()
    commit = _commit_info()
    generated_at = datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")

    runs: list[dict[str, Any]] = []
    if "collatz" in normalized:
        runs.append(
            run_collatz_artifact(
                seed=seed,
                start=collatz_start,
                end=collatz_end,
                fuel=collatz_fuel,
                environment=environment,
                commit=commit,
            )
        )
    if "goldbach" in normalized:
        runs.append(
            run_goldbach_artifact(
                seed=seed,
                start_even=goldbach_start,
                end_even=goldbach_end,
                environment=environment,
                commit=commit,
            )
        )
    if "riemann" in normalized:
        runs.append(
            run_riemann_artifact(
                seed=seed,
                limit=riemann_limit,
                environment=environment,
                commit=commit,
            )
        )

    bundle = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": generated_at,
        "commit": commit,
        "environment": environment,
        "runs": runs,
    }
    validate_bundle(bundle)
    return bundle


def write_bundle(bundle: dict[str, Any], output_path: Path) -> None:
    """Write a verified run bundle as stable pretty JSON."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(bundle, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def validate_bundle(bundle: dict[str, Any]) -> None:
    """Validate the public artifact shape used by the CLI and website."""
    if bundle.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("Unsupported verified run schema version")
    runs = bundle.get("runs")
    if not isinstance(runs, list) or not runs:
        raise ValueError("Verified run bundle must contain at least one run")

    required = {
        "id",
        "engine",
        "claim_level",
        "status",
        "seed",
        "bounds",
        "summary",
        "metrics",
        "samples",
        "elapsed_s",
        "reproduce",
        "environment",
        "commit",
    }
    for run in runs:
        if not isinstance(run, dict):
            raise ValueError("Run entries must be objects")
        missing = sorted(required - run.keys())
        if missing:
            raise ValueError(f"Run {run.get('id', '<unknown>')} missing: {', '.join(missing)}")

    # Structural checks above report the absent field by name; environment
    # checks run afterwards so a wholly missing block is reported as a missing
    # field rather than as a malformed environment.
    _validate_environment(bundle.get("environment"), "bundle")
    for run in runs:
        _validate_environment(run.get("environment"), f"run {run.get('id', '<unknown>')}")


def _validate_environment(environment: Any, where: str) -> None:
    """Reject an environment block that cannot support a provenance claim."""
    if not isinstance(environment, dict):
        raise ValueError(f"Verified run environment for {where} must be an object")

    missing = sorted(
        {"python", "platform", "dependencies", "dependencies_complete"} - environment.keys()
    )
    if missing:
        raise ValueError(f"Verified run environment for {where} missing: {', '.join(missing)}")

    dependencies = environment["dependencies"]
    if not isinstance(dependencies, dict):
        raise ValueError(f"Verified run dependencies for {where} must be an object")

    nulls = sorted(name for name, version in dependencies.items() if version is None)
    if nulls:
        raise ValueError(
            f"Verified run dependency versions for {where} must not be null: {', '.join(nulls)}. "
            "Unresolved packages belong in dependencies_unresolved."
        )


def environment_is_complete(bundle: dict[str, Any]) -> bool:
    """Report whether every declared dependency resolved when the bundle was built.

    An incomplete bundle is still a valid artifact -- it just cannot claim a full
    dependency snapshot, so callers that publish provenance should say so.
    """
    environments = [bundle.get("environment")]
    environments.extend(run.get("environment") for run in bundle.get("runs", []))
    return all(
        isinstance(environment, dict) and environment.get("dependencies_complete") is True
        for environment in environments
    )


def publish_bundle(bundle: dict[str, Any], output_path: Path) -> tuple[bool, str]:
    """Write ``bundle`` unless doing so would downgrade published provenance.

    The site build regenerates this artifact on every deploy. A deploy
    environment without the Python requirements installed still produces a
    structurally valid bundle, just one that resolved no dependency versions.
    Writing it would replace a complete committed snapshot with a weaker one,
    so an incomplete rebuild yields to whatever complete artifact is already
    on disk.

    Returns ``(written, reason)``.
    """
    if environment_is_complete(bundle):
        write_bundle(bundle, output_path)
        return True, "environment resolved every declared dependency"

    unresolved = ", ".join(bundle.get("environment", {}).get("dependencies_unresolved", []))
    if _existing_bundle_is_complete(output_path):
        return False, (
            f"kept the existing artifact: this environment could not resolve {unresolved}, "
            "so rebuilding would publish weaker provenance than what is committed"
        )

    write_bundle(bundle, output_path)
    return True, f"wrote an incomplete snapshot: could not resolve {unresolved}"


def _existing_bundle_is_complete(output_path: Path) -> bool:
    try:
        existing = json.loads(output_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    return isinstance(existing, dict) and environment_is_complete(existing)


def run_collatz_artifact(
    *,
    seed: int,
    start: int,
    end: int,
    fuel: int,
    environment: dict[str, Any] | None = None,
    commit: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Inspect Collatz trajectories for every integer in a finite interval."""
    if start < 1:
        raise ValueError("Collatz start must be >= 1")
    if end < start:
        raise ValueError("Collatz end must be >= start")
    if fuel < 1:
        raise ValueError("Collatz fuel must be positive")

    started = time.perf_counter()
    traces = [_collatz_trace(n, fuel) for n in range(start, end + 1)]
    elapsed = time.perf_counter() - started

    converged = [trace for trace in traces if trace["converged"]]
    top_by_stopping = sorted(traces, key=lambda item: (item["steps"], item["peak"]), reverse=True)[
        :8
    ]
    top_by_peak = max(traces, key=lambda item: item["peak"])
    all_converged = len(converged) == len(traces)
    status = "no_counterexample_found" if all_converged else "fuel_limit_hit"

    return _run_artifact(
        run_id=f"collatzx-{start}-{end}-fuel-{fuel}",
        engine="CollatzX",
        claim_level="bounded_run",
        status=status,
        seed=seed,
        bounds={"start": start, "end": end, "fuel": fuel, "inputs_checked": len(traces)},
        summary=(
            f"Checked Collatz trajectories for {len(traces)} starts from {start} to {end}; "
            f"{len(converged)} reached 1 within {fuel} steps."
        ),
        metrics={
            "inputs_checked": len(traces),
            "converged": len(converged),
            "max_stopping_time": max(trace["steps"] for trace in traces),
            "peak_value": top_by_peak["peak"],
            "peak_start": top_by_peak["n"],
        },
        samples=top_by_stopping,
        elapsed_s=elapsed,
        reproduce=(
            "python -m codebase.cli run collatz "
            f"--start {start} --end {end} --fuel {fuel} --seed {seed} "
            "--output-json src/verified-runs.json"
        ),
        environment=environment,
        commit=commit,
    )


def run_goldbach_artifact(
    *,
    seed: int,
    start_even: int,
    end_even: int,
    environment: dict[str, Any] | None = None,
    commit: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Inspect Goldbach decompositions for every even integer in a finite interval."""
    if start_even < 4 or start_even % 2:
        raise ValueError("Goldbach start must be an even integer >= 4")
    if end_even < start_even or end_even % 2:
        raise ValueError("Goldbach end must be an even integer >= start")

    started = time.perf_counter()
    primes = _prime_sieve(end_even)
    prime_set = set(primes)
    rows: list[dict[str, Any]] = []
    for value in range(start_even, end_even + 1, 2):
        pairs = _goldbach_pairs(value, prime_set)
        rows.append(
            {
                "n": value,
                "partition_count": len(pairs),
                "first_pair": list(pairs[0]) if pairs else None,
                "widest_gap": max((pair[1] - pair[0] for pair in pairs), default=0),
            }
        )
    elapsed = time.perf_counter() - started

    partition_counts = [int(row["partition_count"]) for row in rows]
    zeros = [int(row["n"]) for row in rows if int(row["partition_count"]) == 0]
    sparsest = sorted(rows, key=lambda item: (item["partition_count"], item["n"]))[:8]
    status = "no_counterexample_found" if not zeros else "counterexample_candidate_found"

    return _run_artifact(
        run_id=f"goldbachx-{start_even}-{end_even}",
        engine="GoldbachX",
        claim_level="bounded_run",
        status=status,
        seed=seed,
        bounds={
            "start_even": start_even,
            "end_even": end_even,
            "even_inputs_checked": len(rows),
        },
        summary=(
            f"Checked Goldbach decompositions for {len(rows)} even inputs from "
            f"{start_even} to {end_even}; {len(zeros)} inputs had no partition."
        ),
        metrics={
            "even_inputs_checked": len(rows),
            "zero_partition_inputs": len(zeros),
            "min_partition_count": min(partition_counts),
            "max_partition_count": max(partition_counts),
            "prime_count": len(primes),
        },
        samples=sparsest,
        elapsed_s=elapsed,
        reproduce=(
            "python -m codebase.cli run goldbach "
            f"--start-even {start_even} --end-even {end_even} --seed {seed} "
            "--output-json src/verified-runs.json"
        ),
        environment=environment,
        commit=commit,
    )


def run_riemann_artifact(
    *,
    seed: int,
    limit: int,
    environment: dict[str, Any] | None = None,
    commit: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Produce a capped prime-counting diagnostic used by the RiemannX page."""
    if limit < 10:
        raise ValueError("Riemann diagnostic limit must be >= 10")

    started = time.perf_counter()
    primes = _prime_sieve(limit)
    prime_set = set(primes)
    sample_points = _sample_points(limit, count=12)
    samples = []
    for point in sample_points:
        exact = sum(1 for prime in primes if prime <= point)
        approx = point / math.log(point)
        samples.append(
            {
                "x": point,
                "pi_x": exact,
                "x_over_log_x": round(approx, 4),
                "absolute_error": round(abs(exact - approx), 4),
                "is_prime": point in prime_set,
            }
        )
    elapsed = time.perf_counter() - started

    final_exact = len(primes)
    final_approx = limit / math.log(limit)
    return _run_artifact(
        run_id=f"riemannx-prime-count-{limit}",
        engine="RiemannX",
        claim_level="numerical_diagnostic",
        status="diagnostic_complete",
        seed=seed,
        bounds={"limit": limit, "sample_points": len(samples)},
        summary=(
            f"Computed exact prime counts through {limit} and compared sampled "
            "values with x/log(x)."
        ),
        metrics={
            "limit": limit,
            "pi_limit": final_exact,
            "x_over_log_x_at_limit": round(final_approx, 4),
            "absolute_error_at_limit": round(abs(final_exact - final_approx), 4),
        },
        samples=samples,
        elapsed_s=elapsed,
        reproduce=(
            "python -m codebase.cli run riemann "
            f"--limit {limit} --seed {seed} --output-json src/verified-runs.json"
        ),
        environment=environment,
        commit=commit,
    )


def _run_artifact(
    *,
    run_id: str,
    engine: str,
    claim_level: str,
    status: str,
    seed: int,
    bounds: dict[str, int],
    summary: str,
    metrics: dict[str, int | float],
    samples: list[dict[str, Any]],
    elapsed_s: float,
    reproduce: str,
    environment: dict[str, Any] | None,
    commit: dict[str, Any] | None,
) -> dict[str, Any]:
    return {
        "id": run_id,
        "engine": engine,
        "claim_level": claim_level,
        "status": status,
        "seed": seed,
        "bounds": bounds,
        "summary": summary,
        "metrics": metrics,
        "samples": samples,
        "elapsed_s": round(elapsed_s, 6),
        "reproduce": reproduce,
        "environment": environment or _environment(),
        "commit": commit or _commit_info(),
    }


def _collatz_trace(n: int, fuel: int) -> dict[str, Any]:
    current = n
    steps = 0
    peak = n
    odd_values = 1 if n % 2 else 0
    even_values = 1 if n % 2 == 0 else 0
    while current != 1 and steps < fuel:
        current = current // 2 if current % 2 == 0 else 3 * current + 1
        peak = max(peak, current)
        odd_values += 1 if current % 2 else 0
        even_values += 1 if current % 2 == 0 else 0
        steps += 1
    return {
        "n": n,
        "steps": steps,
        "peak": peak,
        "converged": current == 1,
        "odd_values": odd_values,
        "even_values": even_values,
    }


def _prime_sieve(limit: int) -> list[int]:
    sieve = bytearray(b"\x01") * (limit + 1)
    if limit >= 0:
        sieve[0:1] = b"\x00"
    if limit >= 1:
        sieve[1:2] = b"\x00"
    for candidate in range(2, int(limit**0.5) + 1):
        if sieve[candidate]:
            sieve[candidate * candidate :: candidate] = b"\x00" * (
                (limit - candidate * candidate) // candidate + 1
            )
    return [value for value, is_prime in enumerate(sieve) if is_prime]


def _goldbach_pairs(n: int, primes: set[int]) -> list[tuple[int, int]]:
    pairs = []
    for p in sorted(prime for prime in primes if prime <= n // 2):
        q = n - p
        if q in primes:
            pairs.append((p, q))
    return pairs


def _sample_points(limit: int, *, count: int) -> list[int]:
    points = {max(2, round(2 + ((limit - 2) * idx) / max(1, count - 1))) for idx in range(count)}
    return sorted(points)


def _environment() -> dict[str, Any]:
    """Snapshot the interpreter, platform, and resolvable dependency versions.

    A package that cannot be resolved is named in ``dependencies_unresolved``
    rather than recorded as a ``null`` version. A null would be indistinguishable
    from "this dependency genuinely has no version", and silently turns a
    degraded build environment into a provenance claim the artifact cannot back.
    """
    resolved: dict[str, str] = {}
    unresolved: list[str] = []
    for package in DEFAULT_DEPENDENCIES:
        version = _package_version(package)
        if version is None:
            unresolved.append(package)
        else:
            resolved[package] = version

    return {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "dependencies": resolved,
        "dependencies_unresolved": unresolved,
        "dependencies_complete": not unresolved,
    }


def _package_version(package: str) -> str | None:
    try:
        return metadata.version(package)
    except metadata.PackageNotFoundError:
        return None


def _commit_info() -> dict[str, Any]:
    env_sha = os.environ.get("VERCEL_GIT_COMMIT_SHA") or os.environ.get("GITHUB_SHA")
    if env_sha:
        return {"sha": env_sha, "dirty": False, "source": "environment"}

    root = Path(__file__).resolve().parents[3]
    sha = _git(["rev-parse", "--short=12", "HEAD"], cwd=root) or "unknown"
    dirty = bool(_git(["status", "--porcelain"], cwd=root))
    return {"sha": sha, "dirty": dirty, "source": "git"}


def _git(args: list[str], *, cwd: Path) -> str:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=cwd,
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError:
        return ""
    if result.returncode != 0:
        return ""
    return result.stdout.strip()
