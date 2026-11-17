"""Semantic tests for PX-COL-004. Run: python -m unittest -v test_study (from this directory)."""

import unittest

import numpy as np
import study


class StudyTests(unittest.TestCase):
    def test_prefix_matches_python_including_overflow_path(self):
        ns = [27, 97, 2**37 + 12345, 2**63 - 1, 2**40 - 1, 6_171]
        feat = study.prefix_features(np.array(ns, dtype=np.uint64))
        for n in ns:
            self.assertEqual(feat[n], study._py_prefix(n))

    def test_prefix_stops_at_first_one(self):
        k16, u16, *_ = study._py_prefix(8)
        self.assertEqual((k16, u16), (0, 3))

    def test_stopping_times_match_scalar(self):
        ns = [2, 3, 27, 837_799, 2**37 + 3, 2**63 - 25]
        got = study.stopping_times(np.array(ns, dtype=np.uint64)).tolist()
        self.assertEqual(got, [study.total_stopping_time(n) for n in ns])

    def test_windows_are_disjoint_and_avoid_seen_ranges(self):
        wins = study.test_windows()
        self.assertEqual(len(wins), 24)
        self.assertEqual(wins, study.test_windows())
        for i, a in enumerate(wins):
            for b in list(study.EXCLUDED) + wins[i + 1 :]:
                self.assertGreaterEqual(abs(a - b), study.WINDOW)

    def test_pools_are_distinct_and_deterministic(self):
        p1, k1 = study.pool_and_keys("test", 2**33 + 5, 3, 7)
        p2, k2 = study.pool_and_keys("test", 2**33 + 5, 3, 7)
        self.assertEqual((p1, k1), (p2, k2))
        self.assertEqual(len(set(p1)), len(p1))
        base = 2**33 + 5 + 7 * study.WIDTH
        self.assertTrue(all(base <= n < base + study.WIDTH for n in p1))

    def test_halving_charges_each_input_its_final_depth(self):
        pool, keys = study.pool_and_keys("development", 100_001, 0, 0)
        feat = study.prefix_features(np.array(pool, dtype=np.uint64))
        sel, spent = study.select("halving", pool, keys, 4, feat)
        self.assertEqual(len(sel), 4)
        self.assertEqual(len(spent), 32)
        for n in sel:
            self.assertEqual(spent[n], feat[n][5])
        dropped_first = [n for n in pool[:32] if spent[n] == feat[n][1] and n not in sel]
        self.assertEqual(len(dropped_first), 16)

    def test_uniform_and_single_stage_use_nested_pool_prefixes(self):
        pool, keys = study.pool_and_keys("development", 100_001, 1, 2)
        feat = study.prefix_features(np.array(pool, dtype=np.uint64))
        self.assertEqual(study.select("uniform", pool, keys, 16, feat)[0], pool[:16])
        sel, spent = study.select("odd32", pool, keys, 16, feat)
        self.assertEqual(set(spent), set(pool[:64]))
        self.assertTrue(set(sel) <= set(pool[:64]))


if __name__ == "__main__":
    unittest.main()
