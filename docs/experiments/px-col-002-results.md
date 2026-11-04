# PX-COL-002: finite-prefix selection with charged screening

Completed 3 November 2026. [Project](https://proofx.org),
[complete source/data bundle](../../src/experiments/px-col-002/bundle.zip),
[reproduction instructions](../../src/experiments/px-col-002/README.txt),
[machine-readable results](../../src/experiments/px-col-002/summary.json), and
[independent check](../../src/experiments/px-col-002/verification.json).

The policy screens four uniformly proposed inputs per complete evaluation,
computes at most 32 ordinary Collatz transitions, and ranks the exact endpoint /
starting-value ratio within size strata. It reuses selected prefixes when
continuing to the first 1. The policy has no known-hard anchors, suffix cache or
reference outcomes. The original anchor-expansion policy is a different method;
its earlier negative result is retained in the preprint.

## Protocol and fresh evaluation

The development procedure and fresh intervals were committed at research
revision `a00703e`. A pre-outcome sampler clarification and implementation were
committed at `7c6cb19`. Development used only three existing 100,000-input
intervals below one million, with 16 seeds and prefix lengths 8, 16 and 32.
The pooled charged-transition yields were 501.68, 517.96 and 522.08 targets per
million transitions, selecting length 32. Parameters, source hashes and all
development results were pushed at `52ebace40ca20ca27446172c1dab6ae443f3cd51`
before fresh computation. The frozen files are included in the public bundle.

The fresh intervals are inclusive R1 = 2,097,152–2,197,151, R2 =
33,554,432–33,654,431 and R3 = 536,870,912–536,970,911. Each has 16 consecutive
strata of 6,250 inputs and 313 top-total-stopping-time targets per stratum,
5,008 targets total. Ties favor smaller inputs. Each policy has identical size
quotas and the same ordered proposal pools for seeds 0–31 and budgets
64/256/1024. Smaller budgets use nested pool prefixes. Target labels are
constructed after all policies have written their selections. This is prospective
range transfer inside known verification territory; disjoint starting inputs can
share trajectory suffixes.

## Results at 1,024 complete evaluations

Mean target counts over 32 seeds; exact matched-uniform expected count is
51.28192 in each range. All controls are included in the archive.

| Policy | R1 | R2 | R3 |
| --- | ---: | ---: | ---: |
| Prefix growth | 121.594 | 112.500 | 107.531 |
| Prefix odd count | 130.344 | 125.625 | 117.344 |
| Prefix survival | 50.656 | 52.375 | 50.375 |
| Old input-bit priority | 62.812 | 76.219 | 70.625 |
| Ascending pool | 64.000 | 88.062 | 83.281 |
| Descending pool | 37.969 | 27.688 | 28.938 |
| Uniform pool | 50.656 | 52.375 | 50.375 |

All screening transitions, including discarded proposals, plus selected
continuations are charged. Prefixes are reused rather than counted twice.
The primary endpoint is pooled hits / pooled transitions, compared with the
uniform ratio of exact expected hits to exact expected transitions. This is
not an expectation of per-run efficiency ratios.

| Policy's charged-transition rate / uniform expected rate | R1 | R2 | R3 |
| --- | ---: | ---: | ---: |
| Prefix growth | 1.264 | 1.262 | 1.251 |
| Prefix odd count | 1.353 | 1.397 | 1.361 |
| Prefix survival | 0.601 | 0.661 | 0.660 |
| Old input-bit priority | 1.185 | 1.392 | 1.293 |
| Ascending pool | 1.243 | 1.666 | 1.610 |
| Descending pool | 0.753 | 0.546 | 0.578 |
| Uniform pool (realized) | 0.987 | 1.016 | 0.984 |

The predeclared criterion, exceeding uniform expectation in all three intervals
at budget 1,024, was met. This does not make growth ranking the best method:
the simpler prefix odd-count ablation is better in all three ranges and
ascending selection has higher transition yield in two. Selecting the odd-count
variant on these results would require a new prospective evaluation before
claiming its transfer performance as a newly selected method.

Median local end-to-end times for growth were 53.12/49.55/97.00 ms, compared
with 19.88/19.95/38.26 ms for uniform. Every timing includes proposal generation,
screening where applicable, sorting and actual uncached continuation. Reference
construction, labels, verification and file output are outside policy timing.
Timing is a single-process local measurement on an Intel Core Ultra 9 285H,
Windows, Python 3.13.13 and NumPy 2.4.6; method order rotates by seed/block/budget.
No general wall-time speedup is established. Exact step counts do not price
integer bit width, fraction comparisons, sampling or Python overhead.

## Checks and interpretation

The independent checker imports no generator/selector/analysis modules. It uses
batched-halving arithmetic and a cross-product ratio comparator to recount all
300,000 fresh reference values and 903,168 selected records in 2,016 runs, plus
the 300,000 development references and 196,608 development selected records.
All sampler outputs, quotas, ranks, tie rules, labels, costs and aggregates
passed, including deliberately corrupted-stopping-time rejection. Timing
aggregation is recounted; elapsed time itself is not independently recreated.
Eight semantic tests check prefix reuse, first arrival, exact ranking,
label/suffix isolation, deterministic sampling and input validation.

These are finite, conditional algorithmic results, not confidence statements
about infinite integer dynamics. No new Collatz theorem, record verification
bound, external peer review or universally best policy is claimed. The related
literature already studies parity vectors, long stopping times and statistical
prediction; the added contribution is the frozen, cost-accounted comparison and
complete inspectable evidence.
