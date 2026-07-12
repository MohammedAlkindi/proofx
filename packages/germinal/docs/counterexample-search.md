# Counterexample Search

When automated proof fails, `src/counterexample.py`'s `search_ensemble()` runs three independent counterexample-search methods concurrently. This document describes each method, the local verification step, Wolfram caching, and the ensemble result structure.

## Why three independent methods

Each method has different failure modes. Claude may share biases with the formalization model. SymPy can only operate on bounded integer domains. Wolfram Alpha may have no applicable knowledge pod for a given statement. Running all three independently means that no single blind spot blocks the ensemble: any one method finding a locally verified counterexample is sufficient, and the results of all three are preserved for inspection.

Three methods failing to find a counterexample is stronger evidence than one failing, but it is still absence-of-disproof, not proof. The `unrefuted` status reflects this.

---

## Method 1: Claude reasoning (`CounterexampleFinder`)

Asks Claude to reason about the conjecture and find a concrete counterexample.

**Prompt**: the system prompt instructs the model to think carefully, check whether the conjecture is likely true or false, and — if it can find a counterexample — provide it explicitly with a step-by-step verification that the candidate satisfies all conditions while violating the conclusion. The system block is cached (`cache_control: ephemeral`).

**Output schema** (JSON):
```json
{
  "found": true | false,
  "counterexample": "concrete description or null",
  "reasoning": "the model's reasoning process"
}
```

**Retry behavior**: rate limit and connection errors trigger exponential-backoff retries (up to 4 attempts, 2–60 second wait). Other errors are caught and returned as `found=false` with the error message in `reasoning`.

**Scope**: no structural restrictions — Claude can reason about any conjecture type, including those outside SymPy's scope.

---

## Method 2: SymPy bounded enumeration (`SymbolicCounterexampleFinder`)

Brute-force enumeration over finite integer domains using SymPy, independent of any LLM.

### Applicable conjecture types

The symbolic checker is applicable only to conjectures of the form:

> "For all [integers/natural numbers/positive integers/...] `n`, `<expr>` is `<property>`"

where:
- The quantifier is detected by the regex pattern `for (all|every|any|each) [qualifier] (integer[s]|natural number[s]) <var>`.
- `<expr>` is a single-variable arithmetic expression containing `<var>` that SymPy can parse.
- `<property>` is one of: **divisible by N**, **even**, **odd**, **prime**, **perfect square**.

For multi-variable claims, infinite algebraic structures, claims like "is continuous" or "converges," or expressions SymPy cannot parse, the method returns `applicable=False` and does not attempt a search. This is explicit, not silent.

### Domains checked

| Quantifier type | Domain |
|----------------|--------|
| Natural/positive/non-negative integers | [0, 200] (201 values) |
| All integers (no qualifier) | [−100, 100] (201 values) |

"No counterexample found in this domain" is not a mathematical proof. It means no counterexample exists in this bounded sample.

### Expression normalization

Before parsing, the checker:
1. Replaces `^` with `**` (Python exponentiation).
2. Inserts `*` between digit–variable adjacencies (e.g., `2n` → `2*n`).
3. Parses with SymPy's `parse_expr` using `standard_transformations + implicit_multiplication_application`.

If parsing fails, the method returns `applicable=False` with the parse error.

### Output

```python
{
    "method": "symbolic",
    "applicable": bool,         # False if out-of-scope
    "found": bool,
    "counterexample": str | None,  # e.g., "n = 3: expression = 9, which is NOT prime"
    "reasoning": str,
}
```

---

## Method 3: Wolfram Alpha CAS (`WolframCounterexampleFinder`)

Queries Wolfram Alpha with a reformulated "is this statement false?" question. This method is independent of both Claude and local SymPy — different knowledge base, different reasoning engine.

### Prerequisite

`WOLFRAM_APP_ID` must be set in `.env`. If it is empty, this method returns `applicable=False` immediately and does not make any network call.

### Query construction

```
Is this mathematical statement false? If false, give a concrete counterexample [in <subfield>]: <conjecture>
```

### Response parsing

