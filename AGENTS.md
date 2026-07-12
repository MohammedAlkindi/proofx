# AGENTS.md

Agent operating rules for this repo. Commit style and branch naming follow `~/Github/CLAUDE.md`; this file covers what's specific to ProofX.

## Scope

- This file governs the ProofX root: `codebase/`, `tests/`, `docs/`, `src/`, `scripts/`, `assets/`.
- `packages/germinal/` is out of scope here — it's a distinct project synced via `git subtree` from its own repo/remote (`germinal-remote`) and has its own `CLAUDE.md`. Don't make unrelated edits there while working on ProofX-root tasks; keep the two diffs separable.
- `findings/` and `legacy/` are gitignored (business/pitch material, large historical archive) — don't re-track, move, or delete their contents without being asked.

## Branch policy

- `main` is the default branch; don't commit directly to it for anything multi-commit or reviewable — follow the standard `<type>/<short-kebab-description>` naming (`claude/` prefix for agent-created branches) from `~/Github/CLAUDE.md`.
- One logical change per commit. Don't bundle a `codebase/` engine change with a `src/` site change, or a ProofX-root change with a `packages/germinal/` change.

## What requires confirmation

- Pushing to `origin` (MohammedAlkindi/ProofX) or `germinal-remote` (MohammedAlkindi/Germinal) — always ask first, this repo has two remotes and it's easy to push the wrong tree to the wrong one.
- Any `git subtree pull`/`push` touching `packages/germinal/` — this rewrites/merges history from a separate upstream; get explicit sign-off before running it.
- Changing `pyproject.toml`'s coverage gate (`--cov-fail-under=60`) or ruff/mypy config — these are the project's correctness floor.
- Editing `vercel.json` security headers or rewrites — this is the live public deployment config.
- Deleting or moving anything under `findings/`, `legacy/`, or `assets/`.
- Force-push, `git reset --hard`, or any destructive git operation — never without explicit ask, per global standards.

## Before calling work done

- Install/check the dev toolchain with `pip install -r requirements.txt -r requirements-dev.txt` when a clean environment is needed.
- Run `pytest`, `ruff check .`, `ruff format --check .`, and `mypy codebase` — all four, not just tests. Never commit without them passing.
- If you touched `docs/engines/*.md` scoring derivations, verify the corresponding code still asserts weights sum to 1.0.
- If you touched the static site (`src/`), run `./scripts/validate-links.sh`.
- If you touched `ProofX/` (root Lean layer), run `lake build` and grep for `sorry|admit|axiom|unsafe` per `docs/lean4.md` before considering it done. If `lake`/`elan` are not on PATH locally, say so explicitly and rely on CI (`.github/workflows/lean.yml`) instead of claiming it builds.
- Use `scripts/cleanup.ps1 -Deep` on Windows or `./scripts/cleanup.sh --deep` on Unix shells to remove local caches, coverage outputs, and old root-level scratch folders.
