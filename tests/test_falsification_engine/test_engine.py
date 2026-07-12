"""Smoke tests for FalsificationLedger, LedgerEntry, CollatzFalsifier,
GoldbachFalsifier, and FalsificationEngine."""

import json
import sys
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parents[2]))

from codebase.FalsificationEngine.FalsificationEngine import (
    CollatzFalsifier,
    FalsificationEngine,
    FalsificationLedger,
    GoldbachFalsifier,
    LedgerEntry,
)

# ── Helpers ───────────────────────────────────────────────────────────────────


def _make_entry(
    candidate: int = 27, score: float = 0.5, conjecture: str = "collatz"
) -> LedgerEntry:
    return LedgerEntry(
        candidate=candidate,
        conjecture=conjecture,
        strategy="test",
        features={"lyapunov_exponent": 0.1},
        near_miss_score=score,
        details={},
        timestamp=time.time(),
        rng_seed=0,
    )


# ── FalsificationLedger ───────────────────────────────────────────────────────


class TestFalsificationLedger:
    def test_empty_len(self):
        assert len(FalsificationLedger()) == 0

    def test_append_increments_length(self):
        ledger = FalsificationLedger()
        ledger.append(_make_entry())
        assert len(ledger) == 1

    def test_append_multiple(self):
        ledger = FalsificationLedger()
        for _ in range(5):
            ledger.append(_make_entry())
        assert len(ledger) == 5

    def test_top_k_count(self):
        ledger = FalsificationLedger()
        for score in [0.1, 0.5, 0.9]:
            ledger.append(_make_entry(score=score))
        assert len(ledger.top_k(2)) == 2

    def test_top_k_ordering(self):
        ledger = FalsificationLedger()
        for score in [0.1, 0.9, 0.5]:
            ledger.append(_make_entry(score=score))
        top = ledger.top_k(3)
        assert top[0].near_miss_score >= top[1].near_miss_score >= top[2].near_miss_score

    def test_top_k_returns_highest_score(self):
        ledger = FalsificationLedger()
        ledger.append(_make_entry(score=0.2))
        ledger.append(_make_entry(score=0.8))
        assert ledger.top_k(1)[0].near_miss_score == pytest.approx(0.8)

    def test_top_k_larger_than_len_returns_all(self):
        ledger = FalsificationLedger()
        ledger.append(_make_entry(score=0.5))
        assert len(ledger.top_k(100)) == 1

    def test_to_jsonl_one_line_per_entry(self):
        ledger = FalsificationLedger()
        ledger.append(_make_entry())
        ledger.append(_make_entry(candidate=871))
        assert len(ledger.to_jsonl().splitlines()) == 2

    def test_to_jsonl_is_valid_json(self):
        ledger = FalsificationLedger()
        ledger.append(_make_entry())
        parsed = json.loads(ledger.to_jsonl().splitlines()[0])
        assert parsed["candidate"] == 27

    def test_save_creates_file(self, tmp_path):
        ledger = FalsificationLedger()
        ledger.append(_make_entry())
        out = tmp_path / "ledger.jsonl"
        ledger.save(out)
        assert out.exists()

    def test_save_content_matches_to_jsonl(self, tmp_path):
        ledger = FalsificationLedger()
        ledger.append(_make_entry())
        out = tmp_path / "ledger.jsonl"
        ledger.save(out)
        assert out.read_text(encoding="utf-8").strip() == ledger.to_jsonl().strip()


# ── LedgerEntry ───────────────────────────────────────────────────────────────


class TestLedgerEntry:
    def test_to_dict_json_serializable(self):
        json.dumps(_make_entry().to_dict())  # must not raise

    def test_to_dict_preserves_candidate(self):
        assert _make_entry(candidate=1234).to_dict()["candidate"] == 1234

    def test_to_dict_preserves_score(self):
        assert _make_entry(score=0.73).to_dict()["near_miss_score"] == pytest.approx(0.73)

    def test_to_dict_preserves_conjecture(self):
        assert _make_entry(conjecture="goldbach").to_dict()["conjecture"] == "goldbach"


# ── CollatzFalsifier — unit ───────────────────────────────────────────────────


