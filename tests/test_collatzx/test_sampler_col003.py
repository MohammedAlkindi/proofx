"""Tests for PX-COL-003 proposal samplers."""

import pytest
from codebase.collatzx.sampler_col003 import (
    MULTIPLIER,
    STRATA,
    WIDTH,
    residue_stratified_pools,
    uniform_pools,
)

LOWER_R1 = 10_000_000_000


def test_pool_dimensions_and_strata():
    budget = 64
    pools = uniform_pools(LOWER_R1, seed=0, budget=budget)
    assert len(pools) == STRATA
    expected_count = MULTIPLIER * budget // STRATA
    for p in pools:
        assert len(p) == expected_count


def test_bounds_compliance():
    budget = 256
    pools = residue_stratified_pools(LOWER_R1, seed=1, budget=budget, h=8)
    for s, p in enumerate(pools):
        stratum_min = LOWER_R1 + s * WIDTH
        stratum_max = stratum_min + WIDTH - 1
        for val in p:
            assert stratum_min <= val <= stratum_max


def test_deterministic_reproducibility():
    p1 = residue_stratified_pools(LOWER_R1, seed=42, budget=64, h=8)
    p2 = residue_stratified_pools(LOWER_R1, seed=42, budget=64, h=8)
    assert p1 == p2


def test_seed_diversity():
    p1 = residue_stratified_pools(LOWER_R1, seed=0, budget=64, h=8)
    p2 = residue_stratified_pools(LOWER_R1, seed=1, budget=64, h=8)
    assert p1 != p2


def test_residue_diversity_enhancement():
    h = 6  # 64 residues
    budget = 256  # 64 samples per stratum
    res_pools = residue_stratified_pools(LOWER_R1, seed=7, budget=budget, h=h)
    modulus = 1 << h
    for p in res_pools:
        distinct_residues = len({x % modulus for x in p})
        # With 64 samples and 64 available residues, residue-stratified should achieve all 64
        assert distinct_residues == modulus


def test_invalid_parameters():
    with pytest.raises(ValueError, match="unknown phase"):
        uniform_pools(LOWER_R1, seed=0, budget=64, phase="invalid")
    with pytest.raises(ValueError, match="invalid population"):
        uniform_pools(1, seed=0, budget=64)
    with pytest.raises(ValueError, match="invalid population"):
        uniform_pools(LOWER_R1, seed=-1, budget=64)
    with pytest.raises(ValueError, match="invalid population"):
        uniform_pools(LOWER_R1, seed=0, budget=100)
