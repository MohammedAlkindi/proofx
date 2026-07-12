"""
Cross-Engine Correlation Analysis
══════════════════════════════════
Asks: do high near-miss Collatz candidates cluster in the same numerical
neighbourhoods as high near-miss Goldbach candidates?

If they do, that structural overlap is a genuine research observation — a
region of ℕ that is simultaneously anomalous under two independent
falsification criteria, which is not predicted by any known theory.

Algorithm
─────────
1. Load two ledgers: one Collatz JSONL, one Goldbach JSONL.
2. Rank candidates by near-miss score within each conjecture.
3. For every Collatz top-k candidate c, find Goldbach candidates g with
   |g - c| ≤ radius.  Record (c, g, distance, score_c, score_g).
4. Compute the Pearson and Spearman correlation between interpolated scores
   in a shared numerical range.
5. Run a permutation test (shuffle one set of candidates, recompute
   co-occurrence count) to assess whether the overlap is above chance.
6. Return a structured report dict and optionally render a text summary.

The permutation test is deliberately lightweight (1 000 shuffles) so this
runs in seconds even on large ledgers.
"""

from __future__ import annotations

import json
import logging
import math
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

logger = logging.getLogger("proofx.cross_engine")


# ── Data types ────────────────────────────────────────────────────────────────


@dataclass
class LedgerEntry:
    candidate: int
    conjecture: str
    near_miss_score: float
    features: dict[str, float]
    details: dict[str, Any]
    strategy: str
    timestamp: float
    rng_seed: int


@dataclass
class CoOccurrence:
    collatz_candidate: int
    goldbach_candidate: int
    distance: int
    collatz_score: float
    goldbach_score: float
    joint_score: float  # geometric mean of both scores


# ── Loader ────────────────────────────────────────────────────────────────────


def _load_ledger(path: Path) -> list[LedgerEntry]:
    entries = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            d = json.loads(line)
            entries.append(
                LedgerEntry(
                    candidate=int(d["candidate"]),
                    conjecture=str(d.get("conjecture", "")),
                    near_miss_score=float(d.get("near_miss_score", 0.0)),
                    features=dict(d.get("features", {})),
                    details=dict(d.get("details", {})),
                    strategy=str(d.get("strategy", "")),
                    timestamp=float(d.get("timestamp", 0.0)),
                    rng_seed=int(d.get("rng_seed", 0)),
                )
            )
        except (KeyError, ValueError, json.JSONDecodeError) as exc:
            logger.debug("Skipping malformed entry: %s", exc)
    return entries


# ── Analyzer ──────────────────────────────────────────────────────────────────


