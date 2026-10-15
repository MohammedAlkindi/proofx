# GB-002 results

The protocol was committed at `63bedbc` before outcomes. The complete bundle
contains 3,000 reference inputs, 43,008 policy-replicate records, 63 exact
policy/budget expectations and variances, and 54 contrasts. Each interval has
50 target inputs. Every result below refers to the frozen finite domains and
ideal uniformly random ordering within policy buckets.

## Expected recall at budget 100

| Interval | Uniform | Ascending | Full priority | Without twice-prime |
| --- | ---: | ---: | ---: | ---: |
| 10002–12000 | 10.00% | 8.00% | 12.90% | 33.04% |
| 15002–17000 | 10.00% | 12.00% | 20.64% | 34.46% |
| 18002–20000 | 10.00% | 12.00% | 20.68% | 28.71% |

Full priority exceeds both baselines in all nine interval/budget cells.
Removing twice-prime improves all nine cells too. This is evidence against
that rule for this objective and ordering. It motivates a new prospective
evaluation of the reduced policy; choosing it here is model selection on the
evaluation data, not fresh validation.

Removing powers of two changes expectations only in the middle interval,
where removal increases recall by 0.002 at every budget. Removing modulo 6
changes no selections: earlier priority buckets already fill the quotas.
Removing modulo 30 has mixed effects. All ablations and exact rational values
are published in `src/experiments/gb-002/analysis.json`.

## Checks and interpretation

All 54 paired empirical-Bernstein intervals contain the exact contrast.
These intervals quantify simulation error under the ideal sampling model;
exact expected performance has no Monte Carlo estimation error. A fixed PRNG
seed is reproducible, not a literal random draw with guaranteed coverage.

The verifier checks hashes, every reference input, every seed's selection, and
every analysis field. A separate arithmetic implementation uses trial division,
integer pair enumeration, factorization, and inclusion-indicator covariance.
An independent scratch implementation also recounted all inputs, all rational
moments and contrasts, and all simulation means, deviations and intervals from
the raw ledger; it found no discrepancies. This is internal adversarial
verification, not external peer review.

Size allocation is matched across 100-even strata. Residual within-stratum size
effects remain possible. The reference uses a floating-point asymptotic
approximation to define labels; rational expectations are exact conditional on
those labels. The study measures selection quality per reference query, not
elapsed-time efficiency, scalability, or progress on Goldbach's conjecture.

The bundled source snapshot records the implementation used. Its manifest
records the source revision and source hashes. Floating diagnostic fields use
14 significant digits so reproductions are byte-stable across supported
platform math libraries; exact expectations remain stored as rational numbers.
The protocol's prospective commit remains independently inspectable in Git.

## Reproduction

From a checkout, install the core package in a virtual environment and run:

```sh
pip install .
python -m codebase.experiments reproduce GB-002 results/reproduction --bundle src/experiments/gb-002/bundle.zip
```

The command checks the registry's archive digest, verifies the extracted data,
runs the installed implementation, and compares the four scientific artifact
files. It never executes downloaded source. Source snapshots and environment
metadata remain available in both directories and are excluded from that
comparison. A mismatch retains both copies and fails visibly. Omitting
`--bundle` fetches the published artifact. Use a new output directory each time.

The next useful experiment is an independently specified range and budget
regime for the reduced policy, with a separate runtime measurement if efficiency
is the question. These outcomes must not be relabeled as that future study.
