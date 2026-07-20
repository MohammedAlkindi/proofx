import json

import pytest
from codebase import verified_runs
from codebase.verified_runs import (
    SCHEMA_VERSION,
    build_verified_run_bundle,
    environment_is_complete,
    validate_bundle,
    write_bundle,
)


def test_build_verified_run_bundle_contains_all_public_engines():
    bundle = build_verified_run_bundle(
        seed=7,
        collatz_start=1,
        collatz_end=12,
        collatz_fuel=500,
        goldbach_start=4,
        goldbach_end=30,
        riemann_limit=100,
    )

    assert bundle["schema_version"] == SCHEMA_VERSION
    runs = bundle["runs"]
    assert {run["engine"] for run in runs} == {"CollatzX", "GoldbachX", "RiemannX"}
    assert all(run["seed"] == 7 for run in runs)
    assert all(run["reproduce"].startswith("python -m codebase.cli run") for run in runs)

    collatz = next(run for run in runs if run["engine"] == "CollatzX")
    assert collatz["claim_level"] == "bounded_run"
    assert collatz["metrics"]["inputs_checked"] == 12
    assert collatz["metrics"]["converged"] == 12

    goldbach = next(run for run in runs if run["engine"] == "GoldbachX")
    assert goldbach["status"] == "no_counterexample_found"
    assert goldbach["metrics"]["zero_partition_inputs"] == 0

    riemann = next(run for run in runs if run["engine"] == "RiemannX")
    assert riemann["claim_level"] == "numerical_diagnostic"
    assert riemann["metrics"]["pi_limit"] == 25


def test_validate_bundle_rejects_missing_run_fields():
    bundle = {
        "schema_version": SCHEMA_VERSION,
        "runs": [{"engine": "CollatzX"}],
    }

    try:
        validate_bundle(bundle)
    except ValueError as exc:
        assert "missing" in str(exc)
    else:
        raise AssertionError("validate_bundle should reject incomplete run entries")


def test_environment_names_unresolved_dependencies_instead_of_recording_null(monkeypatch):
    monkeypatch.setattr(
        verified_runs, "DEFAULT_DEPENDENCIES", ("numpy", "proofx-not-a-real-package")
    )

    environment = verified_runs._environment()

    assert None not in environment["dependencies"].values()
    assert "proofx-not-a-real-package" not in environment["dependencies"]
    assert environment["dependencies_unresolved"] == ["proofx-not-a-real-package"]
    assert environment["dependencies_complete"] is False


def test_environment_is_complete_when_every_declared_dependency_resolves(monkeypatch):
    monkeypatch.setattr(verified_runs, "DEFAULT_DEPENDENCIES", ("numpy",))

    environment = verified_runs._environment()

    assert environment["dependencies_unresolved"] == []
    assert environment["dependencies_complete"] is True
    assert environment["dependencies"]["numpy"]


def test_environment_is_complete_rejects_a_bundle_with_unresolved_dependencies(monkeypatch):
    monkeypatch.setattr(
        verified_runs, "DEFAULT_DEPENDENCIES", ("numpy", "proofx-not-a-real-package")
    )

    bundle = build_verified_run_bundle(engines=("goldbach",), goldbach_start=4, goldbach_end=20)

    assert environment_is_complete(bundle) is False


def test_environment_is_complete_accepts_a_fully_resolved_bundle(monkeypatch):
    monkeypatch.setattr(verified_runs, "DEFAULT_DEPENDENCIES", ("numpy",))

    bundle = build_verified_run_bundle(engines=("goldbach",), goldbach_start=4, goldbach_end=20)

    assert environment_is_complete(bundle) is True


def test_validate_bundle_rejects_null_dependency_versions():
    bundle = build_verified_run_bundle(engines=("goldbach",), goldbach_start=4, goldbach_end=20)
    bundle["environment"]["dependencies"]["numpy"] = None

    with pytest.raises(ValueError, match="dependency"):
        validate_bundle(bundle)


def test_validate_bundle_rejects_an_environment_missing_completeness_fields():
    bundle = build_verified_run_bundle(engines=("goldbach",), goldbach_start=4, goldbach_end=20)
    del bundle["environment"]["dependencies_complete"]

    with pytest.raises(ValueError, match="environment"):
        validate_bundle(bundle)


def _bundle(monkeypatch, dependencies):
    monkeypatch.setattr(verified_runs, "DEFAULT_DEPENDENCIES", dependencies)
    return build_verified_run_bundle(engines=("goldbach",), goldbach_start=4, goldbach_end=20)


def test_publish_bundle_writes_when_no_artifact_exists_yet(tmp_path, monkeypatch):
    bundle = _bundle(monkeypatch, ("numpy",))
    output = tmp_path / "verified-runs.json"

    written, _ = verified_runs.publish_bundle(bundle, output)

    assert written is True
    assert json.loads(output.read_text(encoding="utf-8"))["schema_version"] == SCHEMA_VERSION


def test_publish_bundle_keeps_complete_provenance_over_an_incomplete_rebuild(tmp_path, monkeypatch):
    output = tmp_path / "verified-runs.json"
    complete = _bundle(monkeypatch, ("numpy",))
    write_bundle(complete, output)

    degraded = _bundle(monkeypatch, ("numpy", "proofx-not-a-real-package"))
    written, reason = verified_runs.publish_bundle(degraded, output)

    assert written is False
    assert "proofx-not-a-real-package" in reason
    kept = json.loads(output.read_text(encoding="utf-8"))
    assert kept["environment"]["dependencies_complete"] is True
    assert kept["generated_at"] == complete["generated_at"]


def test_publish_bundle_replaces_an_existing_incomplete_artifact(tmp_path, monkeypatch):
    output = tmp_path / "verified-runs.json"
    write_bundle(_bundle(monkeypatch, ("numpy", "proofx-not-a-real-package")), output)

    fresh = _bundle(monkeypatch, ("numpy",))
    written, _ = verified_runs.publish_bundle(fresh, output)

    assert written is True
    assert json.loads(output.read_text(encoding="utf-8"))["generated_at"] == fresh["generated_at"]


def test_publish_bundle_writes_incomplete_artifact_when_nothing_better_is_on_disk(
    tmp_path, monkeypatch
):
    degraded = _bundle(monkeypatch, ("numpy", "proofx-not-a-real-package"))
    output = tmp_path / "verified-runs.json"

    written, _ = verified_runs.publish_bundle(degraded, output)

    assert written is True
    assert (
        json.loads(output.read_text(encoding="utf-8"))["environment"]["dependencies_complete"]
        is False
    )


def test_publish_bundle_replaces_an_unreadable_existing_artifact(tmp_path, monkeypatch):
    output = tmp_path / "verified-runs.json"
    output.write_text("{ not json", encoding="utf-8")

    fresh = _bundle(monkeypatch, ("numpy",))
    written, _ = verified_runs.publish_bundle(fresh, output)

    assert written is True
    assert json.loads(output.read_text(encoding="utf-8"))["schema_version"] == SCHEMA_VERSION


def test_write_bundle_round_trips_json(tmp_path):
    bundle = build_verified_run_bundle(
        engines=("goldbach",),
        goldbach_start=4,
        goldbach_end=20,
    )
    output = tmp_path / "verified-runs.json"

    write_bundle(bundle, output)

    loaded = json.loads(output.read_text(encoding="utf-8"))
    assert loaded["schema_version"] == SCHEMA_VERSION
    assert loaded["runs"][0]["engine"] == "GoldbachX"