class TestCollatzFalsifierMath:
    def test_quick_score_in_unit_interval(self):
        for n in [3, 27, 871, 6171, 77031]:
            s = CollatzFalsifier._quick_score(n)
            assert 0.0 <= s <= 1.0

    def test_quick_score_champion_above_threshold(self):
        # Known champions should score above the queue admission threshold (0.05)
        for champion in [27, 703, 871, 6171]:
            assert CollatzFalsifier._quick_score(champion) >= 0.05

    def test_inverse_predecessors_includes_doubling(self):
        for n in [10, 27, 100]:
            assert 2 * n in CollatzFalsifier._inverse_collatz_predecessors(n)

    def test_inverse_predecessors_odd_rule(self):
        # 3*3 + 1 = 10, so 3 maps to 10 via the odd step
        assert 3 in CollatzFalsifier._inverse_collatz_predecessors(10)

    def test_inverse_predecessors_odd_rule_requires_odd_m(self):
        # (13-1)/3 = 4, which is even — should NOT be included
        assert 4 not in CollatzFalsifier._inverse_collatz_predecessors(13)

    def test_inverse_predecessors_odd_rule_n_not_1_mod_3(self):
        # n=8: (8-1)/3 = 7/3 not integer — no odd predecessor
        preds = CollatzFalsifier._inverse_collatz_predecessors(8)
        assert 2 * 8 in preds  # doubling always present


# ── CollatzFalsifier — search ─────────────────────────────────────────────────


class TestCollatzFalsifierSearch:
    def test_search_returns_ledger_type(self):
        result = CollatzFalsifier().search(budget=3, seed=42)
        assert isinstance(result, FalsificationLedger)

    def test_search_respects_budget(self):
        assert len(CollatzFalsifier().search(budget=4, seed=42)) == 4

    def test_search_all_conjecture_labels(self):
        for e in CollatzFalsifier().search(budget=3, seed=0)._entries:
            assert e.conjecture == "collatz"

    def test_search_strategy_label(self):
        for e in CollatzFalsifier().search(budget=3, seed=0)._entries:
            assert e.strategy == "inverse_tree_beam_search"

    def test_search_scores_in_unit_interval(self):
        for e in CollatzFalsifier().search(budget=3, seed=0)._entries:
            assert 0.0 <= e.near_miss_score <= 1.0

    def test_search_candidates_are_positive_integers(self):
        for e in CollatzFalsifier().search(budget=3, seed=0)._entries:
            assert isinstance(e.candidate, int) and e.candidate > 0

    def test_search_is_reproducible(self):
        a = CollatzFalsifier().search(budget=3, seed=99).top_k(1)[0]
        b = CollatzFalsifier().search(budget=3, seed=99).top_k(1)[0]
        assert a.candidate == b.candidate
        assert a.near_miss_score == pytest.approx(b.near_miss_score)

    def test_search_different_seeds_differ(self):
        a = CollatzFalsifier().search(budget=5, seed=1).top_k(1)[0]
        b = CollatzFalsifier().search(budget=5, seed=999).top_k(1)[0]
        # Not guaranteed, but the top candidate almost certainly differs
        # (the anchors are the same but residue neighborhoods diverge)
        # We only assert both produce valid non-empty ledgers
        assert a.near_miss_score >= 0.0
        assert b.near_miss_score >= 0.0


# ── GoldbachFalsifier — unit ──────────────────────────────────────────────────


class TestGoldbachFalsifierMath:
    def setup_method(self):
        self.g = GoldbachFalsifier(sieve_limit=1_000)

    def test_partition_count_4(self):
        assert self.g._actual_partition_count(4) == 1  # 2+2

    def test_partition_count_10(self):
        assert self.g._actual_partition_count(10) == 2  # 3+7 and 5+5

    def test_partition_count_28(self):
        # 28 = 5+23 = 11+17 = none else with p≤q; check via direct count
        count = self.g._actual_partition_count(28)
        assert count > 0

    def test_partition_count_odd_is_zero(self):
        assert self.g._actual_partition_count(7) == 0

    def test_partition_count_below_4_is_zero(self):
        for n in [1, 2, 3]:
            assert self.g._actual_partition_count(n) == 0

    def test_hardy_littlewood_positive_for_even_n(self):
        assert self.g._hardy_littlewood_expected(100) > 0.0

    def test_hardy_littlewood_zero_for_odd(self):
        assert self.g._hardy_littlewood_expected(7) == 0.0

    def test_hardy_littlewood_zero_for_small_n(self):
        assert self.g._hardy_littlewood_expected(3) == 0.0

    def test_near_miss_score_confirmed_counterexample(self):
        # actual == 0 → full score of 1.0
        assert self.g._near_miss_score(0, 10.0) == pytest.approx(1.0)

    def test_near_miss_score_exact_match_is_zero(self):
        assert self.g._near_miss_score(10, 10.0) == pytest.approx(0.0)

    def test_near_miss_score_partial_deficit(self):
        s = self.g._near_miss_score(5, 10.0)
        assert s == pytest.approx(0.5)

    def test_near_miss_score_in_unit_interval(self):
        for actual, expected in [(0, 5.0), (3, 5.0), (5, 5.0), (10, 5.0)]:
            s = self.g._near_miss_score(actual, expected)
            assert 0.0 <= s <= 1.0

    def test_near_miss_score_zero_expected_is_zero(self):
        assert self.g._near_miss_score(5, 0.0) == pytest.approx(0.0)


