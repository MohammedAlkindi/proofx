"""Cross-check finite-population formulas by complete enumeration."""

import itertools
import math
from fractions import Fraction

import pytest
from codebase.study_stats import bucket_moments, simultaneous_interval


@pytest.mark.parametrize("sizes", [(6,), (2, 4), (1, 2, 3), (1, 1, 1, 1, 1, 1)])
@pytest.mark.parametrize("quota", range(7))
def test_moments_against_every_ordering(sizes, quota):
    targets = {0, 2, 5}
    membership = [group for group, size in enumerate(sizes) for _ in range(size)]
    counts = [
        (size, sum(membership[n] == group for n in targets)) for group, size in enumerate(sizes)
    ]
    outcomes = []
    for permutation in itertools.permutations(range(6)):
        ranking = sorted(permutation, key=lambda n: membership[n])
        outcomes.append(sum(n in targets for n in ranking[:quota]))
    mean = Fraction(sum(outcomes), len(outcomes))
    variance = sum((Fraction(x) - mean) ** 2 for x in outcomes) / len(outcomes)
    actual = bucket_moments(counts, quota)
    assert actual.mean == mean
    assert actual.variance == variance


@pytest.mark.parametrize(
    "buckets,quota",
    [([(2, 3)], 1), ([(2, -1)], 1), ([(2, 1)], 3), ([(True, 0)], 0), ([(2, 1)], True)],
)
def test_invalid_populations(buckets, quota):
    with pytest.raises(ValueError):
        bucket_moments(buckets, quota)


def test_degenerate_population():
    assert bucket_moments([(0, 0), (1, 1)], 1).mean == 1
    assert bucket_moments([(0, 0), (1, 1)], 1).variance == 0


def test_bound_matches_hand_calculation():
    data = [0.25] * 2048
    radius = 14 * math.log(4 * 54 / 0.05) / (3 * 2047)
    assert simultaneous_interval(data, 54) == pytest.approx((0.25 - radius, 0.25 + radius))
    assert simultaneous_interval([-1, 1], 54) == (-1, 1)


@pytest.mark.parametrize(
    "data,count,alpha",
    [
        ([0], 1, 0.05),
        ([float("nan"), 0], 1, 0.05),
        ([0, 2], 1, 0.05),
        ([0, 0], 0, 0.05),
        ([0, 0], 1, 1),
    ],
)
def test_invalid_intervals(data, count, alpha):
    with pytest.raises(ValueError):
        simultaneous_interval(data, count, alpha)
