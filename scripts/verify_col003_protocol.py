"""Independent protocol and sampler verification for PX-COL-003."""

from __future__ import annotations

import sys
from pathlib import Path

from codebase.collatzx.sampler_col003 import (
    STRATA,
    WIDTH,
    residue_stratified_pools,
    uniform_pools,
)

PROTOCOL_PATH = Path("docs/experiments/px-col-003-protocol.md")

RANGES = [
    (10_000_000_000, 10_000_099_999, "R1 (10^10)"),
    (34_359_738_368, 34_359_838_367, "R2 (2^35)"),
    (1_099_511_627_776, 1_099_511_727_775, "R3 (2^40)"),
]


def verify_ranges() -> None:
    print("Checking declared range definitions...")
    for lower, upper, label in RANGES:
        span = upper - lower + 1
        assert span == 100_000, f"{label} span {span} != 100,000"
        assert lower >= 10_000_000_000, f"{label} lower bound {lower} < 10^10"
        # Check stratum partitioning
        for s in range(STRATA):
            s_low = lower + s * WIDTH
            s_high = s_low + WIDTH - 1
            assert s_low < s_high
        print(f"  [OK] {label}: [{lower:,}, {upper:,}], span={span:,}")

    # Check non-overlapping
    for i in range(len(RANGES) - 1):
        assert RANGES[i][1] < RANGES[i + 1][0], "Intervals overlap!"
    print("  [OK] All ranges strictly non-overlapping and disjoint.")


def verify_sampler_determinism() -> None:
    print("Checking sampler reproducibility and residue diversity...")
    for lower, _, label in RANGES:
        # Check uniform
        u1 = uniform_pools(lower, seed=42, budget=64)
        u2 = uniform_pools(lower, seed=42, budget=64)
        assert u1 == u2, f"Uniform sampler non-deterministic on {label}"

        # Check residue stratified
        r1 = residue_stratified_pools(lower, seed=42, budget=64, h=8)
        r2 = residue_stratified_pools(lower, seed=42, budget=64, h=8)
        assert r1 == r2, f"Residue sampler non-deterministic on {label}"

        # Diversity check: residue-stratified draws distinct residues
        modulus = 1 << 6
        r_pool = residue_stratified_pools(lower, seed=7, budget=256, h=6)
        for s, p in enumerate(r_pool):
            distinct_res = len({x % modulus for x in p})
            assert distinct_res == modulus, f"Stratum {s} on {label} failed full residue coverage"
        print(f"  [OK] {label} passed determinism and residue diversity checks.")


def main() -> int:
    assert PROTOCOL_PATH.exists(), f"Protocol file missing: {PROTOCOL_PATH}"
    print(f"Verified protocol document exists at {PROTOCOL_PATH}")
    verify_ranges()
    verify_sampler_determinism()
    print("\nPX-COL-003 Protocol and Sampler Verification: ALL CHECKS PASSED.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
