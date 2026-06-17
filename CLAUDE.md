# CLAUDE.md

Context for Claude Code working in this repo. Read this before touching anything.

## What this is

Germinal generates mathematical conjectures via Claude, formalizes them in Lean 4, attempts automated proofs, and commits every experiment as a reproducible Git snapshot. Backend is FastAPI + Celery + Postgres/SQLite, frontend is Next.js + Tailwind. Full pipeline: generate → formalize → verify → snapshot.

This is a HackMIT differentiator project alongside ProofX. Treat correctness and rigor as higher priority than feature breadth — judges and research-adjacent reviewers will poke at the validation logic first.

## Architecture, in order of how data flows

1. `src/conjecture_generator.py` — Claude proposes N conjectures for a domain. Self-reported confidence score, no independent check.
2. `src/formalizer.py` — translates conjecture to Lean 4, validates with `lake build` against a persistent Mathlib4 sandbox (`src/lean_sandbox.py`). Has a repair loop: failed builds feed the compiler error back to Claude for up to `formalize_repair_attempts` (default 3) retries.
3. `src/verifier.py` — races 7 quick automation tactics (`decide`, `norm_num`, `ring`, `omega`, `simp_all`, `aesop`, `tauto`) against Claude-generated tactic proofs. Only counts success if `lake build` actually passes.
4. `src/counterexample.py` — on verify failure, runs **three independent methods**: Claude-based search, symbolic SymPy search, and Wolfram Alpha search. All discovered candidates are verified locally before acceptance; all signals are preserved and returned.
5. `src/snapshot.py` — commits every experiment to the `experiments` git branch with full metadata. `_commit_to_branch` swaps HEAD via `symbolic_ref`; a `threading.Lock()` serializes concurrent calls so Celery's `--concurrency=2` threads never race on that swap.
6. `src/complexity.py` — pre-pipeline complexity estimate that routes proof strategy (quick_tactics / claude_standard / extended_thinking / human_review).
7. `src/novelty.py` — Jaccard similarity filter to reject near-duplicate conjectures before they enter the pipeline.

API surface is in `api/routes.py`, async jobs run through `api/tasks.py` via Celery with a sync fallback if Celery is unavailable. Frontend pages: `frontend/pages/index.tsx` (run pipeline, view table) and `frontend/pages/experiments/[id].tsx` (detail view, interactive Lean editor, lineage, derive).

**Dual persistence**: every experiment is written in two places by `api/tasks.py` / `api/routes.py`:
- `ExperimentRow` (SQLAlchemy ORM, `src/db.py`) — queryable via the REST API.
- `SnapshotManager` JSON files on the `experiments` git branch (`src/snapshot.py`) — reproducible commits.

Any schema change must update both write paths. Frontend TypeScript interfaces are **not** generated from Pydantic models — grep for duplicated interface definitions in `ExperimentTable.tsx`, `CommandPalette.tsx`, and `frontend/pages/experiments/[id].tsx` before changing any response shape.

## Known gap — do not paper over this

The pipeline only validates that Lean code **typechecks**, not that the underlying claim is true. A false-but-well-typed conjecture sails through formalization. If it then fails to be proved AND all three counterexample methods return no locally verified counterexample, the system has no way to distinguish "genuinely open problem" from "false statement no method can disprove."

Do not collapse "unproved and unrefuted" into a status that visually implies the conjecture is credible or promising. It is an unknown, not a result. Do not paper over this in docs, UI copy, or API response labels.

## Hard rules

- Never claim a conjecture is "true" or "likely true" based solely on absence of a found counterexample. Label it unrefuted, not validated.
- Never modify the Lean sandbox build logic (`src/lean_sandbox.py`) to skip or weaken `lake build` validation, even temporarily. Mock the sandbox call for faster dev loops; never change what counts as valid.
- Counterexample methods are **additive only** — do not remove or replace the existing LLM-based check. Both the LLM and symbolic results must run and be preserved.
- If a symbolic/CAS check can't cleanly apply to a conjecture's structure (infinite domain, no bounded reduction), return "not applicable" explicitly. Never force a fake pass/fail.
- Do not remove or bypass the `threading.Lock()` in `src/snapshot.py`'s `_commit_to_branch`. The lock prevents HEAD corruption under Celery concurrency.
- Every new pipeline module ships with tests. Coverage must grow; no new stage is complete without a test file.

## Running this locally

`ANTHROPIC_API_KEY` is required with no default — `Settings()` raises on instantiation without it. `docker-compose up --build` brings up postgres, redis, the otel-collector, api, worker, flower, and frontend. First boot runs `lake update` inside the Lean sandbox and downloads Mathlib4 (several minutes); subsequent warm builds take 5-30 seconds. If Redis isn't running, Celery and `FailureRegistry` both fall back silently to sync/in-process behavior — this is intentional.

## Running tests

```
python -m pytest tests/ -v
```

No live Lean install or Anthropic API key is required — all Claude API calls and all `subprocess`/`lake` calls are mocked. Every new module must have a corresponding test file; `tests/test_symbolic_counterexample.py` is the reference example.

## Conventions

- Lint: `ruff check src/ api/` and `ruff format --check src/ api/`. Run before considering anything done.
- Claude API calls use prompt caching (`cache_control: ephemeral`) on static system/instruction blocks — preserve this pattern when adding new Claude calls, don't cache dynamic per-request content.
- New Pydantic models go in `api/models.py`; extend existing response schemas additively rather than renaming fields, since the frontend consumes them directly via fetch + manual TypeScript interfaces (no shared codegen).
- Settings are centralized in `src/settings.py` via pydantic-settings; add new env vars there with a sane default, not scattered `os.getenv` calls.
- Frontend has no shared API client — each component defines its own `fetcher`/interface. When you change a response shape, grep for every place that interface is duplicated. Frontend lints separately via `next lint` from `frontend/`.

## What not to touch without being asked

- `Dockerfile.api` / `docker-compose.yml` Lean/elan install steps — fragile, version-pinned to `leanprover/lean4:stable`.
- The Celery sync-fallback pattern in `api/routes.py`'s `run_pipeline` — it's intentional, not a bug, for environments without Redis.
- `otel-collector-config.yaml` — observability is opt-in via `OTEL_EXPORTER_OTLP_ENDPOINT`; don't make it required.
