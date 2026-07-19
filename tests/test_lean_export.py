"""Tests for the ledger-to-Lean certificate exporter."""

import json
import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parents[1] / "packages" / "python"))

from codebase.lean_export import (
    CLAIM_LEVEL,
    CollatzCertificate,
    GoldbachCertificate,
    LedgerExportError,
    build_certificates,
    build_lean_source,
    canonical_digest,
    check_lean,
    collatz_reaches_one_within,
    export_lean,
    is_prime,
    load_ledger,
    sqrt_bound,
)

# ── Fixtures ──────────────────────────────────────────────────────────────────

SCHEMA = "proofx.ledger.v2"


def _collatz_row(candidate: int, stopping_time: int, **details: object) -> dict:
    return {
        "candidate": candidate,
        "conjecture": "collatz",
        "strategy": "test",
        "features": {},
        "near_miss_score": 0.5,
        "details": {
            "stopping_time": stopping_time,
            "computation_time_s": 1.23e-05,
            **details,
        },
        "timestamp": 1783876609.19,
        "rng_seed": 7,
        "schema_version": SCHEMA,
    }


def _goldbach_row(candidate: int, p: int | None, q: int | None) -> dict:
    witness = None if p is None or q is None else {"p": p, "q": q}
    return {
        "candidate": candidate,
        "conjecture": "goldbach",
        "strategy": "test",
        "features": {},
        "near_miss_score": 0.5,
        "details": {
            "actual_partitions": 1,
            "computation_time_s": 4.56e-05,
            "witness": witness,
        },
        "timestamp": 1783876609.19,
        "rng_seed": 7,
        "schema_version": SCHEMA,
    }


def _write_ledger(path: Path, rows: list[dict]) -> Path:
    path.write_text("\n".join(json.dumps(r) for r in rows), encoding="utf-8")
    return path


@pytest.fixture
def fixture_ledger(tmp_path: Path) -> Path:
    return _write_ledger(
        tmp_path / "ledger.jsonl",
        [
            _collatz_row(27, 111),
            _collatz_row(1, 0),
            _goldbach_row(28, 5, 23),
            _goldbach_row(100, 3, 97),
            _goldbach_row(4, 2, 2),
        ],
    )


# ── Arithmetic helpers ────────────────────────────────────────────────────────


class TestArithmeticHelpers:
    def test_is_prime_small(self):
        primes = {2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37}
        for n in range(-5, 40):
            assert is_prime(n) is (n in primes), n

    def test_is_prime_larger(self):
        assert is_prime(99991)
        assert not is_prime(99992)
        assert not is_prime(9409)  # 97^2

    def test_sqrt_bound_is_smallest_b_with_p_le_b_squared(self):
        for p in range(0, 200):
            b = sqrt_bound(p)
            assert p <= b * b
            assert b == 0 or (b - 1) * (b - 1) < p

    def test_sqrt_bound_handles_two(self):
        # p = 2 is the degenerate case: the bound equals p, so the Lean side
        # relies on min(b, p-1) to avoid treating 2 as its own divisor.
        assert sqrt_bound(2) == 2

    def test_sqrt_bound_rejects_negative(self):
        with pytest.raises(LedgerExportError):
            sqrt_bound(-1)

    def test_collatz_mirror_matches_known_values(self):
        assert collatz_reaches_one_within(1, 0)
        assert collatz_reaches_one_within(27, 111)
        assert not collatz_reaches_one_within(27, 110)


# ── Loading and schema ────────────────────────────────────────────────────────


