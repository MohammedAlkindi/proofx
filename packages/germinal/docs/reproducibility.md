# Reproducibility

Every Germinal pipeline run produces a self-contained, versioned snapshot committed to a dedicated Git branch. This document describes the snapshot format, the dual-persistence model, the branch safety mechanism, and how to replay any experiment.

## Snapshot format

Each experiment is stored under `experiments/<uuid>/` on the `experiments` branch:

```
experiments/
└── <uuid>/
    ├── experiment.json   # full pipeline metadata
    ├── conjecture.txt    # natural-language statement
    ├── conjecture.lean   # Lean 4 formalization
    └── proof.lean        # proof, if found (absent otherwise)
```

### experiment.json schema

The JSON file contains the complete experiment record at time of snapshot:

```json
{
  "id": "<uuid>",
  "timestamp": "<ISO 8601>",
  "domain": "<domain string>",
  "subfield": "<subfield tag>",
  "conjecture": "<natural-language statement>",
  "lean_code": "<Lean 4 source>",
  "is_valid": true | false,
  "proved": true | false,
  "final_proof": "<Lean proof source or null>",
  "model_used": "<claude model id>",
  "proof_strategy": "quick_tactics | claude_standard | extended_thinking | human_review",
  "novelty_score": 0.0–1.0,
  "duration_ms": <integer>,
  "counterexample_checked": true | false | null,
  "counterexample_found": true | false | null,
  "extra": { ... }
}
```

Fields in `extra` include per-method counterexample search results, arXiv papers used for generation, and any other pipeline metadata added by `api/tasks.py`.

---

## Git commit format

Each snapshot is committed with:

- **Author**: `Germinal <germinal@localhost>`
- **Commit message**: `experiment(<id>): <ISO 8601 timestamp>`
- **Branch**: `experiments` (configurable via `GIT_EXPERIMENTS_BRANCH`)

The `experiments` branch diverges from `main` immediately and is never merged back. It is a log, not a feature branch.

---

## Dual persistence model

Every experiment is written in two places by `api/tasks.py`:

1. **SQLAlchemy `ExperimentRow`** in the database (`src/db.py`) — queryable via the REST API (`GET /api/v1/experiments`). Supports filtering, pagination, and joins to annotations and jobs.

2. **Git snapshot** on the `experiments` branch (`src/snapshot.py`) — a complete, self-contained record that does not depend on the database being available. Enables replay, diff, and audit without running the API server.

Both writes happen atomically from the task's perspective: the task writes to the DB, then commits the snapshot. If the snapshot commit fails, the DB record exists but the Git snapshot is absent. The inverse (snapshot without DB) does not happen because the DB write happens first.

Any schema change must update both write paths. The Git snapshot format is not generated from the SQLAlchemy model — it must be updated manually in `src/snapshot.py`.

---

## Branch safety under concurrent workers

Celery runs with `--concurrency=2`, so two tasks can call `SnapshotManager.save()` concurrently. Writing to a Git branch requires:

1. Switching the active branch to `experiments` (via `git symbolic-ref HEAD refs/heads/experiments`).
2. Staging files and committing.
3. Switching HEAD back to the original branch.

If two tasks interleave at step 1–3, they can corrupt each other's commits or leave HEAD in an inconsistent state.

`SnapshotManager._commit_to_branch` is protected by a module-level `threading.Lock()`:

```python
_COMMIT_LOCK = threading.Lock()

def _commit_to_branch(self, ...) -> None:
    with _COMMIT_LOCK:
        # symbolic_ref swap, stage, commit, swap back
```

The lock ensures that only one thread at a time executes the symbolic-ref swap sequence. Do not remove or bypass this lock. If you need to add concurrency beyond Celery workers, the lock must be replaced with a distributed lock (e.g., Redis-based).

---

## Replaying an experiment

### From the experiments branch

```bash
# Switch to the snapshots branch (read-only; do not commit on this branch)
git fetch origin experiments
git checkout experiments

# Inspect a specific experiment
cat experiments/<uuid>/experiment.json

# Run the Lean proof (requires Lean 4 installed via elan)
lean --run experiments/<uuid>/proof.lean

# Diff two experiments
diff experiments/<uuid-a>/conjecture.lean experiments/<uuid-b>/conjecture.lean
```

### From the API

```bash
# Get full experiment detail
curl http://localhost:8000/api/v1/experiments/<uuid>

# Export as Lean source
curl http://localhost:8000/api/v1/experiments/<uuid>/export?format=lean

# Export as LaTeX
curl http://localhost:8000/api/v1/experiments/<uuid>/export?format=latex
```

---

## Lean environment

The Lean 4 + Mathlib4 version used for a given snapshot is determined by the `leanprover/lean4:stable` Docker image and the `lean-toolchain` file in the sandbox. To exactly reproduce a build:

1. Use the same Docker image version as was used at experiment time (recorded in `experiment.json`'s `extra` field if present).
2. Check out the `experiments` branch and run `lake build` in the sandbox directory on the `.lean` files.

Mathlib4 version is pinned by the `lake-manifest.json` in the sandbox. The sandbox is not committed to the `experiments` branch — you must have a working Lean environment to replay proofs.

---

## What reproducibility guarantees

- The natural-language statement, Lean 4 formalization, and proof source (if found) are preserved verbatim.
- The full pipeline metadata (model used, strategy, duration, counterexample results) is preserved in `experiment.json`.
- The Git commit timestamp and author are authoritative for when the experiment ran.

What is **not** guaranteed:
- Re-running the pipeline on the same conjecture will produce the same Lean code or proof — Claude outputs are non-deterministic.
- The Lean build will succeed on a different Lean/Mathlib4 version than was used at snapshot time.
