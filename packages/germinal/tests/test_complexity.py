"""Tests for src/complexity.py.

The Anthropic client is mocked; no live API key is required.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from src.complexity import ComplexityEstimator, _strategy_from_scores


# ---------------------------------------------------------------------------
# _strategy_from_scores
# ---------------------------------------------------------------------------


class TestStrategyFromScores:
    def test_quick_tactics_for_low_scores(self):
        assert _strategy_from_scores(1, 1) == "quick_tactics"
        assert _strategy_from_scores(2, 2) == "quick_tactics"
        assert _strategy_from_scores(1, 2) == "quick_tactics"

    def test_human_review_for_max_formalizability(self):
        assert _strategy_from_scores(5, 1) == "human_review"

    def test_human_review_for_max_proof_difficulty(self):
        assert _strategy_from_scores(1, 5) == "human_review"

    def test_extended_thinking_for_hard_proof(self):
        # p >= 4 and neither f nor p reaches 5
        assert _strategy_from_scores(3, 4) == "extended_thinking"
        assert _strategy_from_scores(4, 4) == "extended_thinking"

    def test_claude_standard_for_middle_difficulty(self):
        assert _strategy_from_scores(3, 3) == "claude_standard"
        assert _strategy_from_scores(4, 3) == "claude_standard"


# ---------------------------------------------------------------------------
# ComplexityEstimator.estimate
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_settings():
    s = MagicMock()
    s.anthropic_api_key = "test-key"
    s.claude_model = "claude-test"
    return s


@pytest.fixture
def estimator(mock_settings):
    with patch("src.complexity.anthropic.Anthropic"):
        return ComplexityEstimator(mock_settings)


def _make_response(payload: dict) -> MagicMock:
    msg = MagicMock()
    content_block = MagicMock()
    content_block.text = json.dumps(payload)
    msg.content = [content_block]
    return msg


class TestComplexityEstimator:
    def test_well_formed_response_all_keys_present(self, estimator):
        """All four expected keys are present and values are correctly typed."""
        payload = {
            "formalizability": 2,
            "proof_difficulty": 3,
            "recommended_strategy": "claude_standard",
            "rationale": "Moderate difficulty.",
        }
        estimator._client.messages.create.return_value = _make_response(payload)

        result = estimator.estimate("For all n, n^2 >= 0")

        assert result["formalizability"] == 2
        assert result["proof_difficulty"] == 3
        assert result["recommended_strategy"] == "claude_standard"
        assert "rationale" in result

    def test_missing_strategy_filled_by_scores_quick_tactics(self, estimator):
        """When recommended_strategy is absent, _strategy_from_scores fills it in."""
        payload = {"formalizability": 1, "proof_difficulty": 2, "rationale": "Easy."}
        estimator._client.messages.create.return_value = _make_response(payload)

        result = estimator.estimate("Simple conjecture")

        assert result["recommended_strategy"] == "quick_tactics"

    def test_missing_strategy_filled_by_scores_extended_thinking(self, estimator):
        payload = {
            "formalizability": 3,
            "proof_difficulty": 4,
            "rationale": "Hard proof.",
        }
        estimator._client.messages.create.return_value = _make_response(payload)

        result = estimator.estimate("Hard conjecture")

        assert result["recommended_strategy"] == "extended_thinking"

    def test_missing_strategy_filled_by_scores_human_review(self, estimator):
        payload = {
            "formalizability": 5,
            "proof_difficulty": 3,
            "rationale": "Very complex.",
        }
        estimator._client.messages.create.return_value = _make_response(payload)

        result = estimator.estimate("Very complex conjecture")

        assert result["recommended_strategy"] == "human_review"

    def test_malformed_json_returns_defaults(self, estimator):
        """Non-JSON response falls back to safe defaults without raising."""
        bad_response = MagicMock()
        content_block = MagicMock()
        content_block.text = "this is not valid json at all"
        bad_response.content = [content_block]
        estimator._client.messages.create.return_value = bad_response

        result = estimator.estimate("Any conjecture")

        assert result["formalizability"] == 3
        assert result["proof_difficulty"] == 3
        assert result["recommended_strategy"] == "claude_standard"

    def test_api_exception_returns_defaults(self, estimator):
        """An API exception is swallowed and the safe default dict is returned."""
        estimator._client.messages.create.side_effect = RuntimeError("timeout")

        result = estimator.estimate("Any conjecture")

        assert result["formalizability"] == 3
        assert result["proof_difficulty"] == 3
        assert result["recommended_strategy"] == "claude_standard"

    def test_markdown_fenced_json_is_parsed(self, estimator):
        """Markdown code fences around the JSON response are stripped before parsing."""
        raw_text = (
            "```json\n"
            + json.dumps(
                {
                    "formalizability": 4,
                    "proof_difficulty": 4,
                    "recommended_strategy": "extended_thinking",
                    "rationale": "Non-trivial.",
                }
            )
            + "\n```"
        )
        msg = MagicMock()
        content_block = MagicMock()
        content_block.text = raw_text
        msg.content = [content_block]
        estimator._client.messages.create.return_value = msg

        result = estimator.estimate("Some conjecture")

        assert result["recommended_strategy"] == "extended_thinking"