class TestLoadLedger:
    def test_missing_file(self, tmp_path: Path):
        with pytest.raises(LedgerExportError, match="not found"):
            load_ledger(tmp_path / "nope.jsonl")

    def test_empty_file(self, tmp_path: Path):
        path = tmp_path / "empty.jsonl"
        path.write_text("", encoding="utf-8")
        with pytest.raises(LedgerExportError, match="empty"):
            load_ledger(path)

    def test_malformed_json_reports_line_number(self, tmp_path: Path):
        path = tmp_path / "bad.jsonl"
        path.write_text('{"a": 1}\nnot json\n', encoding="utf-8")
        with pytest.raises(LedgerExportError, match=":2:"):
            load_ledger(path)

    def test_unsupported_schema_version_rejected(self, tmp_path: Path):
        row = _collatz_row(27, 111)
        row["schema_version"] = "proofx.ledger.v1"
        path = _write_ledger(tmp_path / "old.jsonl", [row])
        with pytest.raises(LedgerExportError, match="unsupported ledger schema"):
            load_ledger(path)

    def test_missing_schema_version_rejected(self, tmp_path: Path):
        row = _collatz_row(27, 111)
        del row["schema_version"]
        path = _write_ledger(tmp_path / "none.jsonl", [row])
        with pytest.raises(LedgerExportError, match="unsupported ledger schema"):
            load_ledger(path)


# ── Digest ────────────────────────────────────────────────────────────────────


class TestCanonicalDigest:
    def test_ignores_wall_clock_fields(self):
        a = _collatz_row(27, 111)
        b = _collatz_row(27, 111)
        b["timestamp"] = 999999.0
        b["details"]["computation_time_s"] = 9.99
        assert canonical_digest([a]) == canonical_digest([b])

    def test_detects_semantic_change(self):
        a = _collatz_row(27, 111)
        b = _collatz_row(27, 112)
        assert canonical_digest([a]) != canonical_digest([b])

    def test_detects_added_row(self):
        a = [_collatz_row(27, 111)]
        b = [_collatz_row(27, 111), _collatz_row(1, 0)]
        assert canonical_digest(a) != canonical_digest(b)

    def test_insensitive_to_key_order(self):
        a = _collatz_row(27, 111)
        b = dict(reversed(list(a.items())))
        assert canonical_digest([a]) == canonical_digest([b])


# ── Certificate construction ──────────────────────────────────────────────────


class TestBuildCertificates:
    def test_builds_both_kinds(self, fixture_ledger: Path):
        certs, skipped = build_certificates(load_ledger(fixture_ledger))
        assert len(certs) == 5
        assert skipped == []
        assert sum(isinstance(c, CollatzCertificate) for c in certs) == 2
        assert sum(isinstance(c, GoldbachCertificate) for c in certs) == 3

    def test_sorted_deterministically(self, fixture_ledger: Path):
        certs, _ = build_certificates(load_ledger(fixture_ledger))
        keys = [(type(c).__name__, c.candidate) for c in certs]
        assert keys == sorted(keys)

    def test_missing_witness_is_reported_not_silently_dropped(self, tmp_path: Path):
        path = _write_ledger(tmp_path / "l.jsonl", [_goldbach_row(28, None, None)])
        certs, skipped = build_certificates(load_ledger(path))
        assert certs == []
        assert len(skipped) == 1
        assert "no witness recorded" in skipped[0]

    def test_riemann_rows_reported_as_uncertifiable(self, tmp_path: Path):
        row = _collatz_row(27, 111)
        row["conjecture"] = "riemann"
        path = _write_ledger(tmp_path / "l.jsonl", [row])
        certs, skipped = build_certificates(load_ledger(path))
        assert certs == []
        assert "no certificate form" in skipped[0]

    def test_missing_stopping_time_reported(self, tmp_path: Path):
        row = _collatz_row(27, 111)
        del row["details"]["stopping_time"]
        path = _write_ledger(tmp_path / "l.jsonl", [row])
        certs, skipped = build_certificates(load_ledger(path))
        assert certs == []
        assert "stopping_time" in skipped[0]

    def test_false_collatz_claim_is_an_error_not_a_skip(self, tmp_path: Path):
        # A theorem the kernel would reject must fail here, loudly, rather than
        # surface later as a mysterious build failure.
        path = _write_ledger(tmp_path / "l.jsonl", [_collatz_row(27, 50)])
        with pytest.raises(LedgerExportError, match="does not reach 1"):
            build_certificates(load_ledger(path))


