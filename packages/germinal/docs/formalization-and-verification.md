# Formalization and Verification

This document covers the Lean 4 formalization pipeline (`src/formalizer.py`, `src/lean_sandbox.py`, `src/mathlib_rag.py`) and the automated proof search (`src/verifier.py`).

## What formalization validates — and what it does not

Formalization runs `lake build` against the generated Lean 4 code. A passing build means:

- The Lean code is syntactically valid.
- All referenced Mathlib4 declarations exist and are correctly imported.
- The statement typechecks — Lean's type system accepts it as a well-formed proposition.

A passing build does **not** mean:

- The underlying mathematical claim is true.
- The statement is provable.
- The formalization faithfully represents the intended natural-language conjecture.

A false statement with a correct Lean 4 encoding typechecks without issue. A conjecture that passes formalization and fails all proof attempts could be false, unprovable with current automation, or genuinely open. The system cannot distinguish between these cases.

---

## src/lean_sandbox.py — persistent Lean 4 environment

`LeanSandbox` wraps all `lake build` calls. The Lean 4 + Mathlib4 environment lives in `LEAN_SANDBOX_DIR` (default `.lean_sandbox`) and persists across API calls and process restarts.

**First boot**: `lake update` is run to download Mathlib4. This takes several minutes. Subsequent builds reuse the cached build artifacts.

**Build execution**: each `LeanSandbox.build(lean_code)` call:
1. Writes the Lean source to a temp file in the sandbox.
2. Runs `lake build` with a per-call timeout (`LEAN_TIMEOUT`, default 120 seconds).
3. Returns `(success: bool, output: str)`.

Never call `lake` directly outside the sandbox, and never modify `lean_sandbox.py` to skip or weaken build validation, even temporarily. Mock `LeanSandbox.build()` in tests instead.

---

## src/mathlib_rag.py — Mathlib4 declaration injection

Before generating Lean 4 code, the formalizer queries `mathlib_rag.py` for relevant Mathlib4 declarations. The module maintains a static curated index of declaration names, type signatures, and module paths.

Relevant declarations are selected based on keyword overlap with the conjecture text and injected into the formalization prompt. This gives Claude direct access to:
- Correct theorem and lemma names (e.g., `Nat.Prime`, `Int.dvd_add`)
- Import paths (e.g., `import Mathlib.Data.Nat.Prime`)
- Type signatures for common operations

Without this injection, Claude must guess Mathlib4 API details, leading to build failures on non-existent declarations. The repair loop (described below) catches many such errors, but RAG injection reduces first-attempt failure rates.

---

## src/formalizer.py — Lean 4 translation with repair loop

### Prompt structure

The formalization prompt contains:
1. Static system instructions (cached with `cache_control: ephemeral`).
2. Relevant Mathlib4 declaration signatures from `mathlib_rag.py`.
3. The natural-language conjecture.

For repair attempts, the prompt additionally includes the Lean compiler error from the previous attempt.

### Repair loop

```
Generate Lean 4 code
       ↓
  lake build
       ↓
  passes? → return lean_code (success)
       ↓ fails
  append compiler error to prompt
       ↓
  Claude retries (up to FORMALIZE_REPAIR_ATTEMPTS times, default 3)
       ↓
  exhausted → return error_log (failure, lean_code not valid)
```

The full compiler output is included in the retry prompt, not a summarized version. This gives Claude precise line numbers and error messages to work with.

### Output

`Formalizer.formalize()` returns:
```python
{
    "lean_code": str,     # final generated Lean 4 source
    "is_valid": bool,     # True only if lake build passed
    "error_log": str,     # compiler output if is_valid is False
}
```

Only `is_valid=True` results advance to the verifier. An `is_valid=False` experiment is recorded and snapshotted, but proof search is skipped.

---

## src/verifier.py — automated proof search

### Strategy routing

The `strategy` parameter (set by `ComplexityRouter`) determines how the verifier behaves:

| Strategy | Tactics used | Claude call | Extended thinking |
|----------|-------------|-------------|-------------------|
| `quick_tactics` | All 7 | No | No |
| `claude_standard` | All 7 | Yes | No |
| `extended_thinking` | All 7 | Yes | Yes |
| `human_review` | Skip | Skip | Skip |

### Phase 1: tactic racing

Seven tactics run concurrently via `asyncio.gather`:
- `decide` — decidable propositions
- `norm_num` — numerical normalization
- `ring` — ring identity proofs
- `omega` — linear arithmetic over integers and naturals
- `simp_all` — rewriting with simplification lemmas
- `aesop` — extensible proof search
- `tauto` — tautology checker

Each tactic is wrapped in a Lean `by <tactic>` block and validated by `lake build`. The first tactic to produce a clean build wins; the remaining futures are cancelled.

### Phase 2: Claude tactic proof

If no quick tactic succeeds, the verifier calls Claude to generate a multi-step tactic proof. The prompt includes the Lean 4 statement and any relevant Mathlib4 lemmas.

For `extended_thinking` strategy, Claude's extended thinking mode is enabled with a configurable token budget (`THINKING_BUDGET_TOKENS`, default 10,000 tokens). Set `THINKING_BUDGET_TOKENS=0` to disable extended thinking globally.

The Claude-generated proof is validated by `lake build`. Only a passing build is counted as success.

### Output

`Verifier.verify_async()` returns:
```python
{
    "proved": bool,
    "attempts": [{"attempt": str, "lean_code": str, "error": str, "success": bool}, ...],
    "final_proof": str | None,   # Lean source of the successful proof
    "failure_reason": str | None,
}
```

### Async interface

`verify_async()` is an `async def` method that wraps synchronous Lean calls in `asyncio.to_thread()`. This keeps the FastAPI event loop unblocked during `lake build` execution.

---

## What counts as a valid proof

A conjecture is marked `proved` if and only if `lake build` returns exit code 0 on a Lean source file containing the complete proof. There is no partial credit, no "probably correct" heuristic, and no relaxation of this requirement. If `lake build` fails, the attempt is logged and the conjecture remains unproved.
