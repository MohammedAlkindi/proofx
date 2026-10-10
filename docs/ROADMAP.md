# Roadmap

This is a high-level, forward-looking view of open work. It intentionally does
not duplicate detail that already lives elsewhere and would drift out of sync:

- Granular, checkbox-level tooling status (CI, packaging, coverage gate) is
  tracked in [mvp.md](mvp.md)'s Status table.
- Landed changes are tracked in [CHANGELOG.md](CHANGELOG.md).
- The authoritative list of known gaps is `CLAUDE.md`'s "Known gaps" section.

Update this file when a workstream starts, finishes, or is dropped. Don't let
it become a second source of truth for line-item status — link out instead.

## Now

- **Independent reproductions of GB-001.** Compare candidate-ledger hashes on
  another platform; attach the manifest and verifier output.
- **Held-out Goldbach intervals.** Prespecify interval bands and seeds before
  running them. Examine finite-size effects and family ablations.
- **A Collatz baseline study.** Define an independent target metric, match
  domains and budgets, and separate shared trajectory suffixes in evaluation.
- **Long-run recovery.** Add resumable search state and test interrupted runs
  against uninterrupted runs before recommending large unattended jobs.
- **Rehabilitate excluded modules individually.** The current exclusions and
  promotion criteria are recorded in [quality-scope.md](quality-scope.md).
  Historical rationale is unknown; their presence is not evidence of support.

## Research workbench

- [GB-001](experiments/goldbach-policy-comparison.md): an executable Goldbach
  policy comparison, complete reference dataset, per-seed ledgers, and independent recount.
- [Annotation calibration](calibration.md): held-out metrics with explicit
  label semantics; probability-1 ECE is included.
- Budget-zero searches do no evaluations. Goldbach counting rejects candidates
  beyond the complete sieve and uses the unordered-pair asymptotic convention.
## Recently landed

- **Ledger-to-Lean exporter.** `python -m codebase.cli export lean` turns
  ledger rows into named, kernel-checked Lean theorems in
  `ProofX/Generated/LedgerCertificates.lean`, with a provenance header and a
  drift gate in CI. The Lean layer now reflects actual search output rather
  than hand-written examples. Design:
  `docs/superpowers/specs/2026-07-19-lean-certificate-exporter-design.md`.
- **Kernel-checked, not compiler-trusted.** Certificates close with `decide`
  instead of `native_decide`, and `ProofX/Audit.lean` fails the build if any
  theorem depends on an axiom outside the allowed three.

## Non-goals

Consistent with the "unrefuted at this budget, not proved" discipline in
`CLAUDE.md` and the README's "What ProofX Does Not Claim" section, this
roadmap will not include:

- Proving Collatz, Goldbach, the Riemann Hypothesis, or any related open
  conjecture.
- Treating a clean run, a passing CI gate, or a high near-miss score as
  evidence of truth rather than search coverage.
- Feature work that doesn't improve correctness, reproducibility, code
  quality, documentation, performance, testing, or developer experience (see
  `CONTRIBUTING.md`'s Philosophy section).