class TestWitnessValidation:
    @pytest.mark.parametrize(
        ("n", "p", "q", "match"),
        [
            (28, 5, 7, "expected 28"),  # 5 + 7 = 12, not 28
            (28, 4, 24, "p = 4 is composite"),  # sums, but 4 is composite
            (30, 9, 21, "p = 9 is composite"),  # sums, but 9 and 21 are composite
            (28, 23, 5, "not ordered"),  # p > q
            (27, 4, 23, "even and at least 4"),  # odd candidate
            (2, 1, 1, "even and at least 4"),  # below 4
        ],
    )
    def test_rejects_bad_witness(self, tmp_path: Path, n, p, q, match):
        path = _write_ledger(tmp_path / "l.jsonl", [_goldbach_row(n, p, q)])
        with pytest.raises(LedgerExportError, match=match):
            build_certificates(load_ledger(path))

    def test_rejects_composite_p(self, tmp_path: Path):
        # 9 + 19 = 28 sums correctly and is ordered, but 9 is composite.
        path = _write_ledger(tmp_path / "l.jsonl", [_goldbach_row(28, 9, 19)])
        with pytest.raises(LedgerExportError, match="p = 9 is composite"):
            build_certificates(load_ledger(path))

    def test_rejects_composite_q(self, tmp_path: Path):
        # 5 + 25 = 30 sums correctly and is ordered, but 25 is composite.
        path = _write_ledger(tmp_path / "l.jsonl", [_goldbach_row(30, 5, 25)])
        with pytest.raises(LedgerExportError, match="q = 25 is composite"):
            build_certificates(load_ledger(path))

    def test_bounds_satisfy_the_lean_side_condition(self, fixture_ledger: Path):
        certs, _ = build_certificates(load_ledger(fixture_ledger))
        for cert in certs:
            if isinstance(cert, GoldbachCertificate):
                assert cert.p <= cert.bound_p * cert.bound_p
                assert cert.q <= cert.bound_q * cert.bound_q


# ── Rendering ─────────────────────────────────────────────────────────────────


class TestRendering:
    def test_deterministic_across_runs(self, fixture_ledger: Path):
        first, _ = build_lean_source(fixture_ledger)
        second, _ = build_lean_source(fixture_ledger)
        assert first == second

    def test_no_wall_clock_in_output(self, fixture_ledger: Path):
        source, _ = build_lean_source(fixture_ledger)
        assert "1783876609" not in source
        for token in ("generated_at", "timestamp", "Generated on"):
            assert token not in source

    def test_header_carries_provenance(self, fixture_ledger: Path):
        source, _ = build_lean_source(fixture_ledger)
        assert "ledger_digest    : sha256:" in source
        assert f"claim_level      : {CLAIM_LEVEL}" in source
        assert "ledger_rows      : 5" in source

    def test_disclaims_the_open_conjectures(self, fixture_ledger: Path):
        source, _ = build_lean_source(fixture_ledger)
        assert "None of them states or implies the Collatz or Goldbach" in source

    def test_every_certificate_is_a_named_theorem(self, fixture_ledger: Path):
        source, _ = build_lean_source(fixture_ledger)
        # Count declarations at line start; the header prose says "theorem" too.
        declarations = [ln for ln in source.splitlines() if ln.startswith("theorem ")]
        assert len(declarations) == 5
        # Anonymous examples cannot be reached by #print axioms, so the audit
        # in ProofX/Audit.lean would pass over them.
        assert not any(ln.startswith("example ") for ln in source.splitlines())

    def test_uses_kernel_decide_not_native_decide(self, fixture_ledger: Path):
        source, _ = build_lean_source(fixture_ledger)
        assert "native_decide" not in source
        assert source.count(":= by\n  decide") == 5

    def test_golden_output(self, fixture_ledger: Path):
        source, _ = build_lean_source(fixture_ledger)
        assert "theorem collatz_27_reaches_one :\n    reachesOneWithin 111 27 = true" in source
        assert "theorem collatz_1_reaches_one :\n    reachesOneWithin 0 1 = true" in source
        # 5 <= 3*3 and 23 <= 5*5
        assert "theorem goldbach_28_has_pair :\n    goldbachPair 28 5 23 3 5 = true" in source
        # p = 2 takes bound 2; min(2, p-1) = 1 keeps 2 from dividing itself
        assert "theorem goldbach_4_has_pair :\n    goldbachPair 4 2 2 2 2 = true" in source
        assert source.startswith("/-\n  GENERATED FILE")
        assert source.endswith("end ProofX.Generated\n")

    def test_imports_and_namespace(self, fixture_ledger: Path):
        source, _ = build_lean_source(fixture_ledger)
        assert "import ProofX.Certificates" in source
        assert "namespace ProofX.Generated" in source


