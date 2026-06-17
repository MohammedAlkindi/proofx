"""Tests for src/formalizer.py.

All Claude API calls and Lean sandbox calls are mocked — no live API key or
Lean install is required to run this file.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.formalizer import Formalizer, _strip_fences


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_settings():
    s = MagicMock()
    s.anthropic_api_key = "test-key"
    s.claude_model = "claude-test"
    s.lean_sandbox_dir = ".lean_sandbox_test"
    s.lean_timeout = 30
    s.formalize_repair_attempts = 3
    return s


@pytest.fixture
def formalizer(mock_settings):
    with patch("src.formalizer.anthropic.Anthropic"):
        return Formalizer(mock_settings)


def _sandbox(build_results: list[tuple[bool, str]]) -> MagicMock:
    """Return a mock LeanSandbox whose .build() yields the given results in order."""
    mock = MagicMock()
    mock.build = AsyncMock(side_effect=build_results)
    return mock


# ---------------------------------------------------------------------------
# _strip_fences
# ---------------------------------------------------------------------------


class TestStripFences:
    def test_no_fences_unchanged(self):
        code = "import Mathlib\ntheorem foo : True := sorry"
        assert _strip_fences(code) == code

    def test_strips_fences_with_language_tag(self):
        text = "```lean\nimport Mathlib\ntheorem foo : True := sorry\n```"
        assert _strip_fences(text) == "import Mathlib\ntheorem foo : True := sorry"

    def test_strips_fences_without_language_tag(self):
        text = "```\nimport Mathlib\ntheorem foo : True := sorry\n```"
        assert _strip_fences(text) == "import Mathlib\ntheorem foo : True := sorry"

    def test_strips_leading_and_trailing_whitespace(self):
        text = "  \ntheorem foo : True := sorry\n  "
        assert _strip_fences(text) == "theorem foo : True := sorry"


# ---------------------------------------------------------------------------
# Formalizer.formalize
# ---------------------------------------------------------------------------


class TestFormalize:
    _LEAN = "import Mathlib\ntheorem foo : True := sorry"

    def _patch_deps(self, sandbox):
        return (
            patch("src.formalizer.get_sandbox", return_value=sandbox),
            patch("src.formalizer.mathlib_rag.retrieve", return_value=[]),
            patch("src.formalizer.mathlib_rag.format_for_prompt", return_value=""),
        )

    def test_successful_first_attempt(self, formalizer):
        """is_valid=True on first attempt; repair loop is never triggered."""
        sandbox = _sandbox([(True, "")])

        p1, p2, p3 = self._patch_deps(sandbox)
        with p1, p2, p3:
            formalizer._call_api = MagicMock(return_value=self._LEAN)
            result = formalizer.formalize("For all n, n^2 >= 0")

        assert result["is_valid"] is True
        assert result["lean_code"] == self._LEAN
        assert result["repair_attempts"] == 1
        formalizer._call_api.assert_called_once()

    def test_repair_loop_succeeds_on_second_attempt(self, formalizer):
        """First build fails; error is fed back into the second API call which succeeds."""
        first_error = "type mismatch at line 3"
        sandbox = _sandbox([(False, first_error), (True, "")])

        p1, p2, p3 = self._patch_deps(sandbox)
        with p1, p2, p3:
            api_mock = MagicMock(return_value=self._LEAN)
            formalizer._call_api = api_mock
            result = formalizer.formalize("For all n, n^2 >= 0")

        assert result["is_valid"] is True
        assert result["repair_attempts"] == 2
        assert api_mock.call_count == 2
        # Third positional arg of the second call must be the previous error
        second_call_positional = api_mock.call_args_list[1][0]
        assert first_error in second_call_positional[2]

    def test_all_repair_attempts_exhausted_returns_invalid(self, formalizer):
        """Exhausting all attempts: is_valid=False with the last error preserved."""
        error = "unknown identifier 'Nat.foo'"
        sandbox = _sandbox([(False, error)] * 3)

        p1, p2, p3 = self._patch_deps(sandbox)
        with p1, p2, p3:
            formalizer._call_api = MagicMock(return_value="bad lean code")
            result = formalizer.formalize("hard conjecture", max_attempts=3)

        assert result["is_valid"] is False
        assert result["error_log"] == error
        assert result["repair_attempts"] == 3

    def test_api_exception_returns_gracefully(self, formalizer):
        """A Claude API exception on the first call returns is_valid=False without raising."""
        sandbox = _sandbox([])

        p1, p2, p3 = self._patch_deps(sandbox)
        with p1, p2, p3:
            formalizer._call_api = MagicMock(side_effect=RuntimeError("network error"))
            result = formalizer.formalize("some conjecture")

        assert result["is_valid"] is False
        assert "network error" in result["error_log"]
        assert result["lean_code"] == ""
