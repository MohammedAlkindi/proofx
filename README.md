# ProofX

![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)
![Python](https://img.shields.io/badge/Python-3.13-blue.svg)
![Lean](https://img.shields.io/badge/Lean-4-blueviolet.svg)
![Tests](https://img.shields.io/badge/Tests-pytest-green.svg)
![Coverage gate](https://img.shields.io/badge/coverage%20gate-60%25-brightgreen.svg)
![Lint](https://img.shields.io/badge/Lint-ruff-orange.svg)
![Types](https://img.shields.io/badge/Types-mypy-blue.svg)
![Reproducible](https://img.shields.io/badge/RNG-seeded%20%26%20deterministic-informational.svg)
![Deploy](https://img.shields.io/badge/Deploy-Vercel-black.svg?logo=vercel&logoColor=white)

ProofX is a research toolkit for directed counterexample search in discrete and
analytic number theory. It currently focuses on Collatz, Goldbach, and Riemann
Hypothesis-adjacent numerical experiments. The project is deliberately framed as
search and evidence tooling, not as a proof system.

The central rule is simple: when a run finds no counterexample, the result is
reported as **unrefuted at this budget**. That does not mean true, verified,
validated, likely, or proved. It only means that the configured search did not
find a disproof.

## Current Scope

ProofX contains three kinds of material:

| Area | Status | Role |
| --- | --- | --- |
| `codebase/` | Active Python research toolkit | Runs directed searches, computes features, writes ledgers, and exposes the CLI. |
| `ProofX/` | Root Lean 4 certificate layer | Checks small bounded artifacts and status semantics. |
| `docs/` | Maintainer and research documentation | Describes assumptions, algorithms, run semantics, and limitations. |
| `public/` + `src/` | Static research site | Presents the project, demos, and result summaries without changing the engine behavior. |
| `packages/germinal/` | Vendored sibling project | Separate Lean 4 conjecture-generation and proof-attempt system, synced by subtree. |

`packages/germinal/` has its own README and operating rules. Keep ProofX-root
changes separate from Germinal changes unless a task explicitly crosses that
boundary.

## What ProofX Does Not Claim

ProofX does not prove Collatz, Goldbach, the Riemann Hypothesis, or any related
open conjecture.

ProofX does not certify mathematical truth from empirical runs.

ProofX does not treat high near-miss scores as probabilities of falsehood. A
score ranks candidates inside this toolkit's search strategy; it is not a
calibrated belief.

ProofX does not make benchmark claims unless a run ledger, command, hardware
context, and version information are provided.

## Directed Search

Uniform scans are useful for bounded verification, but they are not what this
repository is mainly testing. ProofX asks a narrower question: if a
counterexample existed, what structural signals might make a candidate worth
checking first?

Current strategies:

| Engine | Search idea | Output |
| --- | --- | --- |
| Collatz | Expand from known high stopping-time anchors and score trajectories by growth, parity, entropy, and excursion features. | Candidate ledger with convergence diagnostics and near-miss scores. |
| Goldbach | Search structurally sparse even numbers whose observed partition count is low relative to Hardy-Littlewood prediction. | Candidate ledger with partition counts, deficits, and residue-family metadata. |
| Riemann | Compute numerical signals from zeta zeros and Keiper-Li coefficients. | Numerical diagnostics only; not a proof of RH or a certified zero computation. |

The shared FalsificationEngine writes every evaluated candidate to JSONL. The
ledger is the audit trail: it records candidate, conjecture label, strategy,
feature vector, score, details, timestamp, and RNG seed.

## Architecture

```text
ProofX/
  codebase/
    FalsificationEngine/     Directed search orchestration and ledgers
    CollatzX/                Collatz sequence features and related experiments
    GoldbachX/               Prime sieve, partitions, and structural filters
    ReimannX/                Riemann-related numerical experiments
    CrossEngineAnalysis/     Correlation tooling for ledgers
    cli.py                   Unified CLI
  ProofX/                    Root Lean 4 certificate definitions
  ProofX.lean                Root Lean import file
  lakefile.lean              Root Lake package
  lake-manifest.json         Lake package manifest
  lean-toolchain             Pinned Lean toolchain
  tests/                     Root pytest suite for ProofX codebase
  docs/                      Project documentation
  public/                    Static site output
  src/                       Static site source fragments, CSS, and scripts
  assets/                    Site and paper assets
  packages/germinal/         Separate vendored Lean 4 project
```

See [docs/architecture.md](docs/architecture.md) for the fuller maintainer map.

Local caches, virtual environments, generated run outputs, and old root-level
scratch folders are intentionally ignored. On Windows, run
`scripts/cleanup.ps1 -Deep`; on Unix shells, run `./scripts/cleanup.sh --deep`.
Do not move the old Germinal tree back to the root: it belongs under
`packages/germinal/`.

## Lean 4 Boundary

The root Lean package checks small bounded certificates. Current examples cover
one Collatz starting value reaching `1` within a finite fuel bound and one
Goldbach witness pair for a concrete even number. These artifacts make finite
claims kernel-checkable; they do not prove open conjectures.

Build the Lean layer with:

```bash
lake build
```

See [docs/lean4.md](docs/lean4.md) for the formal boundary and acceptance bar.

## Near-Miss Scoring

Both falsifiers reduce a candidate to a ranking score in `[0, 1]`.

```text
Collatz:  near_miss = 0.70 * risk_score + 0.30 * excursion_bonus
Goldbach: near_miss = 0.85 * deficit    + 0.15 * structural_hardness
```

These are ranking functions, not proof certificates. They decide what the
search inspects first and what the report surfaces. If a weight changes, the
corresponding derivation in [docs/engines/falsification.md](docs/engines/falsification.md)
must change with it.

## Reproducibility

Engine randomness flows through a seeded NumPy generator. Child seeds are
derived deterministically so that a target-specific run can be compared with a
combined run at the same master seed.

```python
rng_master = np.random.default_rng(seed)
collatz_seed, goldbach_seed = rng_master.integers(0, 2**31, size=2)
```

Every evaluated candidate can be written to JSONL:

```json
{
  "candidate": 12345,
  "conjecture": "collatz",
  "strategy": "inverse_tree_beam_search",
  "features": {
    "lyapunov_exponent": 0.0412,
    "hurst_exponent": 0.5831,
    "parity_ratio": 0.5714
  },
  "near_miss_score": 0.2847,
  "rng_seed": 1234567890
}
```

Reproducibility depends on the Python version, dependency versions, platform
math libraries, and code revision. Keep the command, seed, dependency lockfile,
and ledger together when publishing results.

## Quickstart

```bash
git clone https://github.com/MohammedAlkindi/ProofX.git
cd ProofX

python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

python -m codebase.cli falsify --budget 200 --seed 42 --target both
```

## Research Workflow

```bash
# 1. Run a directed search and save the full ledger.
python -m codebase.cli falsify \
    --budget 2000 --seed 42 --target both \
    --save-ledger results/ledger.jsonl \
    --output-json results/summary.json

# 2. Inspect the ledger in the static viewer.
open public/ledger-viewer.html

# 3. Hand-label entries, then fit a calibrator.
python -m codebase.cli calibrate fit \
    --ledger results/ledger_labelled.jsonl \
    --method isotonic \
    --output results/calibrator.pkl

# 4. Annotate a ledger with calibrated scores.
python -m codebase.cli calibrate annotate \
    --ledger results/ledger.jsonl \
    --calibrator results/calibrator.pkl

# 5. Compare near-miss neighborhoods across engines.
python -m codebase.cli correlate \
    --collatz results/collatz.jsonl \
    --goldbach results/goldbach.jsonl \
    --radius 200
```

## Testing

The repository policy expects these checks before a commit:

```bash
pytest
ruff check .
ruff format --check .
mypy codebase
lake build
./scripts/validate-links.sh
```

The badges describe the intended quality floor, not a mathematical guarantee.
If a check is failing, note that explicitly in any published result or release.

## Documentation

| Doc | Covers |
| --- | --- |
| [docs/architecture.md](docs/architecture.md) | Project boundaries, data flow, ledgers, and status semantics. |
| [docs/research-standards.md](docs/research-standards.md) | Language standards for claims, evidence, and public copy. |
| [docs/lean4.md](docs/lean4.md) | Root Lean package scope, certificate rules, and acceptance bar. |
| [docs/engines/falsification.md](docs/engines/falsification.md) | Shared scoring, ledger schema, and directed-search assumptions. |
| [docs/engines/collatz.md](docs/engines/collatz.md) | CollatzX model, features, and limits. |
| [docs/engines/goldbach.md](docs/engines/goldbach.md) | GoldbachX sieve, partition, and deficit logic. |
| [docs/deployment.md](docs/deployment.md) | Static site deployment and validation notes. |
| [docs/content-strategy.md](docs/content-strategy.md) | Tone and site-copy guidance. |
| [docs/mvp.md](docs/mvp.md) | Minimum viable tooling bar (CI, packaging, local checks) and current gap status. |

## License

MIT. See [LICENSE](LICENSE).
