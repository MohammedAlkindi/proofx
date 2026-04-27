"""Shared test fixtures and configuration."""

import pytest


@pytest.fixture(scope="session")
def small_prime_list():
    return [2, 3, 5, 7, 11, 13, 17, 19, 23, 29]


@pytest.fixture(scope="session")
def collatz_known_sequences():
    """Known Collatz sequences for test verification."""
    return {
        1: [1],
        2: [2, 1],
        3: [3, 10, 5, 16, 8, 4, 2, 1],
        6: [6, 3, 10, 5, 16, 8, 4, 2, 1],
        27: None,  # long — just check it terminates
    }
