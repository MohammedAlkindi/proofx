# Germinal

AI-powered mathematical conjecture explorer — generate candidate hypotheses via Claude, auto-formalize them in Lean 4, attempt automated proofs, and log every experiment as a reproducible Git snapshot.

```
┌─────────────────────────────────────────────────────────────────┐
│                        Germinal Pipeline                        │
│                                                                 │
│   Domain Input                                                  │
│       │                                                         │
│       ▼                                                         │
│  ┌──────────────────┐                                           │
│  │ ConjectureGen    │  Claude API → structured JSON             │
│  └────────┬─────────┘                                           │
│           │ natural language statement                          │
│           ▼                                                     │
│  ┌──────────────────┐                                           │
│  │   Formalizer     │  Claude API → Lean 4 code                 │
│  │                  │  lake build validation (subprocess)       │
│  └────────┬─────────┘                                           │
│           │ valid Lean 4 source                                 │
│           ▼                                                     │
│  ┌──────────────────┐                                           │
│  │    Verifier      │  Claude API → tactic proof (≤3 attempts)  │
│  │                  │  lake build validation (subprocess)       │
│  └────────┬─────────┘                                           │
│           │ proof result                                        │
│           ▼                                                     │
│  ┌──────────────────┐                                           │
│  │ SnapshotManager  │  Git commit to `experiments` branch       │
│  │                  │  experiment.json + .lean files            │
│  └──────────────────┘                                           │
│                                                                 │
│  FastAPI ←→ Next.js (live pipeline status, experiment table)    │
└─────────────────────────────────────────────────────────────────┘
```

## Quickstart

```bash
# 1. Clone
git clone https://github.com/MohammedAlkindi/Germinal.git
cd Germinal

# 2. Configure
cp .env.example .env
# Edit .env and set ANTHROPIC_API_KEY

# 3. Launch
docker-compose up --build
```

- API: http://localhost:8000/docs
- Frontend: http://localhost:3000

## Module Breakdown

| Module | Location | Responsibility |
|--------|----------|----------------|
| Conjecture Generator | `src/conjecture_generator.py` | Calls Claude to propose N conjectures for a domain |
| Formalizer | `src/formalizer.py` | Translates conjectures to Lean 4; validates with `lake build` |
| Verifier | `src/verifier.py` | Attempts automated tactic proofs (up to 3 rounds) |
| Snapshot Manager | `src/snapshot.py` | Commits each experiment to the `experiments` Git branch |
| API | `api/` | FastAPI: /generate, /formalize, /verify, /pipeline, /experiments |
| Frontend | `frontend/` | Next.js + Tailwind: pipeline UI, experiment table, detail view |

## API Reference

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/v1/generate` | Generate N conjectures for a domain |
| `POST` | `/api/v1/formalize` | Translate a conjecture to Lean 4 |
| `POST` | `/api/v1/verify` | Attempt automated proof |
| `POST` | `/api/v1/pipeline` | Full generate→formalize→verify run |
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

## Roadmap

- [ ] Async Celery workers for long-running Lean 4 builds
- [ ] PostgreSQL persistence for experiment metadata
- [ ] Batch generation with parallelism across conjectures
- [ ] Citation of related Mathlib4 theorems in generated Lean code
- [ ] HPC cluster job submission via SLURM adapter
- [ ] Conjecture similarity search (embedding-based deduplication)
- [ ] Public experiment registry

## License

MIT — see [LICENSE](LICENSE).
