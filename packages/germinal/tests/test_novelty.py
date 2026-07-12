"""Tests for src/novelty.py — no external dependencies required."""

from __future__ import annotations

from src.novelty import NoveltyChecker, jaccard


# ---------------------------------------------------------------------------
# jaccard()
# ---------------------------------------------------------------------------


class TestJaccard:
    def test_identical_strings_return_one(self):
        assert jaccard("hello world", "hello world") == 1.0

    def test_disjoint_strings_return_zero(self):
        # "hello world" and "foo bar" share no tokens
        assert jaccard("hello world", "foo bar") == 0.0

    def test_partial_overlap(self):
        # "the cat sat" ∩ "the cat hat" = {"the", "cat"} = 2
        # union = {"the", "cat", "sat", "hat"} = 4  →  0.5
        result = jaccard("the cat sat", "the cat hat")
        assert abs(result - 0.5) < 1e-9

    def test_empty_string_returns_zero(self):
        # _tokenize of empty string is empty frozenset → returns 0.0 early
        assert jaccard("", "hello world") == 0.0
        assert jaccard("hello world", "") == 0.0


# ---------------------------------------------------------------------------
# NoveltyChecker
# ---------------------------------------------------------------------------

# Reference sentences used across multiple tests.  Choosing two statements that
# differ by exactly one token so the Jaccard value is easy to reason about:
#
#   S1 = "every prime number greater than two is odd"
#        tokens: {every, prime, number, greater, than, two, is, odd}  (8 tokens)
#   S2 = "every prime number bigger than two is odd"
#        tokens: {every, prime, number, bigger, than, two, is, odd}   (8 tokens)
#        intersection with S1 = 7 tokens, union = 9 → jaccard ≈ 0.778 > 0.55
#   S3 = "the Riemann hypothesis concerns the zeros of the zeta function"
#        tokens: {the, riemann, hypothesis, concerns, zeros, of, zeta, function}
#        intersection with S1 = {} → jaccard = 0.0

_S1 = "every prime number greater than two is odd"
_S2 = "every prime number bigger than two is odd"
_S3 = "the Riemann hypothesis concerns the zeros of the zeta function"


class TestNoveltyChecker:
    def test_first_statement_is_always_novel(self):
        checker = NoveltyChecker(threshold=0.55)
        is_novel, sim = checker.is_novel(_S1)
        assert is_novel is True
        assert sim == 0.0

    def test_near_duplicate_is_rejected(self):
        checker = NoveltyChecker(threshold=0.55)
        checker.is_novel(_S1)
        is_novel, sim = checker.is_novel(_S2)
        assert is_novel is False
        assert sim >= 0.55

    def test_sufficiently_different_statement_is_novel(self):
        checker = NoveltyChecker(threshold=0.55)
        checker.is_novel(_S1)
        is_novel, sim = checker.is_novel(_S3)
        assert is_novel is True
        assert sim < 0.55

    def test_filter_novel_partitions_correctly(self):
        checker = NoveltyChecker(threshold=0.55)
        conjectures = [
            {"statement": _S1, "id": "1"},
            {"statement": _S2, "id": "2"},  # near-dup of S1
            {"statement": _S3, "id": "3"},
        ]
        novel, duplicates = checker.filter_novel(conjectures)
        assert len(novel) == 2
        assert len(duplicates) == 1
        assert duplicates[0]["id"] == "2"

    def test_filter_novel_attaches_novelty_score(self):
        checker = NoveltyChecker(threshold=0.55)
        conjectures = [{"statement": _S1, "id": "1"}]
        novel, _ = checker.filter_novel(conjectures)
        # First statement seen: sim=0.0 → novelty_score = 1 - 0.0 = 1.0
        assert novel[0]["novelty_score"] == 1.0

    def test_filter_novel_score_for_duplicate(self):
        checker = NoveltyChecker(threshold=0.55)
        conjectures = [
            {"statement": _S1, "id": "1"},
            {"statement": _S2, "id": "2"},
        ]
        _, duplicates = checker.filter_novel(conjectures)
        # novelty_score = 1 - jaccard(S1, S2) ≈ 1 - 0.778 ≈ 0.222
        assert duplicates[0]["novelty_score"] < 0.45

    def test_seed_from_experiments_populates_history(self):
        checker = NoveltyChecker(threshold=0.55)
        checker.seed_from_experiments([{"conjecture": _S1}])
        # A near-duplicate of the seeded statement must be rejected
        is_novel, sim = checker.is_novel(_S2)
        assert is_novel is False
        assert sim >= 0.55

    def test_seed_identical_statement_rejected(self):
        checker = NoveltyChecker(threshold=0.55)
        checker.seed_from_experiments([{"conjecture": _S1}])
        is_novel, sim = checker.is_novel(_S1)
        assert is_novel is False
        assert sim == 1.0
