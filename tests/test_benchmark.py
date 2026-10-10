"""Check experiment reproducibility, independent counting and tamper detection."""

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest
from codebase.benchmark import BenchmarkConfig, run_benchmark, verify_bundle


def test_reproducible_ledgers_and_equal_budgets(tmp_path):
    config = BenchmarkConfig(max_n=100, budget=12, seeds=(3, 7))
    first = run_benchmark(config, tmp_path / "first")
    second = run_benchmark(config, tmp_path / "second")
    assert first["artifacts"] == second["artifacts"]
    assert len(first["runs"]) == 6
    assert all(run["evaluated"] == 12 for run in first["runs"])
    assert verify_bundle(tmp_path / "first") == {
        "reference_candidates": 49,
        "runs": 6,
        "evaluations": 72,
    }
    rows = [
        json.loads(line) for line in (tmp_path / "first/reference.jsonl").read_text().splitlines()
    ]
    assert rows[0]["candidate"] == 4
    assert rows[0]["actual_partitions"] == 1
    assert rows[3]["candidate"] == 10
    assert rows[3]["actual_partitions"] == 2
    assert rows[3]["witness"] == [3, 7]


def test_directed_completion_can_cover_whole_domain(tmp_path):
    manifest = run_benchmark(BenchmarkConfig(max_n=20, budget=9, seeds=(1,)), tmp_path / "run")
    assert all(run["rare_recall"] == 1 for run in manifest["runs"])
    verify_bundle(tmp_path / "run")


@pytest.mark.parametrize(
    "change", ["checksum", "count", "summary", "missing_run", "duplicate_run", "path"]
)
def test_verifier_rejects_corrupt_artifacts(tmp_path, change):
    directory = tmp_path / "run"
    manifest = run_benchmark(BenchmarkConfig(max_n=40, budget=5, seeds=(0,)), directory)
    if change in {"checksum", "count"}:
        path = directory / "reference.jsonl"
        rows = [json.loads(line) for line in path.read_text().splitlines()]
        rows[0]["actual_partitions"] = 0
        path.write_text("\n".join(json.dumps(row) for row in rows) + "\n")
        if change == "count":
            # Updating the checksum does not fool the independent recount.
            manifest["artifacts"]["reference.jsonl"] = hashlib.sha256(path.read_bytes()).hexdigest()
    elif change == "summary":
        manifest["runs"][0]["rare_hits"] += 1
    elif change == "missing_run":
        manifest["runs"].pop()
    elif change == "duplicate_run":
        manifest["runs"].append(manifest["runs"][0])
    else:
        manifest["artifacts"]["../elsewhere.jsonl"] = "0" * 64
    (directory / "manifest.json").write_text(json.dumps(manifest))
    with pytest.raises(ValueError):
        verify_bundle(directory)


@pytest.mark.parametrize(
    "config",
    [
        BenchmarkConfig(max_n=5),
        BenchmarkConfig(max_n=30_000),
        BenchmarkConfig(budget=0),
        BenchmarkConfig(max_n=10, budget=5),
        BenchmarkConfig(seeds=()),
        BenchmarkConfig(seeds=(0, 0)),
        BenchmarkConfig(seeds=(-1,)),
    ],
)
def test_invalid_protocol_rejected_before_creating_output(tmp_path, config):
    with pytest.raises(ValueError):
        run_benchmark(config, tmp_path / "run")
    assert not (tmp_path / "run").exists()


def test_published_output_cannot_be_overwritten(tmp_path):
    config = BenchmarkConfig(max_n=10, budget=2, seeds=(0,))
    run_benchmark(config, tmp_path / "run")
    before = (tmp_path / "run/manifest.json").read_bytes()
    with pytest.raises(FileExistsError):
        run_benchmark(config, tmp_path / "run")
    assert (tmp_path / "run/manifest.json").read_bytes() == before


def test_cli_runs_and_verifies_a_bundle(tmp_path):
    directory = tmp_path / "run"
    root = Path(__file__).resolve().parents[1]
    for args in (
        [
            "goldbach",
            "--max-n",
            "20",
            "--budget",
            "4",
            "--seeds",
            "0",
            "--output-dir",
            str(directory),
        ],
        ["verify", str(directory)],
    ):
        result = subprocess.run(
            [sys.executable, "-m", "codebase.cli", "benchmark", *args],
            cwd=root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=90,
        )
        assert result.returncode == 0, result.stdout + result.stderr
        assert '"evaluations": 12' in result.stdout