# ── Budget guard ──────────────────────────────────────────────────────────────


class TestBudgetGuard:
    def test_rejects_ledger_over_budget(self, fixture_ledger: Path):
        with pytest.raises(LedgerExportError, match="exceeds budget"):
            build_lean_source(fixture_ledger, max_unfoldings=10)

    def test_passes_under_budget(self, fixture_ledger: Path):
        source, _ = build_lean_source(fixture_ledger, max_unfoldings=10_000)
        assert source


# ── Export and drift check ────────────────────────────────────────────────────


class TestExportAndCheck:
    def test_export_then_check_passes(self, fixture_ledger: Path, tmp_path: Path):
        out = tmp_path / "Generated.lean"
        export_lean(fixture_ledger, out)
        assert check_lean(fixture_ledger, out) is True

    def test_export_is_byte_identical_when_rerun(self, fixture_ledger: Path, tmp_path: Path):
        out = tmp_path / "Generated.lean"
        export_lean(fixture_ledger, out)
        first = out.read_bytes()
        export_lean(fixture_ledger, out)
        assert out.read_bytes() == first

    def test_check_fails_when_output_missing(self, fixture_ledger: Path, tmp_path: Path):
        assert check_lean(fixture_ledger, tmp_path / "absent.lean") is False

    def test_check_detects_mutated_output(self, fixture_ledger: Path, tmp_path: Path):
        out = tmp_path / "Generated.lean"
        export_lean(fixture_ledger, out)
        out.write_text(out.read_text(encoding="utf-8") + "\n-- tampered\n", encoding="utf-8")
        assert check_lean(fixture_ledger, out) is False

    def test_check_detects_altered_ledger_row(self, fixture_ledger: Path, tmp_path: Path):
        out = tmp_path / "Generated.lean"
        export_lean(fixture_ledger, out)
        rows = [json.loads(x) for x in fixture_ledger.read_text(encoding="utf-8").splitlines()]
        rows[0]["details"]["stopping_time"] = 112
        _write_ledger(fixture_ledger, rows)
        assert check_lean(fixture_ledger, out) is False

    def test_check_detects_removed_ledger_row(self, fixture_ledger: Path, tmp_path: Path):
        out = tmp_path / "Generated.lean"
        export_lean(fixture_ledger, out)
        rows = [json.loads(x) for x in fixture_ledger.read_text(encoding="utf-8").splitlines()]
        _write_ledger(fixture_ledger, rows[:-1])
        assert check_lean(fixture_ledger, out) is False

    def test_check_detects_added_ledger_row(self, fixture_ledger: Path, tmp_path: Path):
        out = tmp_path / "Generated.lean"
        export_lean(fixture_ledger, out)
        rows = [json.loads(x) for x in fixture_ledger.read_text(encoding="utf-8").splitlines()]
        rows.append(_goldbach_row(10, 3, 7))
        _write_ledger(fixture_ledger, rows)
        assert check_lean(fixture_ledger, out) is False

    def test_check_survives_wall_clock_only_change(self, fixture_ledger: Path, tmp_path: Path):
        # Regenerating the ledger at the same seed changes only wall-clock
        # fields. That must not be reported as drift, or the gate becomes noise.
        out = tmp_path / "Generated.lean"
        export_lean(fixture_ledger, out)
        rows = [json.loads(x) for x in fixture_ledger.read_text(encoding="utf-8").splitlines()]
        for row in rows:
            row["timestamp"] += 1000.0
            row["details"]["computation_time_s"] *= 2
        _write_ledger(fixture_ledger, rows)
        assert check_lean(fixture_ledger, out) is True

    def test_export_creates_parent_directory(self, fixture_ledger: Path, tmp_path: Path):
        out = tmp_path / "nested" / "deeper" / "Generated.lean"
        export_lean(fixture_ledger, out)
        assert out.exists()

    def test_export_reports_skips(self, tmp_path: Path):
        path = _write_ledger(
            tmp_path / "l.jsonl",
            [_collatz_row(27, 111), _goldbach_row(28, None, None)],
        )
        skipped = export_lean(path, tmp_path / "out.lean")
        assert len(skipped) == 1

    def test_no_certifiable_rows_is_an_error(self, tmp_path: Path):
        path = _write_ledger(tmp_path / "l.jsonl", [_goldbach_row(28, None, None)])
        with pytest.raises(LedgerExportError, match="no certifiable rows"):
            build_lean_source(path)


