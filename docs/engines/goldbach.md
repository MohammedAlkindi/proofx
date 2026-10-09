# GoldbachX

GoldbachX contains prime sieving, partition enumeration, and structural filters
for Goldbach-style searches.

It does not prove Goldbach's conjecture. It checks bounded candidates and ranks
families that look sparse under the configured scoring assumptions.

## Conjecture

Every even integer `n >= 4` can be written as the sum of two primes.

No counterexample is known. ProofX should report only the finite ranges and
candidates it actually evaluates.

## Module Map

| Module | Purpose |
| --- | --- |
| `SieveEngine/` | Prime generation with the sieve of Eratosthenes. |
| `PartitionEnumerator/` | Counts prime pairs `(p, q)` with `p + q = n`. |
| `AlgebraicExtensions/` | Residue filters and structural prechecks. |
| `SequenceGenerator/` | Candidate-family generation. |
| `GoldbachReasoner/` | Heuristic symbolic explanations. |
| `MetaVariant/` | Experimental variant generation. |

## Partition Counting

For an even `n`, GoldbachX counts:

```text
G(n) = |{(p, q) : p + q = n, p <= q, p and q prime}|
```

The direct algorithm:

1. Build or receive primes up to `n`.
2. Iterate primes `p <= n / 2`.
3. Count `p` when `n - p` is also prime.

The implementation details matter. If a result is used as evidence, record the
prime source, upper bound, and command.

## Hardy-Littlewood Deficit

The search uses the Hardy-Littlewood prediction as a ranking baseline:

```text
predicted_G(n) =
  C2 * product_{p | n, p >= 3} ((p - 1) / (p - 2)) * n / (log n)^2
```

The deficit score is:

```text
deficit(n) = 1 - G(n) / predicted_G(n)
```

Interpretation:

| Deficit | Meaning |
| --- | --- |
| Near 0 | Observed count is close to prediction. |
| Positive and large | Observed count is lower than prediction. |
| 1.0 | `G(n) = 0`; potential counterexample requiring independent review. |

The prediction is asymptotic. A deficit is not a probability. This is the
unordered-pair convention; the ordered-pair asymptotic has twice this leading
constant. See Borwein, Choi, Martin and Samuels,
[definition of R(N) and Conjecture 3.3](https://personal.math.ubc.ca/~gerg/papers/downloads/PWCRGC.pdf).
The diagonal pair contributes only once to the exact count. The leading-term
approximation is especially crude for small inputs.

Earlier ProofX scores used the ordered constant against unordered counts and
incorrectly retained factors of two in the odd-prime correction. Scores from
that implementation are not comparable to `goldbach.unordered.v2`. New rows
record this score version and the complete sieve bound. A candidate beyond the
sieve bound is rejected; a missing prime outside the sieve is never evidence
of a missing partition.

## Sparse Families

The ranker spends attention on families expected to have fewer partitions:

| Family | Reason |
| --- | --- |
| Powers of two | No odd prime-factor boost in the Euler product. |
| `2p` for large prime `p` | Minimal odd-prime boost. |
| `n == 2 mod 30` | Avoids factors 3 and 5. |
| `n == 2 mod 6` | Avoids factor 3. |

These families are useful for search prioritization. They do not imply a
counterexample exists.

## Symbolic Reasoner

`SymbolicGoldbachReasoner.py` is a rule-based explanation layer. Treat its
output as a sketch or diagnostic, not as a formal proof.

## Browser Demo

The public Goldbach demo enumerates prime pairs for small browser-safe values.
It is educational and interactive. It should not be presented as evidence for
large bounds.

## Commands

```bash
# Directed near-miss search
python -m codebase.cli falsify --budget 500 --seed 42 --target goldbach

# Save a ledger
python -m codebase.cli falsify \
    --budget 500 \
    --seed 42 \
    --target goldbach \
    --save-ledger results/goldbach.jsonl
```

## Reporting Standard

Good:

```text
This run found no Goldbach counterexample within its evaluated candidates.
The listed rows had the largest partition deficits under the configured score.
```

Avoid:

```text
GoldbachX verifies Goldbach across huge ranges.
```
