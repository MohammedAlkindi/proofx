"""Unit tests for SymbolicCounterexampleFinder.

Three cases per the spec:
  1. Applicable + counterexample found
  2. Applicable + no counterexample found
  3. Not applicable (conjecture outside supported scope)

These tests require only sympy (no API key, no network).
"""

import pytest

from src.counterexample import SymbolicCounterexampleFinder


@pytest.fixture
def finder() -> SymbolicCounterexampleFinder:
    return SymbolicCounterexampleFinder()


# ---------------------------------------------------------------------------
# Case 1: Applicable, counterexample exists
# ---------------------------------------------------------------------------

def test_found_parity_n_squared_odd(finder: SymbolicCounterexampleFinder) -> None:
    """n^2 is NOT always odd — n=0 gives 0 (even)."""
    result = finder.search("For all integers n, n^2 is odd")

    assert result["method"] == "symbolic"
    assert result["applicable"] is True
    assert result["found"] is True
    assert result["counterexample"] is not None
    # The counterexample must name the variable and a value
    assert "n =" in result["counterexample"]
    assert result["reasoning"]


def test_found_divisibility_n_squared_divisible_by_3(finder: SymbolicCounterexampleFinder) -> None:
    """n^2 is NOT always divisible by 3 — n=1 gives 1."""
    result = finder.search("For all integers n, n^2 is divisible by 3")

    assert result["method"] == "symbolic"
    assert result["applicable"] is True
    assert result["found"] is True
    assert result["counterexample"] is not None


def test_found_primality_n_squared_is_prime(finder: SymbolicCounterexampleFinder) -> None:
    """n^2 is NOT prime for n >= 2 (and 0, 1 < 2 anyway)."""
    result = finder.search("For all natural numbers n, n^2 is prime")

    assert result["method"] == "symbolic"
    assert result["applicable"] is True
    assert result["found"] is True
    assert result["counterexample"] is not None


# ---------------------------------------------------------------------------
# Case 2: Applicable, no counterexample found in the bounded domain
# ---------------------------------------------------------------------------

def test_not_found_parity_n_squared_plus_n_even(finder: SymbolicCounterexampleFinder) -> None:
    """n^2 + n = n(n+1) is always even (product of consecutive integers)."""
    result = finder.search("For all integers n, n^2 + n is divisible by 2")

    assert result["method"] == "symbolic"
    assert result["applicable"] is True
    assert result["found"] is False
    assert result["counterexample"] is None
    assert result["reasoning"]


def test_not_found_divisibility_6_divides_n3_minus_n(finder: SymbolicCounterexampleFinder) -> None:
    """n^3 - n = (n-1)*n*(n+1) is always divisible by 6."""
    result = finder.search("For all integers n, n^3 - n is divisible by 6")

    assert result["method"] == "symbolic"
    assert result["applicable"] is True
    assert result["found"] is False
    assert result["counterexample"] is None


# ---------------------------------------------------------------------------
# Case 3: Not applicable (conjecture outside supported scope)
# ---------------------------------------------------------------------------

def test_not_applicable_algebraic_structure(finder: SymbolicCounterexampleFinder) -> None:
    """Claims about prime ideals in Noetherian rings are not assessable symbolically."""
    result = finder.search(
        "For every prime ideal P in a Noetherian ring R, "
        "the localization R_P is a local ring."
    )

    assert result["method"] == "symbolic"
    assert result["applicable"] is False
    assert result["found"] is False
    assert result["counterexample"] is None
    assert "Not applicable" in result["reasoning"]


def test_not_applicable_no_quantifier(finder: SymbolicCounterexampleFinder) -> None:
    """Statements without a universal integer quantifier are not applicable."""
    result = finder.search(
        "The Riemann hypothesis states that all non-trivial zeros of the "
        "Riemann zeta function have real part equal to 1/2."
    )

    assert result["method"] == "symbolic"
    assert result["applicable"] is False
    assert result["found"] is False


def test_not_applicable_unsupported_claim_type(finder: SymbolicCounterexampleFinder) -> None:
    """Universal integer claim with an unsupported predicate type is not applicable."""
    result = finder.search(
        "For all integers n, the sequence a_n is convergent."
    )

    assert result["method"] == "symbolic"
    assert result["applicable"] is False
    assert result["found"] is False


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

def test_robustness_empty_like_claim(finder: SymbolicCounterexampleFinder) -> None:
    """Graceful handling of a well-formed quantifier but unparseable expression."""
    result = finder.search("For all integers n, sin(n*pi) is even")

    # sin(n*pi) may or may not parse; either way must not raise
    assert result["method"] == "symbolic"
    assert isinstance(result["found"], bool)
    assert isinstance(result["applicable"], bool)


def test_result_structure_always_complete(finder: SymbolicCounterexampleFinder) -> None:
    """Every result must contain all required keys regardless of outcome."""
    for conjecture in [
        "For all integers n, n^2 is odd",
        "For all integers n, n^2 + n is divisible by 2",
        "For every prime ideal P in a ring, something holds.",
    ]:
        result = finder.search(conjecture)
        assert "method" in result
        assert "applicable" in result
        assert "found" in result
        assert "counterexample" in result
        assert "reasoning" in result
        assert result["method"] == "symbolic"
