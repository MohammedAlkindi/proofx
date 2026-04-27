"""Tests for ReimannX KeiperLi module."""

import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).parents[2]))

from codebase.ReimannX.KeiperLi.KeiperLi import analyze_coefficients, compute_li_coefficients


class TestComputeLiCoefficients:
    def test_returns_numpy_array(self):
        result = compute_li_coefficients(3)
        assert isinstance(result, np.ndarray)

    def test_correct_length(self):
        for n in [1, 3, 5]:
            result = compute_li_coefficients(n)
            assert len(result) == n

    def test_coefficients_are_positive(self):
        # Under RH, all λₙ should be positive
        result = compute_li_coefficients(5)
        assert np.all(result > 0), "All Keiper-Li coefficients should be positive under RH"

    def test_first_coefficient_known_value(self):
        # λ₁ ≈ 0.0230957... (known value)
        result = compute_li_coefficients(1)
        assert abs(result[0] - 0.0230957) < 1e-3


class TestAnalyzeCoefficients:
    def test_positive_monotonic_convex_succeeds(self, capsys):
        # Artificially create positive, monotonic, convex sequence
        coeffs = np.array([1.0, 2.0, 4.0, 8.0])
        analyze_coefficients(coeffs)  # should not raise

    def test_non_positive_still_runs(self, capsys):
        coeffs = np.array([-1.0, 0.5, 2.0])
        analyze_coefficients(coeffs)  # should not raise even with negatives
        captured = capsys.readouterr()
        assert "⚠️" in captured.out or "Turbulence" in captured.out
