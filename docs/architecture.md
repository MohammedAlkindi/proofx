# Architecture

This document describes implementation details for each module. For the high-level pipeline overview, see [README.md](../README.md).

## Data flow

```
Domain → arXiv fetch → ConjectureGen → NoveltyChecker → ComplexityRouter
       → Formalizer → Verifier → CounterexSearch → SnapshotManager
```

The Celery task in `api/tasks.py` owns the end-to-end orchestration. FastAPI submits the job and returns a job ID immediately; clients poll `GET /api/v1/jobs/{id}` or stream progress via `GET /api/v1/jobs/{id}/stream`. If Celery/Redis is unavailable, the pipeline runs synchronously in-process — this is an intentional fallback, not a bug.

---

## src/settings.py — centralized configuration

All environment variables are defined here via `pydantic-settings`. `Settings()` raises on instantiation if `ANTHROPIC_API_KEY` is not set. Key settings:

| Variable | Default | Description |
|----------|---------|-------------|
| `ANTHROPIC_API_KEY` | *(required)* | Claude API key |
| `CLAUDE_MODEL` | `claude-sonnet-4-20250514` | Model used for all Claude calls |
| `WOLFRAM_APP_ID` | `""` | Wolfram Alpha App ID; empty disables the Wolfram method |
| `WOLFRAM_CACHE_TTL_SECONDS` | `86400` | Wolfram response cache TTL (seconds) |
| `DATABASE_URL` | `sqlite+aiosqlite:///./germinal.db` | SQLAlchemy async database URL |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis URL for Celery and FailureRegistry |
| `LEAN_TIMEOUT` | `120` | Per-`lake build` call timeout (seconds) |
| `LEAN_SANDBOX_DIR` | `.lean_sandbox` | Persistent Lean 4 workspace directory |
| `GIT_EXPERIMENTS_BRANCH` | `experiments` | Branch for Git experiment snapshots |
| `NOVELTY_THRESHOLD` | `0.55` | Jaccard similarity threshold for deduplication |
| `THINKING_BUDGET_TOKENS` | `10000` | Extended thinking token budget; `0` disables |
| `ARXIV_MAX_RESULTS` | `4` | Max arXiv papers fetched per generation request |
| `FORMALIZE_REPAIR_ATTEMPTS` | `3` | Max Lean repair retries per conjecture |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | `""` | OpenTelemetry endpoint; empty disables tracing |

Never add scattered `os.getenv` calls. All env vars must go through `Settings`.

---

## src/arxiv_client.py — arXiv context

Fetches paper abstracts from the arXiv API for a given domain. The abstracts are included verbatim in the generation prompt, providing context about what is actively being researched. At most `ARXIV_MAX_RESULTS` papers are fetched per request. The call is async-first and is awaited before calling the conjecture generator.

---

## src/mathlib_rag.py — Mathlib4 declaration index

Maintains a curated list of Mathlib4 declarations (theorem names, type signatures, module paths). When the formalizer is invoked for a given conjecture, `mathlib_rag.py` retrieves the most relevant declarations based on the conjecture text and injects their signatures into the formalization prompt. This gives Claude direct access to the correct Lean 4 library identifiers rather than requiring it to guess import paths or declaration names.

The index is static (checked into the repo), not dynamically queried from Mathlib4 at runtime.

---

## src/conjecture_generator.py — conjecture generation

Calls Claude with a domain prompt that includes:
- Static system instructions (cached with `cache_control: ephemeral`)
- arXiv abstracts for the domain
- Mathlib4 lemma signatures
- Avoidance hints from the failure registry (if any subfields are flagged)

Returns structured JSON per conjecture:
- `id`: UUID
- `statement`: natural-language conjecture
- `domain`, `subfield`: classification tags
- `motivation`: brief rationale
- `confidence_estimate`: model self-report (0.0–1.0; not independently verified)
- `tags`: list of keyword tags

The confidence estimate is self-reported by the model and has no independent grounding. Do not treat it as a calibrated probability.

---

## src/novelty.py — Jaccard similarity filter

Computes token-level Jaccard similarity between an incoming conjecture and all previously seen statements. Conjectures above `NOVELTY_THRESHOLD` (default 0.55) are rejected before any Lean work is done. This runs cheaply on natural-language text and prevents near-duplicate conjectures from entering the expensive formalization pipeline.

---

## src/complexity.py — pre-pipeline complexity estimator

Makes a separate Claude API call to score the conjecture on two dimensions:
- `formalizability` (1–5): how straightforwardly the conjecture can be expressed in Lean 4
- `proof_difficulty` (1–5): how difficult automated proof is likely to be

The combined score maps to one of four proof strategies:

| Strategy | Description |
|----------|-------------|
| `quick_tactics` | Short timeout; try automation tactics only |
| `claude_standard` | Standard Claude call for tactic generation |
| `extended_thinking` | Claude extended thinking mode; higher token budget |
| `human_review` | Routed out of automated pipeline; flagged for human review |

The strategy is passed to `src/verifier.py`. The complexity estimator runs before Lean, so it operates only on the natural-language statement.

---

## src/lean_sandbox.py — persistent Lean 4 environment

Wraps all `lake build` invocations. The Lean 4 + Mathlib4 environment is kept in `LEAN_SANDBOX_DIR` (default `.lean_sandbox`) and persists across API calls. First boot runs `lake update` and downloads Mathlib4 (several minutes). Subsequent builds are warm and take 5–30 seconds.

