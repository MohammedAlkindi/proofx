"""Tests for CollatzX Analytics module."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parents[2]))

from codebase.CollatzX.Analytics.Analytics import (
    AlgebraicFeatureExtractor,
    CollatzSequence,
    CollatzVariant,
    FeatureUnion,
    FitResult,
    ModelType,
    StatisticalFeatureExtractor,
)


class TestCollatzVariant:
    def test_classic_odd(self):
        f = CollatzVariant.get_function(CollatzVariant.CLASSIC)
        assert f(3) == 10

    def test_classic_even(self):
        f = CollatzVariant.get_function(CollatzVariant.CLASSIC)
        assert f(4) == 2

    def test_fractal_odd(self):
        f = CollatzVariant.get_function(CollatzVariant.FRACTAL)
        assert f(3) == 5  # (3*3+1)//2

    def test_fractal_even(self):
        f = CollatzVariant.get_function(CollatzVariant.FRACTAL)
        assert f(6) == 3

    def test_generalized_defaults(self):
        f = CollatzVariant.get_function(CollatzVariant.GENERALIZED, p=3, q=1, d=2)
        assert f(3) == 10  # same as classic with defaults
        assert f(4) == 2

    def test_unsupported_variant_raises(self):
        with pytest.raises((ValueError, AttributeError)):
            CollatzVariant.get_function(None)  # type: ignore


class TestCollatzSequence:
    def test_sequence_starts_with_seed(self):
        cs = CollatzSequence(starting_value=6)
        assert cs.sequence[0] == 6

    def test_sequence_ends_at_1(self):
        cs = CollatzSequence(starting_value=6)
        assert cs.sequence[-1] == 1

    def test_known_stopping_time_6(self):
        cs = CollatzSequence(starting_value=6)
        # 6 -> 3 -> 10 -> 5 -> 16 -> 8 -> 4 -> 2 -> 1  (8 steps)
        assert cs.stopping_time == 8

    def test_seed_1_is_trivial(self):
        cs = CollatzSequence(starting_value=1)
        assert cs.sequence == [1]
        assert cs.stopping_time == 0

    def test_seed_2(self):
        cs = CollatzSequence(starting_value=2)
        assert cs.sequence == [2, 1]
        assert cs.stopping_time == 1

    def test_power_of_two_8(self):
        cs = CollatzSequence(starting_value=8)
        assert cs.stopping_time == 3  # 8->4->2->1

    def test_max_value_tracked(self):
        cs = CollatzSequence(starting_value=3)
        assert cs.max_value == 16  # 3 peaks at 16

    def test_metadata_convergence(self):
        cs = CollatzSequence(starting_value=6)
        assert cs.metadata.get("converged") is True

    def test_large_seed_terminates(self):
        cs = CollatzSequence(starting_value=27)
        assert cs.sequence[-1] == 1


class TestStatisticalFeatureExtractor:
    def setup_method(self):
        self.extractor = StatisticalFeatureExtractor()
        self.seq = [6, 3, 10, 5, 16, 8, 4, 2, 1]

    def test_empty_returns_zeros(self):
        result = self.extractor.extract([])
        assert all(v == 0.0 for v in result.values())

    def test_length_feature(self):
        result = self.extractor.extract(self.seq)
        assert result["length"] == float(len(self.seq))

    def test_max_value_feature(self):
        result = self.extractor.extract(self.seq)
        assert result["max_value"] == 16.0

    def test_min_value_feature(self):
        result = self.extractor.extract(self.seq)
        assert result["min_value"] == 1.0

    def test_feature_names_count(self):
        assert len(self.extractor.feature_names) == 17

    def test_all_features_present(self):
        result = self.extractor.extract(self.seq)
        for name in self.extractor.feature_names:
            assert name in result

    def test_single_element_no_crash(self):
        result = self.extractor.extract([5])
        assert isinstance(result, dict)

    def test_parity_ratio_all_odd(self):
        result = self.extractor.extract([1, 3, 5, 7])
        assert result["parity_ratio"] == 1.0

    def test_parity_ratio_all_even(self):
        result = self.extractor.extract([2, 4, 6, 8])
        assert result["parity_ratio"] == 0.0


class TestAlgebraicFeatureExtractor:
    def setup_method(self):
        self.extractor = AlgebraicFeatureExtractor()
        self.seq = [6, 3, 10, 5, 16, 8, 4, 2, 1]

    def test_basic_extraction(self):
        result = self.extractor.extract(self.seq)
        assert isinstance(result, dict)
        assert len(result) == 12

    def test_empty_returns_zeros(self):
        result = self.extractor.extract([])
        assert all(v == 0.0 for v in result.values())

    def test_power_of_two_ratio(self):
        result = self.extractor.extract([1, 2, 4, 8, 16])
        assert result["is_power_of_two"] == 1.0

    def test_feature_names_accessible(self):
        assert "prime_factors_count" in self.extractor.feature_names
        assert "binary_density" in self.extractor.feature_names


class TestFeatureUnion:
    def test_combines_extractors(self):
        union = FeatureUnion([StatisticalFeatureExtractor(), AlgebraicFeatureExtractor()])
        result = union.extract([6, 3, 10, 5, 16, 8, 4, 2, 1])
        assert "length" in result
        assert "prime_factors_count" in result

    def test_total_feature_count(self):
        union = FeatureUnion([StatisticalFeatureExtractor(), AlgebraicFeatureExtractor()])
        assert len(union.feature_names) == 17 + 12

    def test_empty_sequence(self):
        union = FeatureUnion([StatisticalFeatureExtractor(), AlgebraicFeatureExtractor()])
        result = union.extract([])
        assert all(v == 0.0 for v in result.values())


class TestFitResult:
    def test_to_dict_serializable(self):
        import json

        import numpy as np

        fr = FitResult(
            parameters=np.array([1.0, 2.0]),
            errors=np.array([0.1, 0.2]),
            r_squared=0.95,
            adjusted_r_squared=0.94,
            aic=100.0,
            bic=110.0,
            model_type=ModelType.LINEAR,
            fit_time=0.5,
        )
        d = fr.to_dict()
        json.dumps(d)  # must not raise

    def test_to_dict_contains_model_type(self):
        import numpy as np

        fr = FitResult(
            parameters=np.array([1.0]),
            errors=np.array([0.0]),
            r_squared=0.9,
            adjusted_r_squared=0.89,
            aic=50.0,
            bic=55.0,
            model_type=ModelType.EXPONENTIAL,
            fit_time=0.1,
        )
        assert fr.to_dict()["model_type"] == "EXPONENTIAL"
