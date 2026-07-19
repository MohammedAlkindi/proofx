# Kernel-Checked Ledger Certificate Exporter

Date: 2026-07-19
Status: Design, pending implementation plan

## Problem

ProofX is currently two disconnected halves.

`results/ledger.jsonl` holds 499 scored candidates produced by
`FalsificationEngine`. `ProofX/Certificates.lean` holds four hand-written
`example`s. Nothing connects them. The project's central claim — that directed
search produces candidates which become machine-checkable artifacts — is
unimplemented at exactly the joint where it would be interesting.

This gap is already tracked in two places: the "Known gaps" section of
`CLAUDE.md`, and row 2 of the status table in `docs/mvp.md`.

A second problem surfaced while designing the exporter, and it must be fixed
first.

### The trust boundary is wider than the docs claim

All four certificate examples close with `native_decide`:

```lean
example : reachesOneWithin 111 27 = true := by
  native_decide
```

`native_decide` does not kernel-check. It compiles the proposition to native
code, evaluates it, and trusts the result via the `Lean.ofReduceBool` axiom
together with `trustCompiler`. This widens the trusted computing base to the
Lean compiler and runtime.

That collides with the repository's own rules:

- `CLAUDE.md` describes the root package as one that "kernel-checks bounded,
  finite certificates." It currently does not.
- `docs/lean4.md` line 64 bars any accepted proof containing "an unsound
  `axiom`." `native_decide` introduces two axioms without the token `axiom`
  appearing in the source, so the audit command at `docs/lean4.md` line 83
  passes over it silently.

For a project whose credibility rests on claim discipline, "Lean checked this"
meaning "the Lean compiler evaluated this" is a self-inflicted wound.

### `native_decide` is also masking an algorithmic flaw

`isPrimeNat` performs trial division through `hasDivisorUpTo p (p - 1)`. That
is structural recursion: one kernel unfolding per step. Lean's kernel
GMP-accelerates the individual `%` operations but not the recursion itself.

The hand-written examples use primes 23 and 97, compiled to native code, so the
cost is invisible. Real ledger data is not so kind:

| Conjecture | Rows | Max candidate | Kernel cost driver |
| --- | --- | --- | --- |
| Collatz | 250 | 549,746,376,656 | max stopping time 444 — tractable |
| Goldbach | 250 | 99,992 | primes to ~50,000 — ~10^7 unfoldings total |

Collatz is fine. Values reach 1.9x10^13, but GMP-backed `Nat` arithmetic makes
magnitude nearly free; only the ~444 unfoldings of `reachesOneWithin` cost
anything.

Goldbach is not fine. Switching to kernel `decide` without changing
`isPrimeNat` will crawl or fail outright. The trust shortcut concealed a design
flaw in the definitions, which is an independent argument for fixing the trust
boundary before building anything on top of it.

## Goals

1. Every accepted Lean artifact in the root package is kernel-checked, with
   that property enforced by CI rather than by convention.
2. A deterministic exporter turns `results/ledger.jsonl` rows into
   kernel-checkable Lean certificates.
3. Goldbach certificates attest to what a specific run actually found, not
   merely to a true fact about an integer.
4. Drift between the ledger and the committed certificates fails CI loudly.

## Non-goals

- Proving Collatz, Goldbach, or the Riemann Hypothesis. Claim discipline in
  `docs/research-standards.md` and `docs/lean4.md` applies unchanged.
- Certificates for RiemannX. Its output is a numerical diagnostic
  (`claim_level: "numerical_diagnostic"`) and admits no finite witness of this
  kind.
- Touching `packages/germinal/`.
- Paying down the coverage/mypy/ruff exclusion debt. Separate concern.

## Design

Five phases, ordered by dependency.

### Phase 1 — Close the trust boundary

Scope: `ProofX/Certificates.lean`, `docs/lean4.md`, `CLAUDE.md`,
`.github/workflows/lean.yml`.

- Convert the four `example`s to named theorems. `#print axioms` cannot be
  applied to an anonymous `example`, so naming them is a prerequisite for
  auditing them.
- Replace `native_decide` with `decide`.
- Add an axiom audit to CI. A `by decide` proof reduces to
  `of_decide_eq_true (Eq.refl true)` and should depend on no axioms at all.
  Once Mathlib arrives in Phase 2, proofs may legitimately depend on
  `propext`, `Classical.choice`, and `Quot.sound`.

  Audit rule: allow exactly those three. Fail on `Lean.ofReduceBool`,
  `Lean.trustCompiler`, or `sorryAx`.
- Update the `rg` check in `docs/lean4.md` to include `native_decide`, and add
  it by name to the hard rules in `CLAUDE.md`.

The audit is the durable artifact here. The four current examples are easy to
fix by hand; the point is that the next hundred generated ones cannot regress.

### Phase 2 — Make primality kernel-tractable

Scope: `lakefile.lean`, `lake-manifest.json`, `ProofX/Certificates.lean`.

- Add Mathlib as a Lake dependency and commit the resulting manifest in the
  same change, as `docs/lean4.md` requires.
- Bound trial division at `sqrt p`, reducing ~50,000 unfoldings per prime to
  ~316.
- Prefer Mathlib's `Nat.Prime` and its kernel-friendly decidability instance
  over a hand-rolled predicate.

`docs/lean4.md` line 70 says to add Mathlib only when a specific theorem needs
it. This is that theorem: proving that no divisor at or below `sqrt p` implies
primality is real work, and reimplementing it locally would be worse than
depending on the library that already has it.

