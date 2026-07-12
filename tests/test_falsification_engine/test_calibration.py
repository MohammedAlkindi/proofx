"""Tests for the score calibration module (PlattCalibrator, IsotonicCalibrator,
annotate_ledger).  IsotonicCalibrator tests are skipped when scikit-learn is
absent; PlattCalibrator tests require only scipy."""

import json
import sys
import time
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).parents[2]))

from codebase.FalsificationEngine.calibration import (
    CalibrationReport,
    PlattCalibrator,
    annotate_ledger,
)

# ── Helpers ───────────────────────────────────────────────────────────────────


def _synthetic(n: int = 30, seed: int = 0):
    """Return (scores, labels) that are well-separated enough for convergence."""
    rng = np.random.default_rng(seed)
    scores = rng.uniform(0.0, 1.0, n)
    labels = (scores > 0.5).astype(int).tolist()
    return scores.tolist(), labels


def _write_ledger(path: Path, n: int = 5) -> None:
    """Write a minimal JSONL ledger with evenly-spaced scores to path."""
    lines = []
    for i in range(n):
        entry = {
            "candidate": i * 10 + 4,
            "conjecture": "goldbach",
            "strategy": "test",
            "features": {},
            "near_miss_score": round(i / max(n - 1, 1), 6),
            "details": {},
            "timestamp": time.time(),
            "rng_seed": 0,
        }
        lines.append(json.dumps(entry))
    path.write_text("\n".join(lines), encoding="utf-8")


# ── CalibrationReport ─────────────────────────────────────────────────────────


class TestCalibrationReport:
    def _report(self) -> CalibrationReport:
        return CalibrationReport(
            method="test",
            n_samples=20,
            brier_score=0.1,
            log_loss=0.3,
            expected_calibration_error=0.05,
            score_min=0.0,
            score_max=1.0,
            seed=42,
        )

    def test_to_dict_is_json_serializable(self):
        json.dumps(self._report().to_dict())  # must not raise

    def test_to_dict_contains_method(self):
        assert self._report().to_dict()["method"] == "test"

    def test_to_dict_contains_n_samples(self):
        assert self._report().to_dict()["n_samples"] == 20

    def test_summary_is_string(self):
        assert isinstance(self._report().summary(), str)

    def test_summary_contains_method(self):
        assert "test" in self._report().summary()

    def test_summary_contains_brier(self):
        assert "Brier" in self._report().summary()


# ── PlattCalibrator ───────────────────────────────────────────────────────────


class TestPlattCalibrator:
    def test_predict_before_fit_raises_runtime_error(self):
        with pytest.raises(RuntimeError):
            PlattCalibrator().predict([0.5])

    def test_fit_returns_calibration_report(self):
        scores, labels = _synthetic()
        report = PlattCalibrator().fit(scores, labels)
        assert isinstance(report, CalibrationReport)

    def test_report_method_is_platt(self):
        scores, labels = _synthetic()
        report = PlattCalibrator().fit(scores, labels)
        assert report.method == "platt"

    def test_report_n_samples_matches(self):
        scores, labels = _synthetic(n=20)
        report = PlattCalibrator().fit(scores, labels)
        assert report.n_samples == 20

    def test_predict_output_in_unit_interval(self):
        scores, labels = _synthetic()
        cal = PlattCalibrator()
        cal.fit(scores, labels)
        probs = cal.predict(scores)
        assert np.all(probs >= 0.0) and np.all(probs <= 1.0)

    def test_predict_output_length_matches_input(self):
        scores, labels = _synthetic(n=20)
        cal = PlattCalibrator()
        cal.fit(scores, labels)
        assert len(cal.predict(scores)) == 20

    def test_predict_higher_score_not_lower_prob(self):
        # Platt is monotone: higher raw score → higher calibrated probability
        scores, labels = _synthetic()
        cal = PlattCalibrator()
        cal.fit(scores, labels)
        test_inputs = [0.1, 0.5, 0.9]
        probs = cal.predict(test_inputs)
        assert probs[0] <= probs[1] <= probs[2]

    def test_brier_score_in_report_is_non_negative(self):
        scores, labels = _synthetic()
        report = PlattCalibrator().fit(scores, labels)
        assert report.brier_score >= 0.0

    def test_save_load_roundtrip_predictions_match(self, tmp_path):
        scores, labels = _synthetic()
        cal = PlattCalibrator()
        cal.fit(scores, labels)
        path = tmp_path / "cal.pkl"
        cal.save(path)
        loaded = PlattCalibrator.load(path)
        np.testing.assert_allclose(cal.predict(scores), loaded.predict(scores))

    def test_save_creates_file(self, tmp_path):
        scores, labels = _synthetic()
        cal = PlattCalibrator()
        cal.fit(scores, labels)
        path = tmp_path / "cal.pkl"
        cal.save(path)
        assert path.exists()


