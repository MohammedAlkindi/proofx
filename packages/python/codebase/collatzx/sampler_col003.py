"""Residue-stratified and uniform proposal samplers for PX-COL-003."""

from __future__ import annotations

import numpy as np

STRATA = 16
WIDTH = 6_250
MULTIPLIER = 4


def uniform_pools(lower: int, seed: int, budget: int, phase: str = "test") -> list[list[int]]:
    """Uniform random proposal pools matching PX-COL-002 baseline."""
    if phase not in {"development", "test"}:
        raise ValueError("unknown phase")
    if budget not in (64, 256, 1024) or lower < 2 or seed < 0:
        raise ValueError("invalid population, budget or seed")
    count = MULTIPLIER * budget // STRATA
    result = []
    for stratum in range(STRATA):
        rng = np.random.Generator(
            np.random.PCG64(
                np.random.SeedSequence([0x50584333, int(phase == "test"), lower, seed, stratum, 0])
            )
        )
        seen: set[int] = set()
        ordered = []
        while len(ordered) < count:
            n = lower + stratum * WIDTH + int(rng.integers(WIDTH))
            if n not in seen:
                seen.add(n)
                ordered.append(n)
        result.append(ordered)
    return result


def residue_stratified_pools(
    lower: int, seed: int, budget: int, phase: str = "test", h: int = 8
) -> list[list[int]]:
    """Residue-stratified proposal pools enforcing modular diversity modulo 2^h.
    
    Under Lagarias (1985), parity sequences over h steps are periodic modulo 2^h.
    When 2^h <= count, draws are balanced across congruence classes to suppress
    local proposal clumping.
    """
    if phase not in {"development", "test"}:
        raise ValueError("unknown phase")
    if budget not in (64, 256, 1024) or lower < 2 or seed < 0:
        raise ValueError("invalid population, budget or seed")
    count = MULTIPLIER * budget // STRATA
    modulus = 1 << h
    result = []
    for stratum in range(STRATA):
        rng = np.random.Generator(
            np.random.PCG64(
                np.random.SeedSequence([0x50584333, int(phase == "test"), lower, seed, stratum, 1])
            )
        )
        stratum_base = lower + stratum * WIDTH
        seen: set[int] = set()
        seen_residues: set[int] = set()
        ordered = []

        # Pass 1: draw distinct residues mod 2^h as far as possible
        attempts = 0
        max_attempts = count * 20
        while len(ordered) < count and len(seen_residues) < min(modulus, WIDTH) and attempts < max_attempts:
            attempts += 1
            n = stratum_base + int(rng.integers(WIDTH))
            res = n % modulus
            if n not in seen and res not in seen_residues:
                seen.add(n)
                seen_residues.add(res)
                ordered.append(n)

        # Pass 2: fill remaining quota without duplicate values
        while len(ordered) < count:
            n = stratum_base + int(rng.integers(WIDTH))
            if n not in seen:
                seen.add(n)
                ordered.append(n)

        result.append(ordered)
    return result
