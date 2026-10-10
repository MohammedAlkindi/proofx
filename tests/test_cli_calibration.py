import argparse
import json

import pytest
from codebase.cli import _cmd_calibrate_fit


def _args(tmp_path, labels):
    ledger = tmp_path / "labels.jsonl"
    ledger.write_text(
        "".join(
            json.dumps({"near_miss_score": i / 9, "label": label}) + "\n"
            for i, label in enumerate(labels)
        )
    )
    return argparse.Namespace(
        ledger=str(ledger),
        method="isotonic",
        seed=7,
        output=str(tmp_path / "model.pkl"),
        report=str(tmp_path / "report.json"),
        log_level="WARNING",
        log_file=None,
    )


def test_cli_preserves_invalid_labels_for_validation(tmp_path):
    args = _args(tmp_path, [0] * 5 + [1] * 4 + [0.5])
    with pytest.raises(ValueError, match="binary"):
        _cmd_calibrate_fit(args)


def test_cli_saves_held_out_report(tmp_path):
    args = _args(tmp_path, [0] * 5 + [1] * 5)
    assert _cmd_calibrate_fit(args) == 0
    report = json.loads((tmp_path / "report.json").read_text())
    assert report["n_train"] == 8
    assert report["n_evaluation"] == 2
    assert report["target"] == "user_defined_label_1"
