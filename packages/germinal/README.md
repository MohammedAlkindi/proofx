# Germinal

![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)
![Python](https://img.shields.io/badge/Python-3.11-blue.svg)
![Lean 4](https://img.shields.io/badge/Lean-4-purple.svg)
![Claude](https://img.shields.io/badge/LLM-Claude-orange.svg)
![Wolfram Alpha](https://img.shields.io/badge/Wolfram-Integrated-red.svg)
![Docker](https://img.shields.io/badge/Docker-ready-2496ED.svg?logo=docker&logoColor=white)
![Tests](https://img.shields.io/badge/Tests-pytest-green.svg)
![CI](https://github.com/MohammedAlkindi/Germinal/actions/workflows/ci.yml/badge.svg)

Germinal is an end-to-end pipeline for AI-assisted mathematical conjecture generation and formal verification. It proposes conjectures via Claude, grounds each one in recent arXiv literature and Mathlib4 lemma context, formalizes them in Lean 4 with compiler-error repair loops, attempts automated proofs using tactic racing and extended thinking, and searches for counterexamples using a three-method ensemble. Every experiment is committed as a reproducible Git snapshot with full metadata.

The central design commitment: a conjecture that survives formalization, fails proof search, and resists all counterexample methods is labeled **unrefuted** — not promising, not likely true, not validated. Typechecking a statement in Lean confirms only that the code is well-formed; a false-but-well-typed conjecture passes that check without issue. Three independent methods failing to disprove something is absence-of-disproof, not evidence of truth. Status labels reflect that uncertainty precisely.

## Pipeline

```
┌──────────────────────────────────────────────────────────────────────┐
│                          Germinal Pipeline                           │
│                                                                      │
│   Domain Input                                                       │
│       │                                                              │
│       ├─── arXiv context fetch (recent papers for the domain)        │
│       │                                                              │
│       ▼                                                              │
│  ┌──────────────────┐                                                │
│  │  ConjectureGen   │  Claude API + arXiv abstracts                  │
│  │                  │  + Mathlib4 RAG lemma signatures               │
│  └────────┬─────────┘                                                │
│           │ natural language statement                               │
│           ▼                                                          │
│  ┌──────────────────┐                                                │
│  │ NoveltyChecker   │  Jaccard similarity against existing corpus    │
│  │                  │  Rejects near-duplicates (threshold 0.55)      │
│  └────────┬─────────┘                                                │
│           │ novel conjecture                                         │
│           ▼                                                          │
│  ┌──────────────────┐                                                │
│  │ ComplexityRouter │  Scores formalizability + proof difficulty     │
│  │                  │  Routes: quick_tactics / claude_standard /     │
│  │                  │          extended_thinking / human_review      │
│  └────────┬─────────┘                                                │
│           │                                                          │
│           ▼                                                          │
│  ┌──────────────────┐                                                │
│  │   Formalizer     │  Claude → Lean 4 with Mathlib4 imports         │
│  │                  │  lake build validation                         │
│  │                  │  Repair loop: compiler error fed back to       │
│  │                  │  Claude for up to 3 retries                    │
│  └────────┬─────────┘                                                │
│           │ valid Lean 4 source                                      │
│           ▼                                                          │
│  ┌──────────────────┐                                                │
│  │    Verifier      │  Races 7 tactics: decide / norm_num / ring /   │
│  │                  │  omega / simp_all / aesop / tauto              │
│  │                  │  + Claude tactic proof                         │
│  │                  │  (extended thinking for hard conjectures)      │
│  │                  │  lake build validation on every attempt        │
│  └────────┬─────────┘                                                │
│           │                                                          │
│     ┌─────┴──────┐                                                   │
│   proved      not proved                                             │
│                   │                                                  │
│                   ▼                                                  │
│          ┌──────────────────┐                                        │
│          │ CounterexSearch  │  Three independent methods,            │
│          │                  │  run concurrently (15s timeout):       │
│          │                  │  1. Claude-based reasoning             │
│          │                  │  2. SymPy bounded enumeration          │
│          │                  │  3. Wolfram Alpha CAS query            │
│          │                  │  All candidates locally verified       │
│          │                  │  before acceptance                     │
│          └────────┬─────────┘                                        │
│                   │ unrefuted / counterexample_found                 │
│                   ▼                                                  │
│  ┌──────────────────┐                                                │
│  │ SnapshotManager  │  Git commit to `experiments` branch            │
│  │                  │  experiment.json + Lean source files           │
│  │                  │  Lock-protected HEAD management                │
│  └──────────────────┘                                                │
│                                                                      │
│  FastAPI ←→ Celery workers ←→ Next.js                                │
│  (SSE streaming, interactive Lean editor, lineage graph)             │
└──────────────────────────────────────────────────────────────────────┘
```

## Key engineering decisions

**arXiv grounding.** Before generating conjectures, `src/arxiv_client.py` fetches recent paper abstracts for the target domain (up to 4 by default) and includes them in the generation prompt. Conjectures are seeded in current literature, not produced in a vacuum.

**Mathlib4 RAG.** `src/mathlib_rag.py` maintains a curated index of Mathlib4 declarations. Relevant lemma signatures are injected into formalization prompts so Claude has direct access to the correct Lean 4 library identifiers rather than guessing import paths.

**Novelty filtering before Lean.** `src/novelty.py` computes Jaccard similarity between the incoming conjecture and all existing statements and rejects near-duplicates above a configurable threshold (default 0.55). Filtering runs before any Lean work, so duplicates cost only a similarity computation.

**Complexity routing.** `src/complexity.py` scores formalizability (1–5) and proof difficulty (1–5) before invoking Lean. The scores determine proof strategy: `quick_tactics`, `claude_standard`, `extended_thinking`, or `human_review`. Hard conjectures get extended thinking; simple ones skip directly to fast tactics.

**Lean 4 formalization with repair loop.** `src/formalizer.py` translates conjectures to Lean 4 with Mathlib4 imports and validates via `lake build` against a persistent Lean sandbox (`src/lean_sandbox.py`). When the build fails, the full compiler error is appended to the prompt and Claude retries, up to `FORMALIZE_REPAIR_ATTEMPTS` times (default: 3). The sandbox retains Mathlib4 between calls—Lean compilation is warm after first boot.

**Tactic racing.** `src/verifier.py` races seven automation tactics (`decide`, `norm_num`, `ring`, `omega`, `simp_all`, `aesop`, `tauto`) concurrently against Claude-generated tactic proofs. Only a clean `lake build` counts as success.

**Extended thinking for hard conjectures.** Conjectures routed to the `extended_thinking` strategy use Claude's extended thinking mode during tactic proof generation, with a configurable token budget (default: 10,000 tokens).

**Three-method counterexample ensemble.** `src/counterexample.py`'s `search_ensemble()` launches Claude reasoning, SymPy brute-force enumeration, and Wolfram Alpha CAS queries as three fully independent methods, running concurrently under a 15-second global deadline. All three methods' results are preserved regardless of consensus.

**Local candidate verification.** Every counterexample candidate returned by any method is tested by `LocalCounterexampleVerifier` before being accepted. Candidates that fail local verification are rejected, their rejection reason is logged, and they are not counted as disproof.

**Wolfram Alpha response caching.** Wolfram responses are stored as JSON files under `.cache/wolfram/`, keyed by a SHA-256 hash of the conjecture text and query string, with a configurable TTL (default: 24 hours). Repeated queries for the same conjecture do not hit the Wolfram API.

**Failure registry feedback loop.** `src/failure_registry.py` tracks per-subfield failure counts in Redis (in-process dict when Redis is unavailable). Subfields that accumulate five or more failures are included as avoidance hints in the next generation prompt, steering the model away from historically problematic areas.

**Dual persistence.** Every experiment is written twice: to a SQLAlchemy ORM row queryable via the REST API, and as a JSON snapshot committed to the `experiments` Git branch. Any schema change must update both write paths.

**Git branch safety.** `SnapshotManager._commit_to_branch` swaps HEAD via `symbolic_ref` to write to the `experiments` branch, then swaps back. A `threading.Lock()` serializes concurrent calls so Celery's workers never race on that swap.

**Lineage and derive.** Each experiment can spawn derived conjectures via `POST /api/v1/experiments/{id}/derive`, specifying a relation (`generalization`, `special_case`, or `analogue`). Lineage is retrievable as a graph via `GET /api/v1/experiments/{id}/lineage`.

## Architecture

| Module | File | Role |
|--------|------|------|
| Conjecture Generator | `src/conjecture_generator.py` | Claude + arXiv context + Mathlib4 RAG → structured conjecture JSON with confidence estimate |
| Complexity Router | `src/complexity.py` | Pre-pipeline score for formalizability and proof difficulty; routes to one of four strategies |
| Novelty Checker | `src/novelty.py` | Jaccard similarity against existing conjectures; rejects near-duplicates |
| Formalizer | `src/formalizer.py` | Claude → Lean 4; `lake build` validation; compiler-error repair loop |
| Verifier | `src/verifier.py` | Tactic racing (7 quick tactics) + Claude tactic proofs + extended thinking mode |
| Counterexample Finder | `src/counterexample.py` | Three-method ensemble: Claude, SymPy, Wolfram Alpha; local candidate verification |
| arXiv Client | `src/arxiv_client.py` | Fetches recent paper abstracts to ground generation in current literature |
| Mathlib4 RAG | `src/mathlib_rag.py` | Curated Lean 4 declaration index; injects lemma signatures into formalization prompts |
| Lean Sandbox | `src/lean_sandbox.py` | Persistent Lean 4 + Mathlib4 environment; all `lake build` calls go through here |
| Failure Registry | `src/failure_registry.py` | Redis-backed per-subfield failure tracking; builds avoidance hints for generation prompts |
| Snapshot Manager | `src/snapshot.py` | Commits each experiment to the `experiments` Git branch; lock-protected HEAD management |
| Settings | `src/settings.py` | Centralized pydantic-settings config; all env vars with sane defaults |
| Database | `src/db.py` | SQLAlchemy async ORM; `ExperimentRow`, `AnnotationRow`, `JobRow` |
| API | `api/routes.py` | FastAPI router: async jobs via Celery (sync fallback), SSE streaming, lineage, derive |
| Tasks | `api/tasks.py` | Celery pipeline orchestrator; dual persistence; failure registry updates |
| Frontend | `frontend/` | Next.js + Tailwind: pipeline UI, experiment table, interactive Lean editor, lineage view |

See [docs/architecture.md](docs/architecture.md) for per-module implementation details.

## Quickstart

```bash
# 1. Clone
git clone https://github.com/MohammedAlkindi/Germinal.git
cd Germinal

# 2. Configure
cp .env.example .env
# Edit .env — ANTHROPIC_API_KEY is required; all other keys have defaults

# 3. Launch
docker-compose up --build
```

First boot downloads Mathlib4 into the Lean sandbox (several minutes). Subsequent warm builds take 5–30 seconds.

- API + interactive docs: `http://localhost:8000/docs`
- Frontend: `http://localhost:3000`

Docker brings up: postgres, redis, otel-collector, api, worker (Celery), flower, and frontend.

## Core pipeline

### Conjecture generation

`src/conjecture_generator.py` calls Claude with a domain prompt that includes recent arXiv abstracts and Mathlib4 lemma signatures. It returns structured JSON: natural-language statement, subfield tag, motivation, confidence estimate, and tags. Prompt caching (`cache_control: ephemeral`) is applied to the static instruction block so repeat calls in the same session reuse the cached prefix.

### Novelty and complexity pre-screening

`src/novelty.py` computes Jaccard similarity between the incoming conjecture and all previously seen statements. Conjectures above the similarity threshold are rejected before Lean is invoked.

`src/complexity.py` scores formalizability (1–5) and proof difficulty (1–5) independently using a separate Claude call. Scores determine proof strategy, which is passed downstream to the verifier.

### Lean 4 formalization

`src/formalizer.py` asks Claude to translate the conjecture into valid Lean 4 with Mathlib4 imports. The result is passed to `LeanSandbox.build()` which runs `lake build` against a persistent Mathlib4 checkout. Failed builds trigger the repair loop: the compiler error is appended to the prompt and Claude retries, up to `formalize_repair_attempts` times (default: 3). Only a clean build advances to verification.

**Critical limitation**: typechecking confirms the Lean code is well-formed, not that the underlying mathematical claim is true. A false statement with correct syntax passes this check. See [docs/formalization-and-verification.md](docs/formalization-and-verification.md).

### Automated proof search

`src/verifier.py` attempts proof in two phases:
1. Seven automation tactics race concurrently: `decide`, `norm_num`, `ring`, `omega`, `simp_all`, `aesop`, `tauto`.
2. Claude generates a multi-step tactic proof. Conjectures routed to `extended_thinking` use Claude's extended thinking mode for this step.

Each attempt is validated by `lake build`. Only a passing build counts as success. If proof succeeds, the experiment is marked `proved`. If not, counterexample search begins.

### Counterexample ensemble

`counterexample.py`'s `search_ensemble()` launches three methods concurrently:

1. **Claude** (`CounterexampleFinder`): asks the model to reason about the conjecture and propose a concrete disproof with verification.
2. **SymPy** (`SymbolicCounterexampleFinder`): brute-force enumeration over bounded integer domains. Returns `applicable=False` for claim types it cannot handle.
3. **Wolfram Alpha** (`WolframCounterexampleFinder`): queries the CAS engine when `WOLFRAM_APP_ID` is configured. Responses are cached by conjecture hash.

Every candidate returned by any method is tested by `LocalCounterexampleVerifier`. Candidates that fail local verification are rejected and not counted. All three methods' results are preserved in the response regardless of agreement.

See [docs/counterexample-search.md](docs/counterexample-search.md) for scope constraints, caching details, and consensus semantics.

### Failure registry feedback

After each run, `failure_registry.py` records whether formalization and proof succeeded or failed for the conjecture's subfield. Subfields exceeding the failure threshold (5) appear as avoidance hints in subsequent generation prompts.

## Status semantics

| Status | Meaning |
|--------|---------|
| `proved` | `lake build` passed on a complete proof |
| `unrefuted` | Formalized; proof search failed; no locally verified counterexample found by any method |
| `counterexample_found` | At least one method returned a locally verified counterexample |
| `invalid` | Lean 4 formalization failed; repair loop exhausted |

**`unrefuted` does not imply credibility.** It means the system's current methods could not disprove the statement. This is consistent with the conjecture being genuinely open, trivially false in a way no method caught, or simply outside the scope of automated search.

## Reproducibility

Every pipeline run commits to the `experiments` Git branch:

```
experiments/
└── <uuid>/
    ├── experiment.json   # full pipeline metadata snapshot
    ├── conjecture.txt    # natural-language statement
    ├── conjecture.lean   # Lean 4 formalization
    └── proof.lean        # proof (if found)
```

To replay any experiment:

```bash
git checkout experiments
cat experiments/<uuid>/experiment.json
lean --run experiments/<uuid>/proof.lean
```

See [docs/reproducibility.md](docs/reproducibility.md) for the commit format, branch safety guarantees, and dual-persistence rationale.

## API

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/v1/generate` | Generate N conjectures; `?stream=true` for SSE delivery |
| `POST` | `/api/v1/formalize` | Translate a conjecture to Lean 4 |
| `POST` | `/api/v1/verify` | Attempt automated proof |
| `POST` | `/api/v1/pipeline` | Full async pipeline run (returns job ID immediately) |
| `GET` | `/api/v1/jobs/{id}` | Poll async job status |
| `GET` | `/api/v1/jobs/{id}/stream` | SSE stream of job progress events |
| `GET` | `/api/v1/experiments` | List all experiments with optional filters |
| `GET` | `/api/v1/experiments/{id}` | Full experiment detail |
| `GET` | `/api/v1/experiments/{id}/export` | Export as Lean source or LaTeX |
| `GET` | `/api/v1/experiments/{id}/lineage` | Lineage graph for derived conjectures |
| `POST` | `/api/v1/experiments/{id}/derive` | Derive new conjectures from an existing one |
| `POST` | `/api/v1/experiments/{id}/annotate` | Attach human annotation to an experiment |
| `GET` | `/api/v1/stats` | Aggregate stats and failure registry contents |

Interactive docs: `http://localhost:8000/docs`. Full reference with request/response schemas: [docs/api.md](docs/api.md).

## Development (without Docker)

```bash
# Backend
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env             # set ANTHROPIC_API_KEY at minimum

uvicorn api.main:app --reload

# Celery worker (separate terminal)
celery -A api.celery_app worker --loglevel=info
```

If Redis is not running, Celery and `FailureRegistry` both fall back silently to synchronous in-process behavior. This is intentional for development environments without Redis.

```bash
# Frontend (separate terminal)
cd frontend
npm install
npm run dev
```

Lean 4 must be installed via [elan](https://github.com/leanprover/elan) when running outside Docker:

```bash
curl -sSf https://raw.githubusercontent.com/leanprover/elan/master/elan-init.sh | sh
```

## Testing

```bash
python -m pytest tests/ -v
```

No live Lean install or Anthropic API key is required. All `lake build` subprocess calls and all Claude API calls are mocked. Every pipeline module has a corresponding test file. `tests/test_symbolic_counterexample.py` is the reference example for new test files.

```bash
# Backend lint
ruff check src/ api/
ruff format --check src/ api/

# Frontend type check
cd frontend && npx tsc --noEmit
```

CI runs on every push to `main` and on all pull requests (`.github/workflows/ci.yml`): backend runs ruff and pytest; frontend runs `tsc --noEmit`.

## Project structure

```
src/           core pipeline modules
api/           FastAPI routes, Celery tasks, Pydantic models
frontend/      Next.js + Tailwind UI
tests/         pytest suite (all dependencies mocked)
docs/          deeper technical documentation
experiments/   Git branch containing per-experiment snapshots (not on main)
```

## Further reading

- [docs/architecture.md](docs/architecture.md) — per-module implementation details and configuration reference
- [docs/formalization-and-verification.md](docs/formalization-and-verification.md) — Lean 4 formalization, repair loop, tactic racing, extended thinking
- [docs/counterexample-search.md](docs/counterexample-search.md) — three-method ensemble, scope constraints, local verification, Wolfram caching
- [docs/reproducibility.md](docs/reproducibility.md) — Git snapshot format, branch safety, replay instructions
- [docs/api.md](docs/api.md) — full API reference with request/response schemas

## License

MIT — see [LICENSE](LICENSE).
