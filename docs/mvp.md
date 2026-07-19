# MVP Bar

This document defines the minimum viable state for ProofX to be a credible,
checkable research toolkit, not a product launch checklist. "MVP" here means:
a stranger can clone the repo, run the checks the docs claim exist, and get
the same pass/fail result CI gets. Nothing more is implied.

## Bar

A change meets the MVP bar only if all of the following hold:

- `pip install -r requirements.txt -r requirements-dev.txt -e .` succeeds from a
  clean clone and actually installs `pytest`, `ruff`, and `mypy`.
- `pytest`, `ruff check .`, `ruff format --check .`, and `mypy packages/python/codebase` are
  runnable locally, not just described in `README.md` / `AGENTS.md`.
- The same four checks run in CI on every push and pull request against
  `main`, so the 60% coverage gate (`pyproject.toml`,
  `--cov-fail-under=60`) and lint/type-check are enforced by a gate, not by
  convention.
- `lake build` runs in CI for the root Lean layer (`docs/lean4.md`), separate
  from the Python checks.
- Packaging metadata (`pyproject.toml`) is enough to install `codebase` as a
  package, not just run it as a script tree.
- No secret-bearing file (`.env`, credentials) can be committed by accident;
  `.gitignore` excludes it.

This bar says nothing about engine correctness, near-miss scoring quality, or
site content. Those are governed by `docs/research-standards.md` and
`docs/engines/*.md`, not this doc.

## Status

| Item | State | Where |
| --- | --- | --- |
| `requirements-dev.txt` exists and is installable | Done | `requirements-dev.txt` |
| Python CI (lint, format check, type check, test) on push/PR to `main` | Done | `.github/workflows/ci.yml` |
| Lean CI (`lake build`) on push/PR | Done | `.github/workflows/lean.yml` |
| Coverage gate enforced by CI, not convention | Done | `.github/workflows/ci.yml` runs `pytest`, which enforces `--cov-fail-under=60` from `pyproject.toml` |
| `pyproject.toml` packaging metadata (`[project]`, build backend) | Done | `pyproject.toml` |
| Dependency updates automated | Done | `.github/dependabot.yml` |
| Pre-commit hooks mirror CI lint/type-check locally | Done | `.pre-commit-config.yaml` |
| Secrets excluded from version control | Done | `.gitignore` |
| Rationale for `coverage`/`mypy`/`ruff` exclusions on `CollatzX`/`GoldbachX`/`ReimannX` submodules and `cli.py` | Gap | `pyproject.toml` exclusion lists are still under-documented; see `CLAUDE.md` |
| Exporter from `FalsificationEngine` JSONL ledger to a Lean-checkable certificate | Done | `codebase/lean_export.py`; `python -m codebase.cli export lean` writes `ProofX/Generated/LedgerCertificates.lean`, drift-gated in `ci.yml` |
| Every accepted Lean proof kernel-checked, enforced rather than conventional | Done | `ProofX/Audit.lean` fails `lake build` on a disallowed axiom dependency |

Update this table when a row's state changes; keep it aligned with
`CLAUDE.md`'s "Known gaps" section and `docs/CHANGELOG.md`'s `[Unreleased]`
entries.

## Non-goals

- This bar does not cover formal verification of engine math, calibration
  quality, or public-site accuracy. Those have their own standards docs.
- Reaching this bar does not make any run result a proof. The claim-level
  rules in `docs/research-standards.md` still apply regardless of CI state.
- Closing the two remaining gaps above is not required to ship unrelated
  engine or site work; track them, don't block on them.