class CrossEngineAnalyzer:
    """Measures structural overlap between Collatz and Goldbach near-miss regions."""

    def analyze(
        self,
        collatz_ledger: Path,
        goldbach_ledger: Path,
        neighborhood_radius: int = 100,
        top_k: int | None = None,
        n_permutations: int = 1_000,
        seed: int = 0,
    ) -> dict[str, Any]:
        """Run the full cross-engine analysis and return a structured report.

        Parameters
        ──────────
        collatz_ledger      : JSONL ledger from a Collatz falsification run
        goldbach_ledger     : JSONL ledger from a Goldbach falsification run
        neighborhood_radius : |c - g| ≤ radius counts as co-occurrence
        top_k               : Only consider the top-k entries per engine
                              (None = all entries)
        n_permutations      : Permutation test iterations for significance
        seed                : RNG seed for permutation test reproducibility
        """
        cz_all = _load_ledger(Path(collatz_ledger))
        gb_all = _load_ledger(Path(goldbach_ledger))

        logger.info("Loaded %d Collatz, %d Goldbach entries", len(cz_all), len(gb_all))

        cz_sorted = sorted(cz_all, key=lambda e: e.near_miss_score, reverse=True)
        gb_sorted = sorted(gb_all, key=lambda e: e.near_miss_score, reverse=True)

        cz = cz_sorted[:top_k] if top_k else cz_sorted
        gb = gb_sorted[:top_k] if top_k else gb_sorted

        co_occurrences = self._find_co_occurrences(cz, gb, neighborhood_radius)
        observed_count = len(co_occurrences)

        pvalue, null_mean, null_std = self._permutation_test(
            cz, gb, neighborhood_radius, n_permutations, seed
        )

        pearson_r, spearman_r = self._score_correlations(cz_all, gb_all)

        score_gap = self._score_gap_analysis(cz, gb)

        report: dict[str, Any] = {
            "inputs": {
                "collatz_entries": len(cz_all),
                "goldbach_entries": len(gb_all),
                "analyzed_collatz": len(cz),
                "analyzed_goldbach": len(gb),
                "neighborhood_radius": neighborhood_radius,
                "top_k": top_k,
            },
            "co_occurrences": {
                "observed_count": observed_count,
                "pairs": [
                    {
                        "collatz": c.collatz_candidate,
                        "goldbach": c.goldbach_candidate,
                        "distance": c.distance,
                        "collatz_score": round(c.collatz_score, 4),
                        "goldbach_score": round(c.goldbach_score, 4),
                        "joint_score": round(c.joint_score, 4),
                    }
                    for c in sorted(co_occurrences, key=lambda x: x.joint_score, reverse=True)
                ],
            },
            "permutation_test": {
                "observed": observed_count,
                "null_mean": round(null_mean, 2),
                "null_std": round(null_std, 2),
                "p_value": round(pvalue, 4),
                "n_permutations": n_permutations,
                "significant_at_05": pvalue < 0.05,
                "z_score": round((observed_count - null_mean) / max(null_std, 1e-9), 3),
            },
            "score_correlations": {
                "pearson_r": round(pearson_r, 4) if pearson_r is not None else None,
                "spearman_r": round(spearman_r, 4) if spearman_r is not None else None,
                "note": "Interpolated scores at shared candidates (may be sparse)",
            },
            "score_gap_analysis": score_gap,
        }

        logger.info(
            "Cross-engine: %d co-occurrences | p=%.4f | Pearson r=%.4f",
            observed_count,
            pvalue,
            pearson_r or 0.0,
        )
        return report

    # ── Co-occurrence search ──────────────────────────────────────────────────

    def _find_co_occurrences(
        self,
        cz: list[LedgerEntry],
        gb: list[LedgerEntry],
        radius: int,
    ) -> list[CoOccurrence]:
        gb_index: dict[int, float] = {e.candidate: e.near_miss_score for e in gb}
        hits: list[CoOccurrence] = []

        for c_entry in cz:
            c = c_entry.candidate
            lo, hi = c - radius, c + radius
            for g in range(lo, hi + 1):
                if g in gb_index:
                    g_score = gb_index[g]
                    joint = math.sqrt(c_entry.near_miss_score * g_score)
                    hits.append(
                        CoOccurrence(
                            collatz_candidate=c,
                            goldbach_candidate=g,
                            distance=abs(c - g),
                            collatz_score=c_entry.near_miss_score,
                            goldbach_score=g_score,
                            joint_score=joint,
                        )
                    )
        return hits

    # ── Permutation test ──────────────────────────────────────────────────────

    def _permutation_test(
        self,
        cz: list[LedgerEntry],
        gb: list[LedgerEntry],
        radius: int,
        n_permutations: int,
        seed: int,
    ) -> tuple[float, float, float]:
        """Shuffle Goldbach candidates and recount co-occurrences n_permutations times.

        Returns (p_value, null_mean, null_std).
        p_value = fraction of permutations with count ≥ observed.
        """
        observed = len(self._find_co_occurrences(cz, gb, radius))
        rng = random.Random(seed)

        gb_candidates = [e.candidate for e in gb]
        null_counts: list[int] = []

        # Keep the score distribution intact; only shuffle which candidate it's
        # attached to.  This tests whether the specific *positions* matter.
        gb_scores = [e.near_miss_score for e in gb]

        for _ in range(n_permutations):
            shuffled_candidates = gb_candidates[:]
            rng.shuffle(shuffled_candidates)
            shuffled_gb = [
                LedgerEntry(
                    candidate=c,
                    conjecture="goldbach",
                    near_miss_score=s,
                    features={},
                    details={},
                    strategy="",
                    timestamp=0.0,
                    rng_seed=0,
                )
                for c, s in zip(shuffled_candidates, gb_scores, strict=False)
            ]
            null_counts.append(len(self._find_co_occurrences(cz, shuffled_gb, radius)))

        arr = np.array(null_counts, dtype=float)
        p = float(np.mean(arr >= observed))
        return p, float(arr.mean()), float(arr.std())

    # ── Score correlations ────────────────────────────────────────────────────

    def _score_correlations(
        self,
        cz_all: list[LedgerEntry],
        gb_all: list[LedgerEntry],
    ) -> tuple[float | None, float | None]:
        """Pearson and Spearman r on the intersection of candidate sets.

        Only candidates present in both ledgers contribute.  Usually sparse
        so treat results as indicative, not conclusive.
        """
        cz_map = {e.candidate: e.near_miss_score for e in cz_all}
        gb_map = {e.candidate: e.near_miss_score for e in gb_all}
        shared = sorted(set(cz_map) & set(gb_map))

        if len(shared) < 3:
            return None, None

        cz_scores = np.array([cz_map[c] for c in shared])
        gb_scores = np.array([gb_map[c] for c in shared])

        pearson = float(np.corrcoef(cz_scores, gb_scores)[0, 1])
        # Spearman: correlation of ranks
        cz_ranks = np.argsort(np.argsort(cz_scores)).astype(float)
        gb_ranks = np.argsort(np.argsort(gb_scores)).astype(float)
        spearman = float(np.corrcoef(cz_ranks, gb_ranks)[0, 1])
        return pearson, spearman

    # ── Score gap analysis ────────────────────────────────────────────────────

    def _score_gap_analysis(
        self,
        cz: list[LedgerEntry],
        gb: list[LedgerEntry],
    ) -> dict[str, Any]:
        """Summarise score distribution gaps: are there numerical ranges where
        both engines produce high scores?

        Bins candidates into intervals of width 10 000 and counts how many
        bins contain at least one top-quartile entry from both engines.
        """
        if not cz or not gb:
            return {}

        bin_width = 10_000
        cz_q75 = np.quantile([e.near_miss_score for e in cz], 0.75)
        gb_q75 = np.quantile([e.near_miss_score for e in gb], 0.75)

        cz_hot: dict[int, int] = {}
        for e in cz:
            if e.near_miss_score >= cz_q75:
                b = e.candidate // bin_width
                cz_hot[b] = cz_hot.get(b, 0) + 1

        gb_hot: dict[int, int] = {}
        for e in gb:
            if e.near_miss_score >= gb_q75:
                b = e.candidate // bin_width
                gb_hot[b] = gb_hot.get(b, 0) + 1

        dual_hot_bins = sorted(set(cz_hot) & set(gb_hot))
        return {
            "bin_width": bin_width,
            "collatz_hot_bins": len(cz_hot),
            "goldbach_hot_bins": len(gb_hot),
            "dual_hot_bins": len(dual_hot_bins),
            "dual_hot_ranges": [
                f"[{b * bin_width:,} – {(b + 1) * bin_width - 1:,}]" for b in dual_hot_bins
            ],
            "collatz_q75_threshold": round(float(cz_q75), 4),
            "goldbach_q75_threshold": round(float(gb_q75), 4),
        }

    # ── Human-readable summary ────────────────────────────────────────────────

    @staticmethod
    def print_report(report: dict[str, Any]) -> None:
        p = report["permutation_test"]
        co = report["co_occurrences"]
        gap = report.get("score_gap_analysis", {})
        corr = report["score_correlations"]

        print(f"\n{'═' * 64}")
        print("  ProofX Cross-Engine Correlation Report")
        print(f"{'═' * 64}")
        print(f"  Collatz entries   : {report['inputs']['analyzed_collatz']}")
        print(f"  Goldbach entries  : {report['inputs']['analyzed_goldbach']}")
        print(f"  Radius            : ±{report['inputs']['neighborhood_radius']:,}")
        print()
        print(f"  Co-occurrences observed : {co['observed_count']}")
        print(f"  Null mean ± std         : {p['null_mean']:.1f} ± {p['null_std']:.1f}")
        print(f"  Z-score                 : {p['z_score']:.2f}")
        print(
            f"  p-value ({p['n_permutations']} perms)    : {p['p_value']:.4f}  "
            f"{'✓ significant' if p['significant_at_05'] else '✗ not significant'} at α=0.05"
        )
        print()
        if corr["pearson_r"] is not None:
            print("  Score correlation (shared candidates)")
            print(f"    Pearson  r = {corr['pearson_r']:.4f}")
            print(f"    Spearman r = {corr['spearman_r']:.4f}")
        else:
            print("  Score correlation: insufficient shared candidates")
        print()
        if gap.get("dual_hot_bins", 0) > 0:
            print("  Dual-hot numerical ranges (both engines top-quartile):")
            for rng in gap["dual_hot_ranges"][:10]:
                print(f"    {rng}")
        else:
            print("  No dual-hot bins found in current ledgers.")
        print()
        if co["pairs"]:
            print("  Top co-occurrence pairs (by joint score):")
            for pair in co["pairs"][:5]:
                print(
                    f"    Collatz {pair['collatz']:>10,}  ↔  "
                    f"Goldbach {pair['goldbach']:>10,}  "
                    f"dist={pair['distance']:>4}  "
                    f"joint={pair['joint_score']:.4f}"
                )
        print(f"{'═' * 64}\n")


# ── CLI entry point ───────────────────────────────────────────────────────────


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="ProofX cross-engine correlation analysis")
    parser.add_argument("--collatz", required=True, help="Collatz JSONL ledger")
    parser.add_argument("--goldbach", required=True, help="Goldbach JSONL ledger")
    parser.add_argument("--radius", type=int, default=100)
    parser.add_argument("--top-k", type=int, default=None)
    parser.add_argument("--permutations", type=int, default=1_000)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--output-json", default=None)
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")

    analyzer = CrossEngineAnalyzer()
    report = analyzer.analyze(
        collatz_ledger=Path(args.collatz),
        goldbach_ledger=Path(args.goldbach),
        neighborhood_radius=args.radius,
        top_k=args.top_k,
        n_permutations=args.permutations,
        seed=args.seed,
    )
    analyzer.print_report(report)

    if args.output_json:
        import json

        Path(args.output_json).write_text(
            json.dumps(report, indent=2, default=str), encoding="utf-8"
        )
        print(f"Report saved: {args.output_json}")


if __name__ == "__main__":
    main()
