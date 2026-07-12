# CLAUDE.md

Context for Claude Code working in this repo. Read this before touching anything.

## What this is

ProofX is three things sharing one repo:

1. A static research site (`public/` + `src/`) deployed on Vercel, presenting conjecture-engine findings.
2. A Python research toolkit (`codebase/`) of directed-search falsification engines for Collatz, Goldbach, and Riemann-hypothesis-adjacent experiments.
3. A small root Lean 4 package (`ProofX.lean`, `lakefile.lean`, `ProofX/Certificates.lean`, `ProofX/Status.lean`) that kernel-checks bounded, finite certificates.

`packages/germinal/` is the old Germinal project preserved as a separate vendored package. It has its own `CLAUDE.md`; that file governs inside `packages/germinal/`, not this one. Germinal is not the same thing as the root `ProofX/` Lean package, so do not mix their toolchains, Lake state, or review boundaries.

## Architecture

- `codebase/` - the Python research engines, each a self-contained package with its own `RESEARCH_LOG.md`:
  - `FalsificationEngine/` - orchestrator, Riemann falsifier, calibration, ledgers, and directed counterexample search.
  - `CollatzX/` - analytics, bifurcation, boundary, graph, processing, and rare-event experiments.
  - `GoldbachX/` - algebraic extensions, symbolic reasoning, variants, partition enumeration, sequence generation, and sieves.
  - `ReimannX/` - contour, Keiper-Li, prime echo, threshold, zero-property, and zeta-mirror experiments. The path is currently misspelled; keep imports stable unless a task explicitly migrates it.
  - `CrossEngineAnalysis/` - correlates near-miss candidates across engines.
  - `cli.py` - unified CLI (`python -m codebase.cli <falsify|calibrate|correlate|riemann|collatz|goldbach>`).
- `ProofX/` - root Lean 4 modules (`Certificates.lean`, `Status.lean`). Small and intentionally narrow; see `docs/lean4.md` before adding anything here.
- `tests/` - pytest suite for the root Python toolkit.
- `docs/` - architecture, deployment, content, changelog, Lean, MVP, and engine writeups.
- `public/` + `src/` - static site output and source fragments. `scripts/build.sh` is currently a no-op; `scripts/validate-links.sh` checks links.
- `assets/` - tracked images/PDFs referenced by the public site.
- `packages/germinal/` - isolated old Germinal project. Do not re-expand it into the repository root.
- `findings/`, `legacy/` - gitignored local business/pitch material and historical archives. Do not re-track, move, or delete their contents without being asked.

## Stack

- Python 3.13, pinned runtime dependencies in `requirements.txt`, and dev tools in `requirements-dev.txt`.
- Package metadata in `pyproject.toml`; keep its dependency list synchronized with `requirements.txt`.
- Lean 4, pinned by `lean-toolchain` (`leanprover/lean4:v4.31.0`), built with `lake build`.
- Static site: plain HTML/CSS/JS, deployed on Vercel via `vercel.json`.

## Commands

```bash
python -m pip install -r requirements.txt -r requirements-dev.txt
pytest
ruff check .
ruff format --check .
mypy codebase
lake build
python -m codebase.cli falsify --budget 200 --seed 42 --target both
./scripts/validate-links.sh
```

On Windows, use `scripts/cleanup.ps1 -Deep` to remove local caches, coverage outputs, `.venv`, and any old root-level `frontend/` scratch folder. On Unix shells, use `./scripts/cleanup.sh --deep`.

## Hard rules

- Never let a falsification engine's silence become a claim of truth. A conjecture that survives a search run is "unrefuted at this budget," not "verified," "validated," "likely true," or "proved."
- Coverage is gated at 60% (`pyproject.toml`, `--cov-fail-under=60`). New engine code ships with tests under the matching `tests/test_*` directory.
- `FalsificationEngine` feature weights are asserted to sum to 1.0 and are derived in `docs/engines/falsification.md`. If you change a weight, update that doc's derivation too.
- Reproducibility: all engine randomness flows through a seeded `np.random.Generator` with deterministically derived child seeds. Do not introduce unseeded randomness into a falsifier.
- Do not reorganize or reformat anything under `packages/germinal/` as a side effect of a ProofX-root change.
- No hardcoded secrets. `.env` files are ignored; `.env.example` files are allowed.
- Root Lean artifacts follow the same "unrefuted != proved" discipline as the Python side (`docs/lean4.md`): no accepted proof may contain `sorry`, `admit`, an unsound `axiom`, or `unsafe` code added to bypass an obligation.

## Known gaps

- The rationale for the current coverage, mypy, and ruff exclusions on older engine submodules is not fully documented. Treat the exclusions as cleanup debt, not as a pattern to expand.
- The Lean certificate layer contains hand-written examples only. There is not yet an exporter from `FalsificationEngine` JSONL ledgers to Lean-checkable artifacts.
