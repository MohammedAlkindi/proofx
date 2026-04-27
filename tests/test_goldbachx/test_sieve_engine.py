"""Tests for GoldbachX SieveEngine module."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parents[2]))

from codebase.GoldbachX.SieveEngine.SieveEngine import (
    _validate_limit,
    _validate_primes,
    atkin,
    eratosthenes,
)

FIRST_25_PRIMES = [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47, 53, 59, 61, 67, 71, 73, 79, 83, 89, 97]


class TestValidateLimit:
    def test_valid_limits(self):
        for n in [2, 10, 100, 1000]:
            _validate_limit(n)  # should not raise

    def test_limit_1_raises(self):
        with pytest.raises(ValueError, match="Limit must be"):
            _validate_limit(1)

    def test_limit_0_raises(self):
        with pytest.raises(ValueError):
            _validate_limit(0)

    def test_negative_raises(self):
        with pytest.raises(ValueError):
            _validate_limit(-5)


class TestValidatePrimes:
    def test_valid_primes(self):
        _validate_primes([2, 3, 5, 7, 11])  # should not raise

    def test_empty_raises(self):
        with pytest.raises(ValueError, match="Empty"):
            _validate_primes([])

    def test_wrong_first_prime_raises(self):
        with pytest.raises(ValueError):
            _validate_primes([3, 5, 7])

    def test_non_increasing_raises(self):
        with pytest.raises(ValueError):
            _validate_primes([2, 7, 5])


class TestEratosthenes:
    def test_primes_up_to_2(self):
        assert eratosthenes(2) == [2]

    def test_primes_up_to_10(self):
        assert eratosthenes(10) == [2, 3, 5, 7]

    def test_primes_up_to_30(self):
        assert eratosthenes(30) == [2, 3, 5, 7, 11, 13, 17, 19, 23, 29]

    def test_primes_up_to_100(self):
        result = eratosthenes(100)
        assert result == FIRST_25_PRIMES

    def test_all_results_are_prime(self):
        primes = set(eratosthenes(100))
        for n in range(2, 101):
            is_prime = all(n % i != 0 for i in range(2, int(n**0.5) + 1))
            assert (n in primes) == is_prime

    def test_invalid_limit_raises(self):
        with pytest.raises(ValueError):
            eratosthenes(1)


class TestAtkin:
    def test_primes_up_to_10(self):
        assert atkin(10) == [2, 3, 5, 7]

    def test_primes_up_to_30(self):
        assert atkin(30) == [2, 3, 5, 7, 11, 13, 17, 19, 23, 29]

    def test_matches_eratosthenes(self):
        for limit in [10, 50, 100]:
            assert atkin(limit) == eratosthenes(limit)

    def test_invalid_limit_raises(self):
        with pytest.raises(ValueError):
            atkin(1)
