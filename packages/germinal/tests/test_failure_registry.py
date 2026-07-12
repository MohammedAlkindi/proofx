"""Tests for src/failure_registry.py.

All tests use the no-Redis (local dict fallback) code path so no Redis server
is required.
"""

from __future__ import annotations

from src.failure_registry import FailureRegistry, _AVOID_THRESHOLD


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _reg() -> FailureRegistry:
    """Return a fresh FailureRegistry in local-dict mode."""
    return FailureRegistry(redis_url="")


# ---------------------------------------------------------------------------
# record_failure / record_success / get_count
# ---------------------------------------------------------------------------


class TestCounts:
    def test_initial_count_is_zero(self):
        assert _reg().get_count("algebra", "formalize") == 0

    def test_record_failure_increments(self):
        reg = _reg()
        reg.record_failure("algebra", "formalize")
        assert reg.get_count("algebra", "formalize") == 1

    def test_record_failure_multiple_times(self):
        reg = _reg()
        for _ in range(3):
            reg.record_failure("topology", "verify")
        assert reg.get_count("topology", "verify") == 3

    def test_record_success_decrements(self):
        reg = _reg()
        reg.record_failure("algebra", "formalize")
        reg.record_failure("algebra", "formalize")
        reg.record_success("algebra", "formalize")
        assert reg.get_count("algebra", "formalize") == 1

    def test_record_success_floors_at_zero(self):
        """Calling record_success when count is already 0 must not go negative."""
        reg = _reg()
        reg.record_success("algebra", "formalize")
        assert reg.get_count("algebra", "formalize") == 0

    def test_stage_keys_are_independent(self):
        reg = _reg()
        reg.record_failure("algebra", "formalize")
        # "verify" stage for the same subfield starts at 0
        assert reg.get_count("algebra", "verify") == 0


# ---------------------------------------------------------------------------
# problematic_subfields
# ---------------------------------------------------------------------------


class TestProblematicSubfields:
    def test_at_threshold_is_flagged(self):
        reg = _reg()
        for _ in range(_AVOID_THRESHOLD):
            reg.record_failure("analysis", "formalize")
        assert "analysis" in reg.problematic_subfields("formalize")

    def test_below_threshold_not_flagged(self):
        reg = _reg()
        for _ in range(_AVOID_THRESHOLD - 1):
            reg.record_failure("algebra", "formalize")
        assert "algebra" not in reg.problematic_subfields("formalize")

    def test_wrong_stage_not_returned(self):
        reg = _reg()
        for _ in range(_AVOID_THRESHOLD):
            reg.record_failure("analysis", "verify")
        # Should appear under "verify", not under "formalize"
        assert "analysis" not in reg.problematic_subfields("formalize")
        assert "analysis" in reg.problematic_subfields("verify")


# ---------------------------------------------------------------------------
# build_avoidance_hint
# ---------------------------------------------------------------------------


class TestBuildAvoidanceHint:
    def test_empty_when_nothing_problematic(self):
        assert _reg().build_avoidance_hint() == ""

    def test_contains_subfield_name_when_problematic(self):
        reg = _reg()
        for _ in range(_AVOID_THRESHOLD):
            reg.record_failure("number_theory", "formalize")
        hint = reg.build_avoidance_hint()
        assert "number_theory" in hint
        assert len(hint) > 0

    def test_mentions_verify_separately(self):
        reg = _reg()
        for _ in range(_AVOID_THRESHOLD):
            reg.record_failure("topology", "verify")
        hint = reg.build_avoidance_hint()
        assert "topology" in hint


# ---------------------------------------------------------------------------
# all_stats
# ---------------------------------------------------------------------------


class TestAllStats:
    def test_empty_registry_returns_empty_dict(self):
        assert _reg().all_stats() == {}

    def test_correct_nested_structure(self):
        reg = _reg()
        reg.record_failure("algebra", "formalize")
        reg.record_failure("algebra", "formalize")
        reg.record_failure("topology", "verify")
        stats = reg.all_stats()
        assert stats["algebra"]["formalize"] == 2
        assert stats["topology"]["verify"] == 1

    def test_multiple_stages_for_same_subfield(self):
        reg = _reg()
        reg.record_failure("algebra", "formalize")
        reg.record_failure("algebra", "verify")
        stats = reg.all_stats()
        assert stats["algebra"]["formalize"] == 1
        assert stats["algebra"]["verify"] == 1
