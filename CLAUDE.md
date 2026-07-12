# CLAUDE.md

Context for Claude Code working in this repo. Read this before touching anything.

## What this is

ProofX is two things sharing one repo:

1. A static research site (`public/` + `src/`) deployed on Vercel, presenting conjecture-engine findings.
2. A Python research toolkit (`codebase/`) of directed-search "falsification engines" that hunt for counterexamples to the Collatz, Goldbach, and Riemann-hypothesis-adjacent conjectures, rather than proving anything.

`packages/germinal/` is a **separate project** (a sibling HackMIT effort — Claude-driven Lean 4 conjecture generation/proof) pulled in via `git subtree` from its own remote (`germinal-remote` → github.com/MohammedAlkindi/Germinal). It has its own `CLAUDE.md`; that file governs inside `packages/germinal/`, not this one.

## Architecture

- `codebase/` — the research engines, each a self-contained package with its own `RESEARCH_LOG.md`:
  - `FalsificationEngine/` — `FalsificationEngine.py` (orchestrator), `RiemannFalsifier.py`, `calibration.py`. Entry point for directed counterexample search.
  - `CollatzX/` — Analytics, Bifurcation, Boundary, PrimeGraph, Processing, RareEvent.
  - `GoldbachX/` — AlgebraicExtensions, GoldbachReasoner, MetaVariant, PartitionEnumerator, SequenceGenerator, SieveEngine.
  - `ReimannX/` — ContourTruth, KeiperLi, PrimeEchos, TuringThreshold, ZeroProperties, ZetaMirror.
  - `CrossEngineAnalysis/` — correlates near-miss candidates across engines.
  - `cli.py` — unified CLI (`python -m codebase.cli <falsify|calibrate|correlate|riemann|collatz|goldbach>`).
- `tests/` — pytest suite, one dir per engine (`test_falsification_engine/`, `test_collatzx/`, etc.).
- `docs/` — `architecture.md`, `deployment.md`, `content-strategy.md`, `CHANGELOG.md`, and `engines/*.md` (design writeups per engine — read `docs/engines/falsification.md` before changing scoring logic, it derives every weight used).
- `public/` + `src/` — the static site. `src/components/*.html` are shared partials, `src/scripts/*.js` build the ledger viewer and nav, `src/styles/` is plain CSS. `scripts/build.sh` is currently a no-op (static site, no build step); `scripts/validate-links.sh` checks links; `scripts/cleanup.sh` removes OS cruft.
- `assets/` — images/PDFs referenced by the public site (tracked, unlike `findings/`).
- `findings/`, `legacy/` — gitignored. Business/pitch material and a large historical archive; never add these back to tracking.

## Stack

- Python 3.10, pinned deps in `requirements.txt` (numpy, scipy, sympy, pandas, scikit-learn, statsmodels, torch, networkx, shap, plotly).
- Static site: plain HTML/CSS/JS, deployed on Vercel (`vercel.json` controls rewrites and security headers — don't loosen `X-Frame-Options`/CSP-adjacent headers without a reason).

## Commands

```bash
pytest                                    # full suite, coverage gate enforced (see below)
ruff check .                              # lint
ruff format --check .                     # format check
mypy codebase                             # type check
python -m codebase.cli falsify --budget 200 --seed 42 --target both
./scripts/validate-links.sh               # static site link check
```

## Hard rules

- **Never let a falsification engine's silence become a claim of truth.** A conjecture that survives a search run is "unrefuted at this budget," not "verified" or "likely true." This applies to CLI output, ledger labels, docs, and anything rendered on the public site — mirror the same honesty standard `packages/germinal/CLAUDE.md` enforces for its own pipeline.
- Coverage is gated at 60% (`pyproject.toml`, `--cov-fail-under=60`). New engine code ships with tests under the matching `tests/test_*` dir — don't drop the gate to get a merge through.
- `FalsificationEngine`'s feature weights (Collatz risk score, Goldbach deficit score) are asserted to sum to 1.0 at class load and are derived in `docs/engines/falsification.md`. If you change a weight, update that doc's derivation, not just the code.
- Reproducibility: all engine randomness flows through a single seeded `np.random.Generator` with deterministically derived child seeds. Don't introduce unseeded randomness into a falsifier.
- Don't reorganize or reformat anything under `packages/germinal/` as a side effect of a ProofX-root change — it's synced against a separate upstream via `git subtree` and unrelated diffs there make that sync painful.
- No hardcoded secrets. This repo currently has no server-side component of its own (the static site has none, Germinal's env config lives in `packages/germinal/`).