All formalization and verification calls go through `LeanSandbox.build()`. Never bypass this by calling `lake` directly or shelling out around the sandbox — it would break the isolation guarantees the rest of the system depends on. Mock `LeanSandbox.build()` in tests; never weaken what counts as a valid build.

---

## src/formalizer.py — Lean 4 formalization

See [formalization-and-verification.md](formalization-and-verification.md) for full details.

Summary: Claude translates the conjecture to Lean 4 → `lake build` validates → on failure, compiler error is fed back and Claude retries (up to `FORMALIZE_REPAIR_ATTEMPTS` times). Only a clean build advances.

---

## src/verifier.py — automated proof search

See [formalization-and-verification.md](formalization-and-verification.md) for full details.

Summary: seven quick tactics race concurrently → Claude tactic proof (with extended thinking if strategy requires) → each attempt validated by `lake build`. Provides an async interface (`verify_async`) for use from FastAPI and Celery.

---

## src/counterexample.py — ensemble counterexample search

See [counterexample-search.md](counterexample-search.md) for full details.

Summary: `search_ensemble()` runs Claude, SymPy, and Wolfram Alpha concurrently under a 15-second global deadline. Every candidate is locally verified before acceptance. All three results are preserved. `search_dual()` is a backward-compatible wrapper.

---

## src/failure_registry.py — subfield failure tracking

Tracks formalization and proof failure counts per subfield. Backed by Redis when available; falls back to an in-process dict. Key behaviors:

- `record_failure(subfield, stage)`: increments counter.
- `record_success(subfield, stage)`: decrements counter (floors at 0).
- `problematic_subfields(stage)`: returns subfields with ≥ 5 failures at `stage`.
- `build_avoidance_hint()`: returns a prompt string listing subfields to avoid, for injection into the next generation call.

The failure threshold (`_AVOID_THRESHOLD = 5`) is a constant in the module. Both `formalize` and `verify` stages are tracked independently.

---

## src/snapshot.py — Git experiment snapshots

See [reproducibility.md](reproducibility.md) for the Git format and safety details.

Summary: `SnapshotManager.save()` writes experiment files and commits them to the `experiments` branch using a `symbolic_ref` swap. A `threading.Lock()` serializes concurrent calls.

---

## src/db.py — SQLAlchemy async ORM

Defines three tables:

- `ExperimentRow`: full experiment record (id, domain, conjecture, lean_code, is_valid, proved, final_proof, model_used, duration_ms, extra JSON blob).
- `AnnotationRow`: human annotations linked to experiments (interesting flag, notes, correct_proof).
- `JobRow`: Celery job status tracking (job_id, status, result, error, total_duration_ms).

The database is async-first (`aiosqlite` for SQLite, `asyncpg` for PostgreSQL). SQLite is the default; switch to PostgreSQL for production via `DATABASE_URL`. SQLite WAL mode is enabled automatically.

---

## api/routes.py — FastAPI routes

The router registers under `/api/v1` in `api/main.py`. All components (settings, generator, formalizer, verifier, snapshot) are injected via FastAPI's `Depends()` mechanism.

Key behaviors:
- `POST /generate` with `?stream=true` returns an `EventSourceResponse` that yields conjecture objects as they are parsed from the Claude stream.
- `POST /pipeline` submits a Celery task and returns `202 Accepted` with a job ID. If Celery is unavailable, it falls back to synchronous execution and returns `200 OK` with the full result.
- All Claude calls are wrapped in `asyncio.to_thread()` to avoid blocking the async event loop.

---

## api/tasks.py — Celery pipeline orchestrator

The main `run_pipeline_task` Celery task owns the full pipeline sequence:

1. Fetch arXiv context
2. Generate conjectures
3. Apply novelty filter (reject near-duplicates)
4. Complexity routing
5. Formalize (with repair loop)
6. Verify (tactic racing + Claude proofs)
7. Counterexample ensemble (if not proved)
8. Snapshot commit
9. Dual persistence: write to SQLAlchemy DB and Git snapshot

The task also updates `JobRow` status at each stage so polling clients get live progress.

---

## api/models.py — Pydantic request/response schemas

All request and response schemas live here. Key rules:
- Extend schemas additively (add optional fields with defaults). Renaming or removing fields breaks the frontend, which has no codegen — interfaces are defined manually in TypeScript.
- `CounterexampleResponse` includes per-method detail (`llm_result`, `symbolic_result`, `wolfram_result`) alongside top-level `found`/`counterexample`/`reasoning` fields for backward compatibility.

---

## Frontend (frontend/)

Next.js + Tailwind. Pages:
- `frontend/pages/index.tsx` — main UI: pipeline submission, experiment table, command palette.
- `frontend/pages/experiments/[id].tsx` — experiment detail: interactive Lean editor, lineage graph, derive panel.
- `frontend/pages/settings.tsx` — settings interface.

The frontend has no shared API client. Each component defines its own fetch logic and TypeScript interface. When changing a response schema, grep for duplicated interface definitions in `ExperimentTable.tsx`, `CommandPalette.tsx`, and `frontend/pages/experiments/[id].tsx`.

---

## Observability

OpenTelemetry tracing is configured in `api/main.py` and `otel-collector-config.yaml`. It is opt-in: set `OTEL_EXPORTER_OTLP_ENDPOINT` to enable. When the variable is empty (the default), no traces are emitted and no dependency on the collector exists. Do not make observability required.
