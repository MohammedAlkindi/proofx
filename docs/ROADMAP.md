# Roadmap

This is a high-level, forward-looking view of open work. It intentionally does
not duplicate detail that already lives elsewhere and would drift out of sync:

- Granular, checkbox-level tooling status (CI, packaging, coverage gate) is
  tracked in [docs/mvp.md](docs/mvp.md)'s Status table.
- Landed changes are tracked in [docs/CHANGELOG.md](docs/CHANGELOG.md).
- The authoritative list of known gaps is `CLAUDE.md`'s "Known gaps" section.

Update this file when a workstream starts, finishes, or is dropped. Don't let
it become a second source of truth for line-item status — link out instead.

## Now

- **Document the coverage/mypy/ruff exclusion rationale.** `pyproject.toml`
  excludes `CollatzX`, `GoldbachX`, `ReimannX`, and `cli.py` from parts of the
  lint/type/coverage gates, but why each exclusion exists isn't written down
  anywhere. Treat the exclusions as cleanup debt: document the reason per
  module, then narrow or remove exclusions that no longer need to exist.
- **Ledger-to-Lean exporter.** `docs/lean4.md` describes turning
  `FalsificationEngine` JSONL ledger entries into Lean-checkable certificates,
  but `ProofX/Certificates.lean` still only contains hand-written examples.
  Building this exporter is the main way the Lean layer stops being a static
  demo and starts reflecting actual search output.

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
