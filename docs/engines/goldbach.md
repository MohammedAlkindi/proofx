# GoldbachX Engine

## Conjecture statement

Every even integer n ≥ 4 can be written as the sum of two primes.

Verified computationally for all even n ≤ 4 × 10¹⁸ (Oliveira e Silva et al., 2014).
No counterexample has ever been found.

---

## Module overview

| Module | Purpose |
|--------|---------|
| `AlgebraicExtensions/` | Modular arithmetic filters and residue-class pruning |
| `GoldbachReasoner/` | Symbolic reasoning over partition structure |
| `PartitionEnumerator/` | Direct enumeration of Goldbach pairs (p, q) with p + q = n |
| `SequenceGenerator/` | Generates candidate even numbers from structural families |
| `SieveEngine/` | Eratosthenes sieve and prime-set construction |

---

## SieveEngine

`SieveEngine.py` exposes `eratosthenes(limit)`, which returns a sorted list of all
primes up to `limit` in O(n log log n) time using a bitarray sieve.

The FalsificationEngine uses `_SIEVE_LIMIT = 200_000` by default.
Extend via `--sieve-limit` (once that flag is wired to the CLI).

---

## PartitionEnumerator

Counts G(n) = |{(p, q) : p + q = n, p ≤ q, p and q prime}| for a range of even n.

**Algorithm:**
1. Precompute the prime set S up to n/2 (from `eratosthenes`).
2. For each p in primes with p ≤ n/2: if (n − p) ∈ S, increment count.
3. Time per query: O(π(n/2)) ≈ O(n / (2 log n)).

---

## AlgebraicExtensions

### `composite_precheck(n)`

Fast pre-filter before running the full partition count. Uses the following heuristics:

- If n is divisible by a small prime q < 20, then n − q is either prime or
  has a known partition. The check gates on structural "warnings" that suggest
  n will have few partitions.

### `mod_class_prune(n, mod)`

Returns the residue classes r (mod `mod`) such that r and n − r are both
coprime to `mod` — a necessary condition for both to be prime (beyond 2 and 3).

Example for mod = 6:
- Primes > 3 are ≡ 1 or 5 (mod 6).
- For p + q = n, the allowed (p mod 6, q mod 6) pairs depend on n mod 6.
- n ≡ 2 (mod 6): the only allowed pair is (1 mod 6, 1 mod 6). Fewer choices.
- n ≡ 0 (mod 6): pairs (1,5) and (5,1) are both allowed. More choices.

This is why n ≡ 2 (mod 6) candidates are structurally harder: they have a
smaller allowed residue class, so fewer candidate prime pairs.

---

## Hardy-Littlewood prediction G̃(n)

The Hardy-Littlewood Conjecture B predicts the asymptotic number of Goldbach
representations:

```
G̃(n) = 2 · C₂ · ∏_{p | n, p ≥ 3} (p − 1)/(p − 2) · n / (log n)²
```

where C₂ = ∏_{p ≥ 3} p(p − 2)/(p − 1)² ≈ 0.6602 is the twin-prime constant.

**Euler product interpretation:** Each odd prime factor p of n contributes a
multiplicative boost (p − 1)/(p − 2) > 1 to the predicted partition count.
Numbers with no small odd prime factors get no boost — they sit at the minimum
of the prediction curve relative to their scale.

**Deficit score:**

```
deficit(n) = 1 − G(n) / G̃(n)
```

- deficit = 0: actual count matches prediction exactly.
- deficit = 0.9: actual is only 10 % of prediction — highly anomalous.
- deficit = 1.0: G(n) = 0 — a confirmed counterexample.

The FalsificationEngine uses this deficit as the primary near-miss score for
Goldbach candidates.

---

## Structurally sparse candidate families

The FalsificationEngine's `GoldbachFalsifier` focuses on families where G̃(n)
is minimised relative to n, ordered from sparsest to densest:

| Family | Condition | Reason for sparsity |
|--------|-----------|-------------------|
| Powers of 2 | n = 2ᵏ | No odd prime factors → Euler product = 1 (minimum) |
| 2·p (large prime) | n = 2p, p large prime | Single odd prime factor; (p−1)/(p−2) → 1 as p → ∞ |
| n ≡ 2 (mod 30) | avoids 3 and 5 | Missing boosts from p=3 (factor 2) and p=5 (factor 4/3) |
| n ≡ 2 (mod 6) | avoids 3 | Missing boost from p=3 |

---

## SymbolicGoldbachReasoner

`SymbolicGoldbachReasoner.py` provides a proof-sketch layer that tries to:

1. Identify the algebraic structure of a candidate's partition set.
2. Derive lower bounds on G(n) from known prime distribution theorems
   (e.g., Chen's theorem: every sufficiently large even n = p + q where q is
   prime or a product of two primes).
3. Flag candidates for which no lower bound can be established — these are the
   genuinely hard cases.

---

## Running GoldbachX

```bash
# Partition enumeration up to 1,000,000
python -m codebase.cli goldbach --limit 1000000

# Directed near-miss search via FalsificationEngine
python -m codebase.cli falsify --budget 500 --seed 42 --target goldbach \
    --save-ledger goldbach_ledger.jsonl

# Cross-engine analysis after running both targets
python -m codebase.cli falsify --budget 500 --seed 42 --target both \
    --save-ledger both.jsonl

# (Split ledgers by conjecture first, then):
python -m codebase.cli correlate \
    --collatz collatz.jsonl --goldbach goldbach.jsonl --radius 200
```
