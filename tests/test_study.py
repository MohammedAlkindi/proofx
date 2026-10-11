"""Policy controls, replay, and semantic tampering of study artifacts."""

import json

import pytest
from codebase import study


@pytest.fixture
def small_study(monkeypatch, tmp_path):
    config = json.loads(study.protocol_text())
    config["intervals"] = [[10002, 12000]]
    config["replicates"] = 2
    monkeypatch.setattr(study, "protocol_text", lambda: study.encode(config))
    monkeypatch.setattr(study, "INTERVALS", ((10002, 12000),))
    monkeypatch.setattr(study, "REPLICATES", 2)
    output = tmp_path / "study"
    study.run(output)
    return output


def test_prime_algorithms_agree():
    assert study.prime_set(300) == study.prime_set(300, independent=True)


def test_family_precedence_and_ablation():
    primes = study.prime_set(100)
    domain = [8, 10, 14, 20, 30, 32]
    assert study.buckets(domain, "priority", primes) == [[8, 32], [10, 14], [], [20], [30]]
    assert study.buckets(domain, "without_power_two", primes) == [[], [10, 14], [32], [8, 20], [30]]
    assert study.buckets(domain, "uniform", primes) == [domain]
    assert study.buckets(domain, "ascending", primes) == [[n] for n in domain]
    with pytest.raises(ValueError):
        study.buckets(domain, "invented", primes)


def test_ranking_replays_and_has_exact_domain():
    domain = list(range(10002, 10202, 2))
    groups = study.buckets(domain, "priority", study.prime_set(10200))
    first = study.ranking(groups, domain, 0, 10002, 12000)
    assert first == study.ranking(groups, domain, 0, 10002, 12000)
    assert sorted(first) == domain
    assert first != study.ranking(groups, domain, 1, 10002, 12000)
    assert all(n in groups[0] for n in first[: len(groups[0])])


def test_complete_replay_and_no_overwrite(small_study):
    assert study.verify(small_study)["policy_replicates"] == 14
    with pytest.raises(FileExistsError):
        study.run(small_study)


def test_independent_checker_detects_shared_moment_bug(small_study):
    from codebase.study_check import check_arithmetic

    path = small_study / "analysis.json"
    data = json.loads(path.read_text())
    data["policies"][0]["recall_variance"]["numerator"] += 1
    path.write_text(study.encode(data))
    with pytest.raises(ValueError, match="inclusion-indicator"):
        check_arithmetic(small_study)


@pytest.mark.parametrize(
    "name", ["protocol.json", "reference.json", "selections.jsonl", "analysis.json"]
)
def test_rehashed_semantic_corruption_rejected(small_study, name):
    path = small_study / name
    if name == "selections.jsonl":
        lines = path.read_text().splitlines()
        row = json.loads(lines[0])
        row["strata"][0][0] = row["strata"][0][1]
        lines[0] = study.encode(row).strip()
        path.write_text("\n".join(lines) + "\n")
    else:
        data = json.loads(path.read_text())
        if name == "reference.json":
            data[0]["count"] += 1
        elif name == "analysis.json":
            data["policies"][0]["expected_recall"]["numerator"] += 1
        else:
            data["replicates"] = 1
        path.write_text(study.encode(data))
    manifest_path = small_study / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["artifacts"][name] = study.digest(path)
    manifest_path.write_text(study.encode(manifest))
    with pytest.raises(ValueError):
        study.verify(small_study)


def test_missing_replicate_rejected(small_study):
    path = small_study / "selections.jsonl"
    path.write_text("\n".join(path.read_text().splitlines()[:-1]) + "\n")
    manifest_path = small_study / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["artifacts"][path.name] = study.digest(path)
    manifest_path.write_text(study.encode(manifest))
    with pytest.raises(ValueError):
        study.verify(small_study)


@pytest.mark.parametrize("mode", ["duplicate", "quota", "boolean"])
def test_rehashed_selection_structure_rejected(small_study, mode):
    path = small_study / "selections.jsonl"
    lines = path.read_text().splitlines()
    row = json.loads(lines[0])
    if mode == "duplicate":
        lines[1] = lines[0]
    elif mode == "quota":
        row["strata"][0].pop()
        lines[0] = study.encode(row).strip()
    else:
        row["seed"] = False
        lines[0] = study.encode(row).strip()
    path.write_text("\n".join(lines) + "\n")
    manifest_path = small_study / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["artifacts"][path.name] = study.digest(path)
    manifest_path.write_text(study.encode(manifest))
    with pytest.raises(ValueError):
        study.verify(small_study)