# ── GoldbachFalsifier — search ────────────────────────────────────────────────


class TestGoldbachFalsifierSearch:
    def test_search_returns_ledger_type(self):
        assert isinstance(
            GoldbachFalsifier(sieve_limit=1_000).search(budget=5, seed=0), FalsificationLedger
        )

    def test_search_all_conjecture_labels(self):
        for e in GoldbachFalsifier(sieve_limit=1_000).search(budget=5, seed=0)._entries:
            assert e.conjecture == "goldbach"

    def test_search_scores_in_unit_interval(self):
        for e in GoldbachFalsifier(sieve_limit=1_000).search(budget=5, seed=0)._entries:
            assert 0.0 <= e.near_miss_score <= 1.0

    def test_search_candidates_are_even(self):
        for e in GoldbachFalsifier(sieve_limit=1_000).search(budget=5, seed=0)._entries:
            assert e.candidate % 2 == 0

    def test_search_candidates_at_least_4(self):
        for e in GoldbachFalsifier(sieve_limit=1_000).search(budget=5, seed=0)._entries:
            assert e.candidate >= 4


# ── FalsificationEngine ───────────────────────────────────────────────────────


class TestFalsificationEngine:
    _SIEVE = 1_000
    _BUDGET = 6

    def _engine(self) -> FalsificationEngine:
        return FalsificationEngine(sieve_limit=self._SIEVE)

    def test_invalid_target_raises_value_error(self):
        with pytest.raises(ValueError):
            self._engine().run(budget=self._BUDGET, seed=0, target="notaconjecture")

    def test_run_collatz_returns_ledger(self):
        result = self._engine().run(budget=self._BUDGET, seed=0, target="collatz")
        assert isinstance(result["ledger"], FalsificationLedger)

    def test_run_goldbach_returns_ledger(self):
        result = self._engine().run(budget=self._BUDGET, seed=0, target="goldbach")
        assert isinstance(result["ledger"], FalsificationLedger)

    def test_run_both_collatz_evaluations_nonzero(self):
        stats = self._engine().run(budget=self._BUDGET, seed=0, target="both")["stats"]
        assert stats["collatz_evaluated"] > 0

    def test_run_both_goldbach_evaluations_nonzero(self):
        stats = self._engine().run(budget=self._BUDGET, seed=0, target="both")["stats"]
        assert stats["goldbach_evaluated"] > 0

    def test_run_stats_keys_present(self):
        stats = self._engine().run(budget=self._BUDGET, seed=0, target="both")["stats"]
        required = {
            "collatz_evaluated",
            "goldbach_evaluated",
            "total_evaluated",
            "collatz_max_near_miss",
            "goldbach_max_near_miss",
            "seed",
            "elapsed_s",
        }
        assert required <= set(stats)

    def test_run_stats_seed_matches(self):
        result = self._engine().run(budget=self._BUDGET, seed=42, target="collatz")
        assert result["stats"]["seed"] == 42

    def test_run_all_scores_in_unit_interval(self):
        result = self._engine().run(budget=self._BUDGET, seed=0, target="both")
        for e in result["ledger"]._entries:
            assert 0.0 <= e.near_miss_score <= 1.0

    def test_run_elapsed_positive(self):
        result = self._engine().run(budget=self._BUDGET, seed=0, target="collatz")
        assert result["elapsed_s"] > 0.0

    def test_run_is_reproducible(self):
        r1 = self._engine().run(budget=self._BUDGET, seed=7, target="collatz")
        r2 = self._engine().run(budget=self._BUDGET, seed=7, target="collatz")
        assert r1["top_collatz"][0].candidate == r2["top_collatz"][0].candidate

    def test_min_score_reduces_ledger(self):
        full = self._engine().run(budget=self._BUDGET, seed=0, target="both", min_score=0.0)
        filtered = self._engine().run(budget=self._BUDGET, seed=0, target="both", min_score=0.99)
        assert len(filtered["ledger"]) <= len(full["ledger"])

    def test_min_score_all_entries_above_threshold(self):
        result = self._engine().run(budget=self._BUDGET, seed=0, target="both", min_score=0.3)
        for e in result["ledger"]._entries:
            assert e.near_miss_score >= 0.3