**Open risk.** Mathlib has more than one decidability instance for
`Nat.Prime`, and they differ sharply in kernel reduction behavior. Which one is
kernel-tractable at this scale must be measured on real ledger data during
implementation, not assumed from the names. This is the single largest
technical unknown in the design, and the implementation plan should front-load
a spike that benchmarks it before the exporter is written.

### Phase 3 — Record the Goldbach witness

Scope: `packages/python/codebase/FalsificationEngine/`, `results/ledger.jsonl`,
`src/results.json`.

`GoldbachCertificate` requires the explicit prime pair `(p, q)`. Ledger rows
record `actual_partitions` — the count — and discard the pair the run found.

Add a `witness` object (`{"p": ..., "q": ...}`) to Goldbach ledger rows at
search time, and bump the ledger schema version.

The alternative, recomputing the pair inside the exporter, was rejected: the
resulting certificate would attest to a property of the integer rather than to
what the run discovered, which quietly breaks the provenance chain the whole
project exists to demonstrate.

Regenerate `results/ledger.jsonl` and `src/results.json` from the same
`--seed 42 --budget 500` invocation so the committed data matches the schema.

Site impact is small. `src/pages/ledger-viewer/` reads `/results.json` and
user-uploaded files, never `results/ledger.jsonl` directly, and the change is
purely additive.

### Phase 4 — The exporter

Scope: new `packages/python/codebase/lean_export.py`, `cli.py`, new
`ProofX/Generated/LedgerCertificates.lean`, `ProofX.lean`.

Follows the existing `verified_runs.py` pattern rather than inventing a
parallel vocabulary: `SCHEMA_VERSION`, `claim_level`, `bounds`, `reproduce`,
and a validator.

CLI, matching the existing `run` subcommand shape:

```bash
python -m codebase.cli export lean \
  --ledger results/ledger.jsonl \
  --out ProofX/Generated/LedgerCertificates.lean
python -m codebase.cli export lean --check
```

Output requirements:

- **Deterministic.** Rows sorted by `(conjecture, candidate)`; stable
  formatting; byte-identical across runs on identical input.
- **No wall-clock timestamps in the generated file.** A timestamp would make
  `--check` fail on every run, which would train everyone to ignore it.
- **Provenance header** recording ledger path, SHA-256 of ledger contents,
  ledger schema version, exporter version, and row count.
- **One named theorem per row**, so every generated proof is reachable by the
  Phase 1 axiom audit.

Adds `kernel_checked_certificate` to the `claim_level` vocabulary. This is a
genuinely stronger level than the existing `bounded_run` and
`numerical_diagnostic`, and public copy must still name the finite scope of
each certificate per `docs/lean4.md`.

`ProofX.lean` imports the generated module so `lake build` covers it.

### Phase 5 — CI enforcement

Scope: `.github/workflows/lean.yml`, `.github/workflows/ci.yml`.

Four gates:

1. `lake build` — the committed certificates kernel-check.
2. `export lean --check` — the committed certificates still match the ledger.
3. Axiom audit — no proof depends on a disallowed axiom.
4. Build budget guard — a future ledger that blows up kernel cost fails loudly
   instead of hanging CI.

`lean.yml` currently runs bare `leanprover/lean-action@v1`. It needs Mathlib
cache retrieval, or CI will rebuild Mathlib from source and the job will take
hours.

Estimated kernel cost across the full ledger is ~270k unfoldings
(250 x 444 for Collatz, 250 x 316 x 2 for Goldbach), which should complete in
well under a minute once Mathlib is cached. Mathlib cache download, not
certificate checking, will dominate the job.

## Testing

Python, under `tests/test_falsification_engine/` and a new
`tests/test_lean_export.py`:

- Determinism: identical input yields byte-identical output across runs.
- `--check` detects a mutated generated file.
- `--check` detects a ledger row added, removed, or altered.
- Witness validation rejects a row whose `p + q` does not equal its candidate,
  or whose `p`/`q` is composite.
- Golden-file test against a small fixture ledger.
- Rows lacking a witness field are handled explicitly, not silently skipped.

New code ships with tests per the 60% coverage gate in `pyproject.toml`.

Lean side: `lake build` is the test. The axiom audit is the regression guard.

## Risks

| Risk | Mitigation |
| --- | --- |
| Mathlib decidability instance not kernel-tractable at scale | Benchmark spike before writing the exporter; Phase 2 blocks Phase 4 |
| Mathlib inflates Lean CI time | Cache retrieval in `lean.yml`; measure before and after |
| Regenerating the ledger changes committed site data | Additive change; verify `results.html` and `ledger-viewer` still render |
| Generated file churn swamps review | Deterministic sort and stable formatting keep diffs minimal |

## Decisions taken

- Trust fix first, exporter second. An exporter emitting `native_decide`
  certificates would industrialize a soundness gap and mass-produce artifacts
  failing the repository's own acceptance bar.
- Witness recorded in the ledger, not recomputed in the exporter, to preserve
  provenance.
- `sqrt` bound with Mathlib, rather than a hand-written proof or Pratt
  certificates, for correctness and reuse.
- Certificates committed to git with a `--check` drift gate, mirroring
  `ruff format --check`, and following the precedent of committed
  `src/verified-runs.json`.
- Full ledger exported, with a budget guard, rather than a top-N subset.

## Out of scope, noted for later

`.claude/worktrees/frontend-rebuild/` holds a stale copy of the repository,
including an old `codebase/` tree. It pollutes repo-wide `grep` results. Worth
cleaning up separately; not part of this work.
