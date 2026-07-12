# Architecture

This document describes the ProofX root project. It does not govern
`packages/germinal/`, which is a separate vendored project with its own docs and
operating rules.

## Project Boundaries

| Path | Purpose | Notes |
| --- | --- | --- |
| `codebase/` | Python research toolkit | Contains the engines, CLI, ledgers, calibration, and cross-engine analysis. |
| `ProofX/` | Root Lean 4 certificate layer | Contains bounded certificate predicates and status semantics. |
| `ProofX.lean`, `lakefile.lean`, `lake-manifest.json`, `lean-toolchain` | Lean package entry points | Build with `lake build`; toolchain and manifest are pinned at the root. |
| `tests/` | Root test suite | Covers the Python toolkit; coverage is configured in `pyproject.toml`. |
| `docs/` | Maintainer and research documentation | Explains methods, assumptions, and publication standards. |
| `src/` | Static research site | Source inputs under `components/`, `pages/`, `scripts/`, and `static/`; deployable HTML and assets at the `src/` root, built by `scripts/build_site.py`. |
| `packages/germinal/` | Vendored sibling project | Separate Lean 4 conjecture-generation and proof-attempt system. |
| `findings/`, `legacy/` | Ignored local archives | Historical/pitch material; do not re-track or reorganize during code cleanup. |

ProofX root work should not casually edit Germinal. If a change needs both
projects, keep the diffs and commit messages separate.

## Root Hygiene

The root should stay readable:

- Keep Lean entry points at the root (`ProofX.lean`, `lakefile.lean`, `lean-toolchain`) and Lean modules under `ProofX/`.
- Keep the old Germinal project under `packages/germinal/`; do not restore its old root-level `api/`, `frontend/`, `src/`, or `tests/` layout.
- Keep local caches, virtual environments, coverage outputs, and run ledgers out of git. Use `scripts/cleanup.ps1 -Deep` on Windows or `./scripts/cleanup.sh --deep` on Unix shells when the Explorer tree gets noisy.
- Keep `src/` as the single static-site tree: source subdirectories plus reproducible deploy output at the `src/` root.

## Data Flow

```text
CLI command
  -> FalsificationEngine
  -> target falsifier(s)
  -> candidate evaluation
  -> FalsificationLedger
  -> JSON summary and optional JSONL ledger
  -> optional calibration / cross-engine analysis
  -> optional static-site presentation
  -> optional Lean certificate export
```

The CLI is the public entry point for research runs. The static site is a
presentation layer over code and sample outputs; it is not the source of truth
for engine behavior.

The Lean package is a certificate layer over small bounded artifacts. It should
only receive concrete statements whose scope is finite and explicit.

## Status Semantics

Use the same status language in code, docs, and UI:

| Status | Meaning | Forbidden implication |
| --- | --- | --- |
| `counterexample_found` | The configured run found a candidate that violates the checked condition. | Do not claim theorem-level disproof without independently reviewing the checker. |
| `unrefuted_at_budget` | The configured run found no counterexample within its budget. | Do not say verified, validated, likely true, or proved. |
| `near_miss` | A candidate ranked highly by the engine's scoring function. | Do not treat the score as a calibrated probability. |
| `error` | The run failed or a candidate could not be evaluated. | Do not silently omit failed evaluations from public summaries. |

The project is strongest when it is boringly precise. A negative search result
is a statement about a run, not a statement about mathematical truth.

## Core Modules

### `codebase/FalsificationEngine/`

Owns shared run orchestration, ledger records, top-k ranking, calibration, and
the Collatz/Goldbach directed searches. `RiemannFalsifier.py` adds numerical
Riemann-adjacent diagnostics. All engines should write enough metadata for a
reader to understand what was checked and under what assumptions.

### `codebase/CollatzX/`

Contains Collatz trajectory features, graph and boundary experiments,
high-throughput processing helpers, and rare-event analysis. The root
FalsificationEngine uses the analytics layer for feature extraction and ranking.

### `codebase/GoldbachX/`

Contains prime sieves, partition enumeration, residue-class filters, and
heuristic symbolic reasoning. The root FalsificationEngine uses these pieces to
rank structurally sparse even numbers.

### `codebase/ReimannX/`

Contains numerical experiments related to zeta zeros and Keiper-Li
coefficients. The directory name is currently spelled `ReimannX`; use the
existing path in imports unless the rename is handled as a separate migration.

### `codebase/CrossEngineAnalysis/`

Compares near-miss neighborhoods across ledgers. This is exploratory tooling;
correlation between score families should be presented as a hypothesis generator,
not as evidence that conjectures are related.

### `ProofX/`

Contains the root Lean 4 modules. `ProofX/Certificates.lean` defines concrete
certificate types for bounded Collatz and Goldbach checks. `ProofX/Status.lean`
encodes the shared run-status vocabulary and proves that ordinary search
statuses are not theorem claims.

This layer is intentionally small. A Lean file may certify a finite witness or a
finite computation, but it should not mirror Python heuristics unless the exact
predicate, inputs, and output schema are documented.

## Ledger Contract

Every ledger row should preserve:

- `candidate`: the integer or index evaluated.
- `conjecture`: engine label such as `collatz`, `goldbach`, or `riemann`.
- `strategy`: candidate-generation strategy.
- `features`: numeric feature vector used for scoring.
- `near_miss_score`: ranking score in `[0, 1]`.
- `details`: engine-specific diagnostics.
- `timestamp`: run time in epoch seconds.
- `rng_seed`: seed used for candidate generation.

Do not publish a result table without enough context to reconstruct the command,
budget, seed, code revision, and dependency environment.

## Reproducibility Limits

ProofX tries to make runs replayable, but replay is not absolute. Differences in
Python, NumPy, SciPy, mpmath, platform math libraries, or hardware can alter
floating-point behavior and performance. Publish ledgers alongside summaries so
that downstream readers can inspect raw candidates instead of trusting a page
copy claim.

## Static Site

The site source under `src/` should be modest:

- Prefer "search", "rank", "inspect", "record", and "replay".
- Avoid "prove", "certify", "validate", and "verify" unless a specific checker
  and scope are named.
- Do not hard-code benchmark figures without a linked reproducible run.
- Keep `src/static/styles.css` stable unless the task is explicitly design work.

Run `scripts/build.sh` and `scripts/validate-links.sh` after changing site files.
