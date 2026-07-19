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

Scope: `ProofX/Certificates.lean`. No new dependencies.

Bound trial division, reducing ~50,000 unfoldings per prime to ~316. But take
the bound from the *exporter* rather than computing it in Lean:

```lean
def IsPrime (p : Nat) : Prop :=
  2 ≤ p ∧ ∀ d, d ∣ p → d = 1 ∨ d = p

theorem isPrime_of_bounded (p b : Nat)
    (hp : 2 ≤ p) (hb : p ≤ b * b)
    (hnd : hasDivisorUpTo p b = false) : IsPrime p
```

The exporter already knows `p`, so it emits the bound `b` alongside it and Lean
verifies instead of computing. The `p ≤ b * b` side condition costs the kernel
one multiplication.

This is the same principle Phase 3 applies to the Goldbach pair — the search
finds the witness, Lean checks it — pushed one level deeper. Certificates carry
their own bound.

**Why not Mathlib.** The earlier draft of this design added Mathlib to get
`Nat.Prime` and a `sqrt`-bounded decidability instance. That was rejected:

- Mathlib has more than one decidability instance for `Nat.Prime` and they
  differ sharply in kernel reduction behavior. Picking wrong means `decide`
  hangs, and which is which must be measured rather than assumed. Carrying the
  bound in the certificate removes the question entirely.
- Mathlib would require `lake exe cache get` in CI or the job rebuilds from
  source for hours, for a package whose Lake manifest is otherwise empty.
- `docs/lean4.md` line 70 says to add Mathlib only when a specific theorem
  needs it. With the bound supplied externally, no theorem here does.

The cost is one self-contained proof obligation, resting only on
`Nat.div_mul_cancel` and basic arithmetic from core.

**Structural payoff.** `isPrime_of_bounded` is proven once. Every generated
certificate stays a cheap `by decide` on a Bool, and its *meaning* comes from
that single theorem. One hard proof, N cheap certificates — the generated
file's kernel cost scales linearly while the soundness argument does not.

**Estimated size.** Roughly 50-80 lines across two results: the main theorem
plus a helper, `2 ≤ m → m ≤ b → m ∣ p → hasDivisorUpTo p b = true`, by
induction on `b`. The main argument: if `d ∣ p` with `d ≠ 1` and `d ≠ p`, set
`e = p / d`; both `d > b` and `e > b` would give `p = d * e > b * b ≥ p`, so
the smaller of the two is a divisor in `[2, b]`, contradicting `hnd`.

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

Regenerate `results/ledger.jsonl` from `--seed 42 --budget 500`.

**Correction to an earlier assumption.** This design originally spoke of the
"committed" ledger. `results/` is gitignored (`.gitignore` line 45) and no
ledger has ever been tracked, so there is nothing committed to match against
and CI has no ledger file to read.

Rather than un-ignore a 500-row generated artifact, CI regenerates it from the
seed before checking drift. Phase 3 measured the search to be fully
deterministic — two runs agree on every candidate, score, seed, and witness —
so a fresh run is a sound reference. This is also the stronger check: it
verifies the certificates match what the engine *actually produces now*, not
merely what some committed snapshot claims.

The consequence for Phase 5 is that the drift gate belongs in `ci.yml`, which
already has the Python toolchain, rather than in `lean.yml`.

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
- **Provenance header** recording ledger path, SHA-256 of a *canonical
  projection* of the ledger, ledger schema version, exporter version, and row
  count.

  Not a hash of the raw bytes. Measured during Phase 3: two runs at
  `--seed 42 --budget 500` agree on every candidate, score, seed, and witness,
  but differ in two wall-clock fields — top-level `timestamp` and
  `details.computation_time_s`. Hashing raw bytes would change the header on
  every regeneration even when no certificate changed, producing exactly the
  reflexive-ignore problem the no-timestamp rule above exists to prevent.

  The canonical projection drops both fields, sorts keys, and hashes the
  result. Verified stable across regenerations.
- **One named theorem per row**, so every generated proof is reachable by the
  Phase 1 axiom audit.

Adds `kernel_checked_certificate` to the `claim_level` vocabulary. This is a
genuinely stronger level than the existing `bounded_run` and
`numerical_diagnostic`, and public copy must still name the finite scope of
each certificate per `docs/lean4.md`.

`ProofX.lean` imports the generated module so `lake build` covers it.

### Phase 5 — CI enforcement

Scope: `.github/workflows/lean.yml`, `.github/workflows/ci.yml`.

Four gates, split across the two workflows by which toolchain each needs:

`lean.yml`:

1. `lake build` — the committed certificates kernel-check.
2. Axiom audit — no proof depends on a disallowed axiom. Enforced inside the
   build by `ProofX/Audit.lean`, so gate 1 subsumes it; a textual pre-scan
   fails faster on the obvious case.

`ci.yml` (has Python; `lean.yml` does not):

3. Regenerate the ledger from `--seed 42 --budget 500`, then
   `export lean --check` — the committed certificates still match what the
   engine produces.
4. Build budget guard — a future ledger that blows up kernel cost fails loudly
   instead of hanging CI.

`lean.yml` currently runs bare `leanprover/lean-action@v1` with no axiom check.
It gains the audit and the drift check. With no Mathlib dependency it needs no
cache step, and the Lake manifest stays empty.

Estimated kernel cost across the full ledger is ~270k unfoldings
(250 x 444 for Collatz, 250 x 316 x 2 for Goldbach), which should complete in
seconds. Toolchain setup, not certificate checking, dominates the job.

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
| `isPrime_of_bounded` proof harder than estimated | Self-contained and resting only on core arithmetic; Phase 2 blocks Phase 4, so it surfaces before exporter work |
| Regenerating the ledger changes committed site data | Additive change; verify `results.html` and `ledger-viewer` still render |
| Generated file churn swamps review | Deterministic sort and stable formatting keep diffs minimal |
| Lean toolchain absent locally | `v4.31.0` was not installed on the dev machine; `lake build` had never run. Install before Phase 1 |

## Decisions taken

- Trust fix first, exporter second. An exporter emitting `native_decide`
  certificates would industrialize a soundness gap and mass-produce artifacts
  failing the repository's own acceptance bar.
- Witness recorded in the ledger, not recomputed in the exporter, to preserve
  provenance.
- Exporter-supplied divisor bound with a self-contained soundness proof, rather
  than Mathlib's `Nat.Prime` or Pratt certificates. Mathlib was rejected for
  the reasons in Phase 2. Pratt certificates give O(log p) kernel cost instead
  of O(sqrt p) and are the right answer if the Goldbach budget ever grows
  substantially, but at the current ledger maximum of 99,992 the ~316
  unfoldings per prime do not justify the added exporter complexity.
- Certificates committed to git with a `--check` drift gate, mirroring
  `ruff format --check`, and following the precedent of committed
  `src/verified-runs.json`.
- Full ledger exported, with a budget guard, rather than a top-N subset.

## Out of scope, noted for later

`.claude/worktrees/frontend-rebuild/` holds a stale copy of the repository,
including an old `codebase/` tree. It pollutes repo-wide `grep` results. Worth
cleaning up separately; not part of this work.
