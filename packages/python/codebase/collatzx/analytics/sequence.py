"""Core Collatz variants and sequence generation."""

from __future__ import annotations

import time
import warnings
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any

from .runtime import config


class CollatzVariant(Enum):
    """Supported Collatz step functions."""

    CLASSIC = auto()
    GENERALIZED = auto()
    FRACTAL = auto()
    MODULAR = auto()

    @classmethod
    def get_function(cls, variant: CollatzVariant, **params):
        if variant == cls.CLASSIC:
            return lambda n: 3 * n + 1 if n % 2 else n // 2
        if variant == cls.GENERALIZED:
            p = params.get("p", 3)
            q = params.get("q", 1)
            d = params.get("d", 2)
            return lambda n: p * n + q if n % 2 else n // d
        if variant == cls.FRACTAL:
            return lambda n: (3 * n + 1) // 2 if n % 2 else n // 2
        if variant == cls.MODULAR:
            mod = params.get("mod", 3)
            return lambda n: (2 * n + 1) if n % mod == 0 else (n // 2)
        raise ValueError(f"Unsupported variant: {variant.name}")


@dataclass
class CollatzSequence:
    """A generated Collatz trajectory and its bounded-run metadata."""

    starting_value: int
    sequence: list[int] = field(default_factory=list)
    stopping_time: int | None = None
    max_value: int | None = None
    features: dict[str, float] = field(default_factory=dict)
    computation_time: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.sequence:
            self.generate_sequence()

    def generate_sequence(self) -> None:
        """Generate a trajectory subject to the configured safety limits."""
        start_time = time.perf_counter()
        n = self.starting_value
        seq = [n]
        steps = 0
        seen: set[int] | None = set() if config.ENABLE_CYCLE_DETECTION else None

        while n != 1 and steps < config.MAX_ITERATIONS:
            if n > config.MAX_VALUE:
                raise OverflowError(f"Value {n} exceeds MAX_VALUE")

            if seen is not None and n in seen:
                warnings.warn(
                    f"Cycle detected for start={self.starting_value} at n={n}",
                    stacklevel=2,
                )
                break
            if seen is not None:
                seen.add(n)

            n = 3 * n + 1 if n % 2 else n // 2
            seq.append(n)
            steps += 1

        if steps >= config.MAX_ITERATIONS:
            warnings.warn(
                f"Max iterations reached for start={self.starting_value}",
                stacklevel=2,
            )

        self.sequence = seq
        self.stopping_time = len(seq) - 1
        self.max_value = max(seq) if seq else None
        self.computation_time = time.perf_counter() - start_time
        self.metadata = {
            "iterations": steps,
            "converged": n == 1,
            "cycle_detected": seen is not None and len(seq) != len(set(seq)) if seen else False,
        }
