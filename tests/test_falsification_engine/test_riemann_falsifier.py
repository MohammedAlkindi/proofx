"""Smoke tests for RiemannFalsifier.

All tests are skipped automatically if mpmath is not installed.
Budget is kept at 4 (2 zeros + 2 Keiper-Li coefficients) with low precision
(15 dps) so the suite completes in a few seconds.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parents[2]))

mpmath = pytest.importorskip("mpmath", reason="mpmath not installed — skipping RiemannFalsifier tests")

from codebase.FalsificationEngine.FalsificationEngine import FalsificationLedger
from codebase.FalsificationEngine.RiemannFalsifier import RiemannFalsifier

# ── Fixture ───────────────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def rf():
    # 15 dps: fast enough for CI; deviations still resolve to ~1e-7
    return RiemannFalsifier(precision_dps=15)


@pytest.fixture(scope="module")
def small_ledger(rf):
    # budget=4 → 2 zeros + 2 Keiper-Li entries
    return rf.search(budget=4, seed=0)


# ── Construction ──────────────────────────────────────────────────────────────


class TestRiemannFalsifierConstruction:
    def test_missing_mpmath_raises(self, monkeypatch):
        import builtins
        real_import = builtins.__import__

        def _block_mpmath(name, *args, **kwargs):
            if name == "mpmath":
                raise ImportError("blocked")
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", _block_mpmath)
        with pytest.raises(RuntimeError, match="mpmath"):
            RiemannFalsifier()


# ── Search output structure ───────────────────────────────────────────────────


class TestRiemannFalsifierSearch:
    def test_returns_falsification_ledger(self, small_ledger):
        assert isinstance(small_ledger, FalsificationLedger)

    def test_ledger_is_non_empty(self, small_ledger):
        assert len(small_ledger) > 0

    def test_all_entries_labelled_riemann(self, small_ledger):
        for e in small_ledger._entries:
            assert e.conjecture == "riemann"

    def test_both_strategies_present(self, small_ledger):
        strategies = {e.strategy for e in small_ledger._entries}
        assert "zero_deviation_scan" in strategies
        assert "keiper_li_coefficients" in strategies

    def test_scores_in_unit_interval(self, small_ledger):
        for e in small_ledger._entries:
            assert 0.0 <= e.near_miss_score <= 1.0

    def test_zero_scan_entries_have_required_detail_keys(self, small_ledger):
        zero_entries = [e for e in small_ledger._entries if e.strategy == "zero_deviation_scan"]
        assert zero_entries, "Expected at least one zero_deviation_scan entry"
        for e in zero_entries:
            for key in ("zero_index", "zero_real", "zero_imag", "deviation_from_half"):
                assert key in e.details, f"Missing detail key: {key}"

    def test_keiper_li_entries_have_required_detail_keys(self, small_ledger):
        kl_entries = [e for e in small_ledger._entries if e.strategy == "keiper_li_coefficients"]
        assert kl_entries, "Expected at least one keiper_li_coefficients entry"
        for e in kl_entries:
            for key in ("n", "lambda_n", "is_positive", "is_increasing"):
                assert key in e.details, f"Missing detail key: {key}"

    def test_known_zeros_on_critical_line(self, small_ledger):
        # All verified non-trivial zeros satisfy Re(ρ) = 0.5 exactly.
        # At 15 dps the computed deviation should be < 1e-6.
        zero_entries = [e for e in small_ledger._entries if e.strategy == "zero_deviation_scan"]
        for e in zero_entries:
            assert e.details["deviation_from_half"] < 1e-6

    def test_first_keiper_li_coefficient_is_positive(self, small_ledger):
        # λ_1 ≈ 0.023 > 0 (positivity required by RH; holds for known n)
        kl_entries = sorted(
            [e for e in small_ledger._entries if e.strategy == "keiper_li_coefficients"],
            key=lambda e: e.details["n"],
        )
        assert kl_entries[0].details["lambda_n"] > 0.0

    def test_zero_index_starts_at_one(self, small_ledger):
        zero_entries = [e for e in small_ledger._entries if e.strategy == "zero_deviation_scan"]
        indices = [e.details["zero_index"] for e in zero_entries]
        assert min(indices) == 1