Pod texts are scanned for:
- Explicit counterexample language: "counterexample", "counter-example", "is false", "does not hold", "violates"
- Plain yes/no answers to the falsity question
- Absence of negating phrases: "no counterexample", "statement is true"

Ambiguous responses (no clear yes/no, no counterexample-bearing pod) are returned as `applicable=False` with the raw pod text preserved in `reasoning`.

### Response caching

Wolfram responses are cached as JSON files to avoid redundant API calls:

- **Location**: `.cache/wolfram/<sha256_hash>.json`
- **Cache key**: SHA-256 of `{conjecture_hash}:{query_string}`
- **TTL**: `WOLFRAM_CACHE_TTL_SECONDS` (default: 86400 seconds = 24 hours)
- **Format**: `{"created_at": <unix_timestamp>, "value": <pod_texts>}`

On a cache hit within the TTL, the Wolfram API is not called. On a miss or expired entry, the API is queried and the result is written to cache.

---

## Local candidate verification (`LocalCounterexampleVerifier`)

Every candidate returned by any method is tested locally before being accepted. Unverified candidates are **rejected** — their counterexample value is set to `None`, `found` is set to `False`, and the rejection reason is appended to `reasoning`.

### Verification procedure

1. Extract a single-variable integer assignment from the candidate text using the regex `\b(?P<var>[a-z])\s*=\s*(?P<value>-?\d+)\b`.
2. Parse the conjecture to identify the variable name, domain, expression, and claim type (same parser as `SymbolicCounterexampleFinder`).
3. Evaluate the expression at the candidate value using SymPy.
4. Check whether the result violates the claim.

If any step fails (no assignment found, expression unparseable, variable mismatch, value outside domain, evaluation error, or result satisfies the claim rather than violating it), the candidate is rejected.

This verifier is conservative: it rejects candidates it cannot positively confirm. For claim types outside the symbolic checker's supported set, it cannot verify and rejects accordingly.

---

## Ensemble execution

All three methods run concurrently via `concurrent.futures.ThreadPoolExecutor` with a shared 15-second global deadline. Individual methods that exceed the deadline are cancelled and their result is recorded as `timed_out=True, found=False`.

```python
result = search_ensemble(conjecture, subfield, settings)
```

### Return structure

```python
{
    "found": bool,               # True if any method found a verified counterexample
    "counterexample": str | None,  # from the first method that found one
    "reasoning": str,            # combined summary
    "llm_result": MethodResult,
    "symbolic_result": MethodResult,
    "wolfram_result": MethodResult,
    "methods_attempted": int,    # always 3
    "methods_applicable": int,   # methods where applicable=True
    "methods_found_counterexample": int,
    "consensus": str,            # see below
    "method_disagreement": {
        "claude_found": bool,
        "sympy_found": bool,
        "wolfram_found": bool,
    },
}
```

### Consensus values

| Consensus | Meaning |
|-----------|---------|
| `counterexample_found` | At least one method returned a locally verified counterexample |
| `unrefuted` | All methods ran without errors and none found a counterexample |
| `partial_failure` | At least one method timed out or raised an error; result is incomplete |

### Method disagreement

`method_disagreement` records each method's `found` value independently. When methods disagree (one found a counterexample, another did not), this is logged at INFO level. Disagreement does not block the ensemble result — if any method finds a verified counterexample, `found=True`.

---

## `search_dual()` backward-compatibility wrapper

`search_dual(conjecture, subfield, settings)` is an alias for `search_ensemble()`. It exists to avoid breaking callers from before the ensemble was introduced. New code should call `search_ensemble()` directly.

---

## Status semantics

| Outcome | Status label |
|---------|-------------|
| A locally verified counterexample found | `counterexample_found` |
| No verified counterexample from any method; no errors | `unrefuted` |
| No verified counterexample; at least one method failed or timed out | `partial_failure` (recorded in `consensus`; top-level `found=False`) |

`unrefuted` means the system could not disprove the conjecture with its current methods. It does not mean the conjecture is true, promising, or worth further investment. It is an epistemic state, not a result.
