"""Tests for CrossEngineAnalyzer — uses in-memory JSONL files via tmp_path."""

import json
import math
import sys
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parents[2]))

from codebase.CrossEngineAnalysis.cross_engine import CoOccurrence, CrossEngineAnalyzer, LedgerEntry

# ── Helpers ───────────────────────────────────────────────────────────────────


def _make_entry(candidate: int, score: float, conjecture: str = "collatz") -> LedgerEntry:
    return LedgerEntry(
        candidate=candidate,
        conjecture=conjecture,
        near_miss_score=score,
        features={},
        details={},
        strategy="test",
        timestamp=time.time(),
        rng_seed=0,
    )


def _write_jsonl(path: Path, entries: list) -> None:
    lines = [
        json.dumps(
            {
                "candidate": e.candidate,
                "conjecture": e.conjecture,
                "near_miss_score": e.near_miss_score,
                "features": e.features,
                "details": e.details,
                "strategy": e.strategy,
                "timestamp": e.timestamp,
                "rng_seed": e.rng_seed,
            }
        )
        for e in entries
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def _ledger_pair(tmp_path, cz_candidates, gb_candidates, score=0.5):
    cz = [_make_entry(c, score) for c in cz_candidates]
    gb = [_make_entry(c, score, "goldbach") for c in gb_candidates]
    cz_path = tmp_path / "collatz.jsonl"
    gb_path = tmp_path / "goldbach.jsonl"
    _write_jsonl(cz_path, cz)
    _write_jsonl(gb_path, gb)
    return cz_path, gb_path


# ── _find_co_occurrences (internal unit tests) ────────────────────────────────


class TestFindCoOccurrences:
    def setup_method(self):
        self.analyzer = CrossEngineAnalyzer()

    def test_no_proximity_returns_empty(self):
        cz = [_make_entry(100, 0.8)]
        gb = [_make_entry(500, 0.7, "goldbach")]
        assert self.analyzer._find_co_occurrences(cz, gb, radius=10) == []

    def test_exact_match_produces_one_hit(self):
        cz = [_make_entry(200, 0.8)]
        gb = [_make_entry(200, 0.7, "goldbach")]
        hits = self.analyzer._find_co_occurrences(cz, gb, radius=50)
        assert len(hits) == 1

    def test_exact_match_distance_is_zero(self):
        cz = [_make_entry(200, 0.8)]
        gb = [_make_entry(200, 0.7, "goldbach")]
        assert self.analyzer._find_co_occurrences(cz, gb, radius=50)[0].distance == 0

    def test_within_radius_produces_hit(self):
        cz = [_make_entry(100, 0.8)]
        gb = [_make_entry(140, 0.7, "goldbach")]
        assert len(self.analyzer._find_co_occurrences(cz, gb, radius=50)) == 1

    def test_outside_radius_returns_empty(self):
        cz = [_make_entry(100, 0.8)]
        gb = [_make_entry(300, 0.7, "goldbach")]
        assert self.analyzer._find_co_occurrences(cz, gb, radius=10) == []

    def test_boundary_at_radius_is_included(self):
        # distance == radius should count
        cz = [_make_entry(100, 0.8)]
        gb = [_make_entry(150, 0.7, "goldbach")]
        assert len(self.analyzer._find_co_occurrences(cz, gb, radius=50)) == 1

    def test_boundary_beyond_radius_excluded(self):
        cz = [_make_entry(100, 0.8)]
        gb = [_make_entry(151, 0.7, "goldbach")]
        assert self.analyzer._find_co_occurrences(cz, gb, radius=50) == []

    def test_joint_score_is_geometric_mean(self):
        cz = [_make_entry(100, 0.64)]
        gb = [_make_entry(100, 0.25, "goldbach")]
        hits = self.analyzer._find_co_occurrences(cz, gb, radius=0)
        assert hits[0].joint_score == pytest.approx(math.sqrt(0.64 * 0.25))

    def test_multiple_goldbach_within_radius(self):
        cz = [_make_entry(100, 0.8)]
        gb = [_make_entry(c, 0.5, "goldbach") for c in [95, 100, 105]]
        hits = self.analyzer._find_co_occurrences(cz, gb, radius=10)
        assert len(hits) == 3

    def test_returns_list_of_co_occurrence_dataclasses(self):
        cz = [_make_entry(100, 0.8)]
        gb = [_make_entry(100, 0.7, "goldbach")]
        hits = self.analyzer._find_co_occurrences(cz, gb, radius=5)
        assert all(isinstance(h, CoOccurrence) for h in hits)

    def test_empty_collatz_returns_empty(self):
        gb = [_make_entry(100, 0.7, "goldbach")]
        assert self.analyzer._find_co_occurrences([], gb, radius=100) == []

    def test_empty_goldbach_returns_empty(self):
        cz = [_make_entry(100, 0.8)]
        assert self.analyzer._find_co_occurrences(cz, [], radius=100) == []


# ── CrossEngineAnalyzer.analyze ───────────────────────────────────────────────


class TestCrossEngineAnalyzerAnalyze:
    def setup_method(self):
        self.analyzer = CrossEngineAnalyzer()

    def test_returns_dict(self, tmp_path):
        cz_path, gb_path = _ledger_pair(tmp_path, [100, 200, 300], [400, 500, 600])
        result = self.analyzer.analyze(cz_path, gb_path, n_permutations=10, seed=0)
        assert isinstance(result, dict)

    def test_required_top_level_keys(self, tmp_path):
        cz_path, gb_path = _ledger_pair(tmp_path, [100, 200, 300], [400, 500, 600])
        report = self.analyzer.analyze(cz_path, gb_path, n_permutations=10, seed=0)
        for key in ("inputs", "co_occurrences", "permutation_test", "score_correlations"):
            assert key in report

    def test_inputs_entry_counts_correct(self, tmp_path):
        cz_path, gb_path = _ledger_pair(tmp_path, [100, 200, 300], [400, 500])
        report = self.analyzer.analyze(cz_path, gb_path, n_permutations=10, seed=0)
        assert report["inputs"]["collatz_entries"] == 3
        assert report["inputs"]["goldbach_entries"] == 2

    def test_overlapping_candidates_produce_co_occurrences(self, tmp_path):
        cz_path, gb_path = _ledger_pair(tmp_path, [100, 200], [100, 200])
        report = self.analyzer.analyze(
            cz_path, gb_path, neighborhood_radius=0, n_permutations=10, seed=0
        )
        assert report["co_occurrences"]["observed_count"] >= 2

    def test_non_overlapping_no_co_occurrences(self, tmp_path):
        cz_path, gb_path = _ledger_pair(tmp_path, [100, 200, 300], [50_000, 60_000, 70_000])
        report = self.analyzer.analyze(
            cz_path, gb_path, neighborhood_radius=10, n_permutations=10, seed=0
        )
        assert report["co_occurrences"]["observed_count"] == 0

    def test_p_value_in_unit_interval(self, tmp_path):
        cz_path, gb_path = _ledger_pair(
            tmp_path, [100, 200, 300, 400, 500], [110, 210, 310, 410, 510]
        )
        report = self.analyzer.analyze(cz_path, gb_path, n_permutations=50, seed=0)
        pval = report["permutation_test"]["p_value"]
        assert 0.0 <= pval <= 1.0

    def test_permutation_test_null_std_non_negative(self, tmp_path):
        cz_path, gb_path = _ledger_pair(tmp_path, [100, 200, 300], [150, 250, 350])
        report = self.analyzer.analyze(cz_path, gb_path, n_permutations=20, seed=0)
        assert report["permutation_test"]["null_std"] >= 0.0

    def test_top_k_limits_analyzed_entries(self, tmp_path):
        cz_path, gb_path = _ledger_pair(
            tmp_path, [100, 200, 300, 400, 500], [110, 210, 310, 410, 510]
        )
        report = self.analyzer.analyze(cz_path, gb_path, top_k=2, n_permutations=10, seed=0)
        assert report["inputs"]["analyzed_collatz"] == 2
        assert report["inputs"]["analyzed_goldbach"] == 2

    def test_co_occurrence_pairs_are_list(self, tmp_path):
        cz_path, gb_path = _ledger_pair(tmp_path, [100, 200], [100, 200])
        report = self.analyzer.analyze(
            cz_path, gb_path, neighborhood_radius=0, n_permutations=10, seed=0
        )
        assert isinstance(report["co_occurrences"]["pairs"], list)

    def test_co_occurrence_pair_keys(self, tmp_path):
        cz_path, gb_path = _ledger_pair(tmp_path, [100], [100])
        report = self.analyzer.analyze(
            cz_path, gb_path, neighborhood_radius=0, n_permutations=10, seed=0
        )
        pair = report["co_occurrences"]["pairs"][0]
        for key in (
            "collatz",
            "goldbach",
            "distance",
            "collatz_score",
            "goldbach_score",
            "joint_score",
        ):
            assert key in pair

    def test_score_correlations_none_when_no_shared_candidates(self, tmp_path):
        cz_path, gb_path = _ledger_pair(tmp_path, [100, 200], [300, 400])
        report = self.analyzer.analyze(cz_path, gb_path, n_permutations=10, seed=0)
        # No shared candidates → both correlations are None
        assert report["score_correlations"]["pearson_r"] is None
        assert report["score_correlations"]["spearman_r"] is None

    def test_n_permutations_recorded(self, tmp_path):
        cz_path, gb_path = _ledger_pair(tmp_path, [100, 200], [300, 400])
        report = self.analyzer.analyze(cz_path, gb_path, n_permutations=17, seed=0)
        assert report["permutation_test"]["n_permutations"] == 17

    def test_radius_recorded_in_inputs(self, tmp_path):
        cz_path, gb_path = _ledger_pair(tmp_path, [100], [200])
        report = self.analyzer.analyze(
            cz_path, gb_path, neighborhood_radius=42, n_permutations=10, seed=0
        )
        assert report["inputs"]["neighborhood_radius"] == 42

    def test_reproducible_with_same_seed(self, tmp_path):
        cz_path, gb_path = _ledger_pair(tmp_path, [100, 200, 300], [110, 210, 310])
        r1 = self.analyzer.analyze(cz_path, gb_path, n_permutations=30, seed=7)
        r2 = self.analyzer.analyze(cz_path, gb_path, n_permutations=30, seed=7)
        assert r1["permutation_test"]["p_value"] == r2["permutation_test"]["p_value"]