# ── IsotonicCalibrator ────────────────────────────────────────────────────────


class TestIsotonicCalibrator:
    def test_fit_requires_10_samples(self):
        pytest.importorskip("sklearn", reason="scikit-learn not installed")
        from codebase.FalsificationEngine.calibration import IsotonicCalibrator

        with pytest.raises(ValueError, match="10"):
            IsotonicCalibrator().fit([0.1, 0.9], [0, 1])

    def test_fit_returns_calibration_report(self):
        pytest.importorskip("sklearn", reason="scikit-learn not installed")
        from codebase.FalsificationEngine.calibration import IsotonicCalibrator

        scores, labels = _synthetic(n=30)
        report = IsotonicCalibrator().fit(scores, labels)
        assert isinstance(report, CalibrationReport)

    def test_report_method_is_isotonic(self):
        pytest.importorskip("sklearn", reason="scikit-learn not installed")
        from codebase.FalsificationEngine.calibration import IsotonicCalibrator

        scores, labels = _synthetic(n=30)
        report = IsotonicCalibrator().fit(scores, labels)
        assert report.method == "isotonic"

    def test_predict_output_in_unit_interval(self):
        pytest.importorskip("sklearn", reason="scikit-learn not installed")
        from codebase.FalsificationEngine.calibration import IsotonicCalibrator

        scores, labels = _synthetic(n=30)
        cal = IsotonicCalibrator()
        cal.fit(scores, labels)
        probs = cal.predict(scores)
        assert np.all(probs >= 0.0) and np.all(probs <= 1.0)

    def test_predict_before_fit_raises_runtime_error(self):
        pytest.importorskip("sklearn", reason="scikit-learn not installed")
        from codebase.FalsificationEngine.calibration import IsotonicCalibrator

        with pytest.raises(RuntimeError):
            IsotonicCalibrator().predict([0.5])

    def test_labels_must_be_binary(self):
        pytest.importorskip("sklearn", reason="scikit-learn not installed")
        from codebase.FalsificationEngine.calibration import IsotonicCalibrator

        scores = list(range(15))
        labels = list(range(15))  # not binary
        with pytest.raises(ValueError):
            IsotonicCalibrator().fit(scores, labels)


# ── annotate_ledger ───────────────────────────────────────────────────────────


class TestAnnotateLedger:
    def _fitted_calibrator(self) -> PlattCalibrator:
        scores, labels = _synthetic(n=30)
        cal = PlattCalibrator()
        cal.fit(scores, labels)
        return cal

    def test_output_file_is_created(self, tmp_path):
        ledger_path = tmp_path / "ledger.jsonl"
        _write_ledger(ledger_path, n=5)
        out = tmp_path / "out.jsonl"
        annotate_ledger(ledger_path, self._fitted_calibrator(), out)
        assert out.exists()

    def test_output_has_same_line_count(self, tmp_path):
        ledger_path = tmp_path / "ledger.jsonl"
        _write_ledger(ledger_path, n=5)
        out = tmp_path / "out.jsonl"
        annotate_ledger(ledger_path, self._fitted_calibrator(), out)
        assert len(out.read_text(encoding="utf-8").strip().splitlines()) == 5

    def test_calibrated_prob_key_present(self, tmp_path):
        ledger_path = tmp_path / "ledger.jsonl"
        _write_ledger(ledger_path, n=5)
        out = tmp_path / "out.jsonl"
        annotate_ledger(ledger_path, self._fitted_calibrator(), out)
        for line in out.read_text(encoding="utf-8").strip().splitlines():
            assert "calibrated_prob" in json.loads(line)

    def test_calibrated_prob_in_unit_interval(self, tmp_path):
        ledger_path = tmp_path / "ledger.jsonl"
        _write_ledger(ledger_path, n=5)
        out = tmp_path / "out.jsonl"
        annotate_ledger(ledger_path, self._fitted_calibrator(), out)
        for line in out.read_text(encoding="utf-8").strip().splitlines():
            prob = json.loads(line)["calibrated_prob"]
            assert 0.0 <= prob <= 1.0

    def test_original_fields_preserved(self, tmp_path):
        ledger_path = tmp_path / "ledger.jsonl"
        _write_ledger(ledger_path, n=3)
        out = tmp_path / "out.jsonl"
        annotate_ledger(ledger_path, self._fitted_calibrator(), out)
        for line in out.read_text(encoding="utf-8").strip().splitlines():
            d = json.loads(line)
            assert "candidate" in d
            assert "near_miss_score" in d
            assert "conjecture" in d

    def test_default_output_path_uses_calibrated_suffix(self, tmp_path):
        ledger_path = tmp_path / "my_ledger.jsonl"
        _write_ledger(ledger_path, n=3)
        annotate_ledger(ledger_path, self._fitted_calibrator())
        expected = tmp_path / "my_ledger.calibrated.jsonl"
        assert expected.exists()
