"""Numerical Keiper-Li coefficient diagnostics.

These routines compute small finite prefixes for inspection. They are numerical
diagnostics only, not a proof of the Riemann Hypothesis.
"""

from __future__ import annotations

import matplotlib.pyplot as plt
import mpmath
import numpy as np


def _xi(s: mpmath.mpf) -> mpmath.mpf:
    """Completed zeta xi function with the removable value at s=1."""
    if s == 1:
        return mpmath.mpf("0.5")
    return (
        mpmath.mpf("0.5")
        * s
        * (s - 1)
        * mpmath.gamma(s / 2)
        * mpmath.power(mpmath.pi, -s / 2)
        * mpmath.zeta(s)
    )


def compute_li_coefficients(n_terms: int) -> np.ndarray:
    """Compute the first ``n_terms`` Keiper-Li coefficients numerically."""
    if n_terms < 1:
        raise ValueError("n_terms must be positive")

    mpmath.mp.dps = 80
    coefficients: list[float] = []
    print("Computing Keiper-Li coefficients...")

    for order in range(1, n_terms + 1):

        def differentiated(s: mpmath.mpf, order: int = order) -> mpmath.mpf:
            return mpmath.power(s, order - 1) * mpmath.log(_xi(s))

        derivative = mpmath.diff(differentiated, 1, order)
        coefficient = derivative / mpmath.factorial(order - 1)
        coefficients.append(float(coefficient))
        print(f"lambda_{order} = {coefficient}")

    return np.array(coefficients, dtype=float)


def analyze_coefficients(coefficients: np.ndarray) -> None:
    """Print simple finite-prefix diagnostics for a coefficient sequence."""
    print("\nPerforming Keiper-Li finite-prefix diagnostics...")

    positive = bool(np.all(coefficients > 0))
    print(f"Positivity: {'all coefficients > 0' if positive else 'some coefficients <= 0'}")

    diffs = np.diff(coefficients)
    monotonic = bool(np.all(diffs > 0))
    print(f"Monotonicity: {'strictly increasing' if monotonic else 'not strictly increasing'}")

    second_diffs = np.diff(coefficients, 2)
    convex = bool(np.all(second_diffs > 0))
    print(f"Convexity: {'convex finite prefix' if convex else 'non-convex finite prefix'}")

    if positive and monotonic and convex:
        print("\nFinite-prefix diagnostic: no anomaly in these checks.")
    else:
        print("\nTurbulence detected in this finite-prefix diagnostic.")


def plot_coefficients(coefficients: np.ndarray, output_path: str = "li_flow.png") -> None:
    """Visualize a finite prefix of Keiper-Li coefficients."""
    plt.figure(figsize=(12, 6))

    plt.subplot(1, 2, 1)
    plt.plot(coefficients, "o-", color="navy", markersize=4)
    plt.xlabel("n")
    plt.ylabel("lambda_n")
    plt.title("Keiper-Li Coefficients")
    plt.grid(True, alpha=0.3)

    plt.subplot(1, 2, 2)
    plt.semilogy(np.abs(coefficients), "o-", color="crimson", markersize=4)
    plt.xlabel("n")
    plt.ylabel("log|lambda_n|")
    plt.title("Logarithmic Growth")
    plt.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(output_path)
    print(f"\nVisualization saved to {output_path}")


def main() -> None:
    n_terms = 50
    coefficients = compute_li_coefficients(n_terms)
    analyze_coefficients(coefficients)
    plot_coefficients(coefficients)


if __name__ == "__main__":
    main()
