"""Tests for the multi-method counterexample ensemble."""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any

from src import counterexample as cx


def _method(
    method: str,
    found: bool,
    counterexample: str | None = None,
    applicable: bool = True,
) -> dict[str, Any]:
    return {
        "method": method,
        "applicable": applicable,
        "found": found,
        "counterexample": counterexample,
        "reasoning": "test result",
    }


def test_wolfram_cache_hit_avoids_second_lookup(tmp_path: Path) -> None:
    cache = cx.WolframQueryCache(ttl_seconds=60, cache_dir=tmp_path)
    statement_hash = "abc"
    query = "is false?"
    value = [["Result", "No"]]

    assert cache.get(statement_hash, query) is None
    cache.set(statement_hash, query, value)

    assert cache.get(statement_hash, query) == value


def test_wolfram_cache_expired_entry_is_miss(tmp_path: Path) -> None:
    cache = cx.WolframQueryCache(ttl_seconds=1, cache_dir=tmp_path)
    statement_hash = "abc"
    query = "is false?"
    cache.set(statement_hash, query, [("Result", "No")])

    path = cache._path(statement_hash, query)
    path.write_text('{"created_at": 0, "value": [["Result", "No"]]}')

    assert cache.get(statement_hash, query) is None


def test_local_verification_accepts_real_counterexample() -> None:
    result = cx.LocalCounterexampleVerifier.verify(
        "For all integers n, n^2 is odd",
        "n = 0: expression = 0",
    )

    assert result["verified"] is True


def test_local_verification_rejects_invalid_counterexample() -> None:
    result = cx.LocalCounterexampleVerifier.verify(
        "For all integers n, n^2 is odd",
        "n = 1: expression = 1",
    )

    assert result["verified"] is False
    assert "satisfies" in result["reason"]


def test_consensus_calculation(monkeypatch: Any) -> None:
    def fake_run(
        conjecture: str,
        subfield: str,
        settings: Any,
    ) -> dict[str, dict[str, Any]]:
        return {
            "claude": cx._normalize_method_result(
                _method("llm", True, "n = 0"), "claude", conjecture
            ),
            "sympy": cx._normalize_method_result(
                _method("symbolic", False), "sympy", conjecture
            ),
            "wolfram_alpha": cx._normalize_method_result(
                _method("wolfram", False), "wolfram_alpha", conjecture
            ),
        }

    monkeypatch.setattr(cx, "_run_backend_searches", fake_run)

    result = cx.search_ensemble("For all integers n, n^2 is odd")

    assert result["found"] is True
    assert result["methods_attempted"] == 3
    assert result["methods_applicable"] == 3
    assert result["methods_found_counterexample"] == 1
    assert result["consensus"] == "counterexample_found"
    assert result["llm_result"]["verified_locally"] is True


def test_unrefuted_consensus_when_all_applicable_no_hits(monkeypatch: Any) -> None:
    def fake_run(
        conjecture: str,
        subfield: str,
        settings: Any,
    ) -> dict[str, dict[str, Any]]:
        return {
            "claude": cx._normalize_method_result(
                _method("llm", False), "claude", conjecture
            ),
            "sympy": cx._normalize_method_result(
                _method("symbolic", False), "sympy", conjecture
            ),
            "wolfram_alpha": cx._normalize_method_result(
                _method("wolfram", False), "wolfram_alpha", conjecture
            ),
        }

    monkeypatch.setattr(cx, "_run_backend_searches", fake_run)

    result = cx.search_ensemble("For all integers n, n^2 + n is divisible by 2")

    assert result["consensus"] == "unrefuted"


def test_timeout_handling_continues_with_partial_results(monkeypatch: Any) -> None:
    class SlowClaude:
        def __init__(self, settings: Any = None) -> None:
            pass

        def search(self, conjecture: str, subfield: str = "") -> dict[str, Any]:
            time.sleep(0.2)
            return _method("llm", True, "n = 0")

    class FastSympy:
        def search(self, conjecture: str, subfield: str = "") -> dict[str, Any]:
            return _method("symbolic", False)

    class FastWolfram:
        def __init__(self, settings: Any = None) -> None:
            pass

        def search(self, conjecture: str, subfield: str = "") -> dict[str, Any]:
            return _method("wolfram", False)

    monkeypatch.setattr(cx, "BACKEND_TIMEOUT_SECONDS", 0.05)
    monkeypatch.setattr(cx, "CounterexampleFinder", SlowClaude)
    monkeypatch.setattr(cx, "SymbolicCounterexampleFinder", FastSympy)
    monkeypatch.setattr(cx, "WolframCounterexampleFinder", FastWolfram)

    result = cx.search_ensemble("For all integers n, n^2 + n is divisible by 2")

    assert result["llm_result"]["timed_out"] is True
    assert result["symbolic_result"].get("timed_out") is not True
    assert result["wolfram_result"].get("timed_out") is not True
    assert result["consensus"] == "partial_failure"


def test_disagreement_logging(monkeypatch: Any, caplog: Any) -> None:
    def fake_run(
        conjecture: str,
        subfield: str,
        settings: Any,
    ) -> dict[str, dict[str, Any]]:
        return {
            "claude": cx._normalize_method_result(
                _method("llm", True, "n = 0"), "claude", conjecture
            ),
            "sympy": cx._normalize_method_result(
                _method("symbolic", False), "sympy", conjecture
            ),
            "wolfram_alpha": cx._normalize_method_result(
                _method("wolfram", True, "n = 0"),
                "wolfram_alpha",
                conjecture,
            ),
        }

    monkeypatch.setattr(cx, "_run_backend_searches", fake_run)
    caplog.set_level(logging.INFO, logger="src.counterexample")

    result = cx.search_ensemble("For all integers n, n^2 is odd")

    assert result["method_disagreement"] == {
        "claude_found": True,
        "sympy_found": False,
        "wolfram_found": True,
    }
    assert "Counterexample backend disagreement" in caplog.text
