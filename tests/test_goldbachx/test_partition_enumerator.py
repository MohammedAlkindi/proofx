"""Tests for GoldbachX PartitionEnumerator module."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parents[2]))

from codebase.GoldbachX.PartitionEnumerator.PartitionEnumerator import (
    _validate_input,
    enumerate_partitions,
    metadata,
    discover,
)


class TestValidateInput:
    def test_valid_input(self):
        _validate_input(4, [2, 3])  # should not raise

    def test_odd_n_raises(self):
        with pytest.raises(ValueError):
            _validate_input(5, [2, 3, 5])

    def test_n_less_than_4_raises(self):
        with pytest.raises(ValueError):
            _validate_input(2, [2])

    def test_empty_primes_raises(self):
        with pytest.raises(ValueError):
            _validate_input(4, [])

    def test_prime_below_2_raises(self):
        with pytest.raises(ValueError):
            _validate_input(4, [1, 2])

    def test_prime_greater_than_n_raises(self):
        with pytest.raises(ValueError):
            _validate_input(4, [2, 5])


class TestEnumeratePartitions:
    def setup_method(self):
        from codebase.GoldbachX.SieveEngine.SieveEngine import eratosthenes
        self.primes_100 = eratosthenes(100)

    def test_goldbach_4(self):
        result = enumerate_partitions(4, [2, 3])
        assert (2, 2) in result

    def test_goldbach_6(self):
        result = enumerate_partitions(6, [2, 3, 5])
        assert (3, 3) in result

    def test_goldbach_10(self):
        result = enumerate_partitions(10, [2, 3, 5, 7])
        assert (3, 7) in result or (7, 3) in result
        assert (5, 5) in result

    def test_all_pairs_sum_to_n(self):
        n = 28
        result = enumerate_partitions(n, self.primes_100[:10])
        for p, q in result:
            assert p + q == n

    def test_unique_flag(self):
        result_unique = enumerate_partitions(10, [2, 3, 5, 7], unique=True)
        result_all = enumerate_partitions(10, [2, 3, 5, 7], unique=False)
        # unique should have p <= q
        for p, q in result_unique:
            assert p <= q

    def test_returns_list(self):
        result = enumerate_partitions(4, [2, 3])
        assert isinstance(result, list)

    def test_large_even_number_has_partitions(self):
        # Goldbach conjecture: every even > 2 should have partitions
        for n in [20, 50, 100]:
            primes = [p for p in self.primes_100 if p <= n]
            result = enumerate_partitions(n, primes)
            assert len(result) >= 1, f"No partitions found for n={n}"


class TestMetadata:
    def test_metadata_returns_dict(self):
        result = metadata()
        assert isinstance(result, dict)
        assert "version" in result

    def test_discover_returns_component(self):
        result = discover()
        assert "component" in result
        assert result["component"] == "PartitionEnumerator"