# ── Against the real ledger ───────────────────────────────────────────────────


class TestRealLedger:
    """Exercised only when a local ledger exists; results/ is gitignored."""

    @pytest.fixture
    def real_ledger(self) -> Path:
        path = Path(__file__).parents[1] / "results" / "ledger.jsonl"
        if not path.exists():
            pytest.skip("results/ledger.jsonl not present (gitignored)")
        return path

    def test_exports_cleanly(self, real_ledger: Path, tmp_path: Path):
        source, skipped = build_lean_source(real_ledger)
        assert skipped == []
        declarations = [ln for ln in source.splitlines() if ln.startswith("theorem ")]
        assert len(declarations) == 500

    def test_kernel_cost_within_budget(self, real_ledger: Path):
        certs, _ = build_certificates(load_ledger(real_ledger))
        cost = sum(c.unfolding_cost for c in certs)
        # Spec estimated ~270k unfoldings for the full ledger.
        assert cost < 1_000_000, f"kernel cost {cost} higher than the design assumed"


class TestEmittedClaimsAreTrue:
    """Parse the rendered Lean back and re-derive every claim independently.

    The exporter validates its own inputs, but this checks the text it actually
    emitted. A rendering bug -- a transposed argument, a wrong bound -- would
    otherwise surface only as a failing `lake build`, far from its cause.
    """

    COLLATZ_RE = re.compile(
        r"theorem collatz_(\d+)_reaches_one :\s*\n\s*reachesOneWithin (\d+) (\d+) = true"
    )
    GOLDBACH_RE = re.compile(
        r"theorem goldbach_(\d+)_has_pair :\s*\n\s*goldbachPair (\d+) (\d+) (\d+) (\d+) (\d+) = true"
    )

    def test_collatz_claims_hold(self, fixture_ledger: Path):
        source, _ = build_lean_source(fixture_ledger)
        matches = self.COLLATZ_RE.findall(source)
        assert len(matches) == 2
        for name, fuel, start in matches:
            assert int(name) == int(start), "theorem name must identify its candidate"
            assert collatz_reaches_one_within(int(start), int(fuel))

    def test_goldbach_claims_hold(self, fixture_ledger: Path):
        source, _ = build_lean_source(fixture_ledger)
        matches = self.GOLDBACH_RE.findall(source)
        assert len(matches) == 3
        for name, n, p, q, bp, bq in matches:
            n, p, q, bp, bq = (int(x) for x in (n, p, q, bp, bq))
            assert int(name) == n
            assert n >= 4 and n % 2 == 0
            assert p + q == n
            assert p <= q
            assert is_prime(p) and is_prime(q)
            # The side condition isPrime_of_isPrimeWithBound requires.
            assert p <= bp * bp
            assert q <= bq * bq

    def test_no_divisor_in_the_range_decide_will_search(self, fixture_ledger: Path):
        # Mirrors `hasDivisorUpTo p (min b (p - 1))` on the Lean side. If this
        # found a divisor, `decide` would evaluate to false and the kernel
        # would reject the theorem.
        source, _ = build_lean_source(fixture_ledger)
        for _, _, p, q, bp, bq in self.GOLDBACH_RE.findall(source):
            for value, bound in ((int(p), int(bp)), (int(q), int(bq))):
                limit = min(bound, value - 1)
                assert not any(value % d == 0 for d in range(2, limit + 1))
