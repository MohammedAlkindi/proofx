# Germinal

![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)
![Python](https://img.shields.io/badge/Python-3.11-blue.svg)
![Lean 4](https://img.shields.io/badge/Lean-4-purple.svg)
![Claude](https://img.shields.io/badge/LLM-Claude-orange.svg)
![Wolfram Alpha](https://img.shields.io/badge/Wolfram-Integrated-red.svg)
![Docker](https://img.shields.io/badge/Docker-ready-2496ED.svg?logo=docker&logoColor=white)
![Tests](https://img.shields.io/badge/Tests-pytest-green.svg)

AI-powered mathematical conjecture explorer — generate candidate hypotheses via Claude, auto-formalize them in Lean 4, attempt automated proofs, search for counterexamples, and log every experiment as a reproducible Git snapshot.

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
│  │ ComplexityRouter │  Scores formalizability + proof difficulty     │
│  │                  │  Routes: quick_tactics / claude_standard /     │
│  │                  │          extended_thinking / human_review      │
│  └────────┬─────────┘                                                │
│           │                                                          │
│           ▼                                                          │
│  ┌──────────────────┐                                                │
│  │ NoveltyChecker   │  Jaccard similarity deduplication              │
│  │                  │  Rejects near-duplicate conjectures            │
│  └────────┬─────────┘                                                │
│           │ novel conjecture                                         │
│           ▼                                                          │
│  ┌──────────────────┐                                                │
│  │ ConjectureGen    │  Claude API + arXiv + Mathlib4 RAG context     │
│  └────────┬─────────┘                                                │
│           │ natural language statement                               │
│           ▼                                                          │
│  ┌──────────────────┐                                                │
│  │   Formalizer     │  Claude → Lean 4 (Mathlib4 RAG-assisted)       │
│  │                  │  lake build validation                         │
│  │                  │  Repair loop: compiler errors fed back to      │
│  │                  │  Claude for up to N retries                    │
│  └────────┬─────────┘                                                │
│           │ valid Lean 4 source                                      │
│           ▼                                                          │
│  ┌──────────────────┐                                                │
│  │    Verifier      │  Races 7 tactics: decide / norm_num / ring /   │
│  │                  │  omega / simp_all / aesop / tauto              │
│  │                  │  + Claude tactic proof (extended thinking      │
│  │                  │    for hard conjectures)                       │
│  │                  │  lake build validation on every attempt        │
│  └────────┬─────────┘                                                │
│           │                                                          │
│     ┌─────┴──────┐                                                   │
│   proved      not proved                                             │
│                   │                                                  │
│                   ▼                                                  │
│          ┌──────────────────┐                                        │
│          │ CounterexSearch  │  Two independent methods in parallel:  │
│          │                  │  1. LLM-based (Claude)                 │
│          │                  │  2. Symbolic/sympy brute-force         │
│          └────────┬─────────┘                                        │
│                   │ unrefuted (not proved, not disproved)            │
│                   ▼                                                  │
│  ┌──────────────────┐                                                │
│  │ SnapshotManager  │  Git commit to `experiments` branch            │
│  │                  │  experiment.json + .lean files                 │
│  └──────────────────┘                                                │
│                                                                      │
│  FastAPI ←→ Celery workers ←→ Next.js                                │
│  (SSE live streaming, interactive Lean editor, lineage graph)        │
└──────────────────────────────────────────────────────────────────────┘
```

## Quickstart

```bash
# 1. Clone
git clone https://github.com/MohammedAlkindi/Germinal.git
cd Germinal

# 2. Configure
cp .env.example .env
# Edit .env — set ANTHROPIC_API_KEY at minimum

# 3. Launch
docker-compose up --build
```

- API: http://localhost:8000/docs
- Frontend: http://localhost:3000

## Module Breakdown

| Module | Location | Responsibility |
|--------|----------|----------------|
| Conjecture Generator | `src/conjecture_generator.py` | Claude + arXiv context + Mathlib4 RAG → structured conjecture JSON |
| Complexity Router | `src/complexity.py` | Scores formalizability/difficulty; routes to quick_tactics / claude_standard / extended_thinking / human_review |
| Novelty Checker | `src/novelty.py` | Jaccard similarity filter — rejects near-duplicate conjectures before they enter the pipeline |
| Formalizer | `src/formalizer.py` | Claude → Lean 4; `lake build` validation; repair loop feeds compiler errors back for up to N retries |
| Verifier | `src/verifier.py` | Races 7 automation tactics against Claude tactic proofs; only counts success if `lake build` passes |
| Counterexample Finder | `src/counterexample.py` | Two independent methods: LLM-based (Claude) + symbolic/sympy brute-force; `search_dual()` runs both |
| arXiv Client | `src/arxiv_client.py` | Fetches recent paper abstracts to ground conjecture generation in current literature |
| Mathlib4 RAG | `src/mathlib_rag.py` | Curated Mathlib4 declaration index; injects relevant lemma signatures into formalization prompts |
| Lean Sandbox | `src/lean_sandbox.py` | Persistent Lean 4 + Mathlib4 environment; all `lake build` calls go through here |
| Snapshot Manager | `src/snapshot.py` | Commits each experiment to the `experiments` Git branch; preserves active branch via symbolic_ref swap |
| API | `api/` | FastAPI: async jobs via Celery (sync fallback if Redis unavailable), SSE streaming |
| Frontend | `frontend/` | Next.js + Tailwind: pipeline UI, experiment table, interactive Lean editor, lineage view, command palette |

## What "unrefuted" means

When a conjecture is neither proved nor disproved, Germinal labels it **unrefuted** — not "promising" or "likely true". Two independent counterexample methods (LLM + symbolic) both failing to find a disproof is a stronger signal than one, but it is still absence-of-disproof, not a proof. The status reflects that.

## API Reference

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/v1/generate` | Generate N conjectures for a domain |
| `POST` | `/api/v1/formalize` | Translate a conjecture to Lean 4 |
| `POST` | `/api/v1/verify` | Attempt automated proof |
| `POST` | `/api/v1/pipeline` | Full generate→formalize→verify→snapshot run |
| `GET` | `/api/v1/experiments` | List all experiments |
| `GET` | `/api/v1/experiments/{id}` | Full detail for one experiment |

Interactive docs at `http://localhost:8000/docs`.

## How Reproducibility Works

Every pipeline run writes to `experiments/<uuid>/`:

```
experiments/
└── <uuid>/
    ├── experiment.json   # full metadata snapshot
    ├── conjecture.txt    # natural-language statement
    ├── conjecture.lean   # Lean 4 formalization
    └── proof.lean        # completed proof (if found)
```

Each experiment is committed to the `experiments` Git branch with:
- author: `Germinal <germinal@localhost>`
- message: `experiment(<id>): <ISO timestamp>`

To replay any experiment:

```bash
git checkout experiments
cat experiments/<uuid>/experiment.json
lean --run experiments/<uuid>/proof.lean
```

## Development (without Docker)

```bash
# Backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # fill in ANTHROPIC_API_KEY
uvicorn api.main:app --reload

# Frontend
cd frontend
npm install
npm run dev
```

Lean 4 must be installed via [elan](https://github.com/leanprover/elan):

```bash
curl -sSf https://raw.githubusercontent.com/leanprover/elan/master/elan-init.sh | sh
```

## Linting

```bash
ruff check src/ api/
ruff format --check src/ api/
```

## License

MIT — see [LICENSE](LICENSE).
