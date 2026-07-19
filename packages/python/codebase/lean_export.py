"""Export FalsificationEngine ledger rows as kernel-checkable Lean certificates.

The engines produce a JSONL ledger of scored candidates. This module turns the
rows that admit a finite witness into Lean theorems that the kernel checks
during `lake build`, closing the gap between "the search found this" and "a
proof assistant confirmed the bounded fact."

What a certificate does and does not say
----------------------------------------
Each generated theorem states a bounded, finite fact:

    reachesOneWithin 111 27 = true
    goldbachPair 28 5 23 3 5 = true

The first says 27 reaches 1 within 111 Collatz steps. The second says 28 is an
even number at least 4 with 5 + 23 = 28 and both summands prime, each verified
against a supplied trial-division bound.

Neither states nor implies the Collatz or Goldbach conjecture. A ledger of
500 such certificates is 500 finite checks, not evidence for either conjecture.
See docs/research-standards.md and docs/lean4.md.

Why the bound travels with the certificate
------------------------------------------
Primality is checked by trial division bounded at `b`, where the exporter
guarantees `p <= b * b`. Computing that bound in Lean would need a `sqrt`
soundness argument and a Mathlib dependency; supplying it here costs the kernel
one multiplication instead. The Lean side proves once that a bound plus the
absence of divisors below it implies primality -- see `isPrimeWithBound` and
`isPrime_of_isPrimeWithBound` in ProofX/Certificates.lean.

Why the witness comes from the ledger
-------------------------------------
Goldbach rows carry `details.witness`, the pair the search actually found.
Recomputing it here would produce a certificate attesting to a property of the
integer rather than to what the run discovered, breaking the provenance chain.
Rows without a witness are reported, not silently dropped.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

EXPORTER_VERSION = "proofx.lean_export.v1"
SUPPORTED_LEDGER_SCHEMAS = frozenset({"proofx.ledger.v2"})
CLAIM_LEVEL = "kernel_checked_certificate"

DEFAULT_LEDGER = Path("results/ledger.jsonl")
DEFAULT_OUTPUT = Path("ProofX/Generated/LedgerCertificates.lean")

# Wall-clock fields excluded from the provenance digest. Two runs at the same
# seed agree on every candidate, score, seed, and witness but differ in these,
# so hashing them would change the header on every regeneration and train
# everyone to ignore the drift check.
_VOLATILE_ROW_FIELDS = frozenset({"timestamp"})
_VOLATILE_DETAIL_FIELDS = frozenset({"computation_time_s"})

# Rough kernel cost model, used only for the budget guard. Collatz costs one
# unfolding per step of fuel; each bounded primality check costs one unfolding
# per candidate divisor.
_DEFAULT_MAX_UNFOLDINGS = 2_000_000


class LedgerExportError(ValueError):
    """Raised when a ledger cannot be turned into sound certificates."""


# ── Arithmetic helpers ────────────────────────────────────────────────────────


def is_prime(n: int) -> bool:
    """Deterministic primality by trial division.

    Deliberately not a probabilistic test: a certificate exporter that emitted
    a theorem on the strength of a Miller-Rabin witness would be asserting
    something it had not established.
    """
    if n < 2:
        return False
    if n < 4:
        return True
    if n % 2 == 0:
        return False
    d = 3
    while d * d <= n:
        if n % d == 0:
            return False
        d += 2
    return True


def sqrt_bound(p: int) -> int:
    """Smallest b with `p <= b * b`.

    This is the bound the certificate carries. `isPrimeWithBound` needs both
    `p <= b * b` and no divisor in `[2, min(b, p-1)]`; the `min` is what lets
    p = 2 work, where the naive bound would otherwise treat p as its own
    divisor.
    """
    if p < 0:
        raise LedgerExportError(f"negative value has no square-root bound: {p}")
    b = 0
    while b * b < p:
        b += 1
    return b


def collatz_reaches_one_within(start: int, fuel: int) -> bool:
    """Mirror of `ProofX.reachesOneWithin`, used to verify before emitting.

    Emitting a theorem the kernel then rejects would turn `lake build` into the
    place where exporter bugs surface. Checking here fails earlier and louder.
    """
    n = start
    for _ in range(fuel):
        if n == 1:
            return True
        n = n // 2 if n % 2 == 0 else 3 * n + 1
    return n == 1


# ── Ledger loading and canonical digest ───────────────────────────────────────


def load_ledger(path: Path) -> list[dict[str, Any]]:
    """Read a JSONL ledger, validating its schema version."""
    if not path.exists():
        raise LedgerExportError(f"ledger not found: {path}")
    rows: list[dict[str, Any]] = []
    for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise LedgerExportError(f"{path}:{lineno}: malformed JSON: {exc}") from exc
    if not rows:
        raise LedgerExportError(f"ledger is empty: {path}")

    versions = {row.get("schema_version") for row in rows}
    unsupported = versions - SUPPORTED_LEDGER_SCHEMAS
    if unsupported:
        raise LedgerExportError(
            f"unsupported ledger schema version(s): {sorted(map(str, unsupported))}; "
            f"this exporter reads {sorted(SUPPORTED_LEDGER_SCHEMAS)}"
        )
    return rows


def canonical_digest(rows: list[dict[str, Any]]) -> str:
    """SHA-256 over a canonical projection of the ledger.

    Excludes wall-clock fields so the digest is stable across regenerations of
    the same seeded run. Keys are sorted so dict ordering cannot affect it.
    """
    projected = []
    for row in rows:
        clean = {k: v for k, v in row.items() if k not in _VOLATILE_ROW_FIELDS}
        details = clean.get("details")
        if isinstance(details, dict):
            clean["details"] = {
                k: v for k, v in details.items() if k not in _VOLATILE_DETAIL_FIELDS
            }
        projected.append(clean)
    payload = json.dumps(projected, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


# ── Certificates ──────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class CollatzCertificate:
    candidate: int
    fuel: int

    @property
    def theorem_name(self) -> str:
        return f"collatz_{self.candidate}_reaches_one"

    def render(self) -> str:
        return (
            f"theorem {self.theorem_name} :\n"
            f"    reachesOneWithin {self.fuel} {self.candidate} = true := by\n"
            f"  decide"
        )

    @property
    def unfolding_cost(self) -> int:
        return self.fuel


@dataclass(frozen=True)
class GoldbachCertificate:
    candidate: int
    p: int
    q: int
    bound_p: int
    bound_q: int

    @property
    def theorem_name(self) -> str:
        return f"goldbach_{self.candidate}_has_pair"

    def render(self) -> str:
        return (
            f"theorem {self.theorem_name} :\n"
            f"    goldbachPair {self.candidate} {self.p} {self.q} "
            f"{self.bound_p} {self.bound_q} = true := by\n"
            f"  decide"
        )

    @property
    def unfolding_cost(self) -> int:
        return min(self.bound_p, self.p - 1) + min(self.bound_q, self.q - 1)


Certificate = CollatzCertificate | GoldbachCertificate


def build_certificates(rows: list[dict[str, Any]]) -> tuple[list[Certificate], list[str]]:
    """Turn ledger rows into certificates.

    Returns the certificates and a list of human-readable skip reasons. Rows
    are skipped only for reasons that are reported; nothing is dropped in
    silence.
    """
    certificates: list[Certificate] = []
    skipped: list[str] = []

    for row in rows:
        conjecture = row.get("conjecture")
        candidate = row.get("candidate")
        details = row.get("details") or {}

        if not isinstance(candidate, int):
            skipped.append(f"{conjecture}: non-integer candidate {candidate!r}")
            continue

        if conjecture == "collatz":
            fuel = details.get("stopping_time")
            if not isinstance(fuel, int):
                skipped.append(f"collatz {candidate}: missing integer stopping_time")
                continue
            if not collatz_reaches_one_within(candidate, fuel):
                raise LedgerExportError(
                    f"collatz {candidate}: does not reach 1 within {fuel} steps; "
                    "refusing to emit a theorem the kernel would reject"
                )
            certificates.append(CollatzCertificate(candidate=candidate, fuel=fuel))

        elif conjecture == "goldbach":
            witness = details.get("witness")
            if witness is None:
                skipped.append(
                    f"goldbach {candidate}: no witness recorded "
                    "(pre-v2 row, or the run found no partition)"
                )
                continue
            p, q = witness.get("p"), witness.get("q")
            if not isinstance(p, int) or not isinstance(q, int):
                skipped.append(f"goldbach {candidate}: malformed witness {witness!r}")
                continue
            _validate_goldbach_witness(candidate, p, q)
            certificates.append(
                GoldbachCertificate(
                    candidate=candidate,
                    p=p,
                    q=q,
                    bound_p=sqrt_bound(p),
                    bound_q=sqrt_bound(q),
                )
            )

        else:
            # RiemannX output is a numerical diagnostic and admits no finite
            # witness of this kind. Not an error; just not certifiable.
            skipped.append(f"{conjecture} {candidate}: conjecture has no certificate form")

    _reject_duplicate_names(certificates)
    certificates.sort(key=lambda c: (type(c).__name__, c.candidate))
    return certificates, skipped


def _validate_goldbach_witness(n: int, p: int, q: int) -> None:
    """Reject a witness that would produce a false or unprovable theorem."""
    if n < 4 or n % 2 != 0:
        raise LedgerExportError(f"goldbach {n}: candidate must be even and at least 4")
    if p + q != n:
        raise LedgerExportError(f"goldbach {n}: witness {p} + {q} = {p + q}, expected {n}")
    if p > q:
        raise LedgerExportError(f"goldbach {n}: witness not ordered, {p} > {q}")
    if not is_prime(p):
        raise LedgerExportError(f"goldbach {n}: witness p = {p} is composite")
    if not is_prime(q):
        raise LedgerExportError(f"goldbach {n}: witness q = {q} is composite")


def _reject_duplicate_names(certificates: list[Certificate]) -> None:
    seen: set[str] = set()
    for cert in certificates:
        if cert.theorem_name in seen:
            raise LedgerExportError(f"duplicate theorem name: {cert.theorem_name}")
        seen.add(cert.theorem_name)


# ── Rendering ─────────────────────────────────────────────────────────────────


def render_lean(
    certificates: list[Certificate],
    *,
    digest: str,
    ledger_path: Path,
    row_count: int,
) -> str:
    """Render certificates as a self-describing Lean module.

    Deterministic by construction: the certificate list is pre-sorted and the
    header carries no wall-clock timestamp, so identical input yields
    byte-identical output.
    """
    cost = sum(c.unfolding_cost for c in certificates)
    collatz = [c for c in certificates if isinstance(c, CollatzCertificate)]
    goldbach = [c for c in certificates if isinstance(c, GoldbachCertificate)]

    lines: list[str] = [
        "/-",
        "  GENERATED FILE -- DO NOT EDIT BY HAND.",
        "",
        "  Regenerate with:",
        "    python -m codebase.cli export lean",
        "",
        "  Verify it still matches the ledger with:",
        "    python -m codebase.cli export lean --check",
        "",
        "  Provenance",
        f"    exporter_version : {EXPORTER_VERSION}",
        f"    ledger_path      : {ledger_path.as_posix()}",
        f"    ledger_digest    : sha256:{digest}",
        f"    ledger_rows      : {row_count}",
        f"    certificates     : {len(certificates)} "
        f"({len(collatz)} collatz, {len(goldbach)} goldbach)",
        f"    claim_level      : {CLAIM_LEVEL}",
        f"    est_unfoldings   : {cost}",
        "",
        "  The digest covers a canonical projection of the ledger that excludes",
        "  wall-clock fields, so it is stable across regenerations of the same",
        "  seeded run.",
        "",
        "  Each theorem below is a bounded, finite fact checked by the Lean",
        "  kernel. None of them states or implies the Collatz or Goldbach",
        "  conjecture, and a passing build is not evidence for either. See",
        "  docs/research-standards.md and docs/lean4.md.",
        "-/",
        "import ProofX.Certificates",
        "",
        "namespace ProofX.Generated",
        "",
    ]

    if collatz:
        lines += [
            "/-! ### Collatz",
            "",
            "Each theorem states that the candidate reaches 1 within the exact",
            "number of steps the search recorded. -/",
            "",
        ]
        lines += [c.render() + "\n" for c in collatz]

    if goldbach:
        lines += [
            "/-! ### Goldbach",
            "",
            "Each theorem states that the recorded prime pair sums to the",
            "candidate, with both summands verified prime against the bound",
            "carried in the certificate. -/",
            "",
        ]
        lines += [c.render() + "\n" for c in goldbach]

    lines.append("end ProofX.Generated")
    return "\n".join(lines) + "\n"


# ── Top-level operations ──────────────────────────────────────────────────────


def build_lean_source(
    ledger_path: Path = DEFAULT_LEDGER,
    *,
    max_unfoldings: int = _DEFAULT_MAX_UNFOLDINGS,
) -> tuple[str, list[str]]:
    """Load a ledger and render the Lean module. Returns (source, skip reasons)."""
    rows = load_ledger(ledger_path)
    certificates, skipped = build_certificates(rows)
    if not certificates:
        raise LedgerExportError(f"no certifiable rows in {ledger_path}")

    cost = sum(c.unfolding_cost for c in certificates)
    if cost > max_unfoldings:
        raise LedgerExportError(
            f"estimated kernel cost {cost} exceeds budget {max_unfoldings}. "
            "A ledger this expensive would hang the Lean build rather than fail "
            "it. Raise --max-unfoldings deliberately, or narrow the ledger."
        )

    source = render_lean(
        certificates,
        digest=canonical_digest(rows),
        ledger_path=ledger_path,
        row_count=len(rows),
    )
    return source, skipped


def export_lean(
    ledger_path: Path = DEFAULT_LEDGER,
    output_path: Path = DEFAULT_OUTPUT,
    *,
    max_unfoldings: int = _DEFAULT_MAX_UNFOLDINGS,
) -> list[str]:
    """Write the generated Lean module. Returns skip reasons."""
    source, skipped = build_lean_source(ledger_path, max_unfoldings=max_unfoldings)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(source, encoding="utf-8")
    return skipped


def check_lean(
    ledger_path: Path = DEFAULT_LEDGER,
    output_path: Path = DEFAULT_OUTPUT,
    *,
    max_unfoldings: int = _DEFAULT_MAX_UNFOLDINGS,
) -> bool:
    """True iff the file on disk matches what the ledger would produce now."""
    source, _ = build_lean_source(ledger_path, max_unfoldings=max_unfoldings)
    if not output_path.exists():
        return False
    return output_path.read_text(encoding="utf-8") == source
