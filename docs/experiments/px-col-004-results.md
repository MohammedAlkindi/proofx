# PX-COL-004 results: successive-halving prefix screening

Run 16 November 2026 under the protocol frozen at
`13716c5d099bb291a6959a67986ed2eaa1d62585`
([protocol](px-col-004-protocol.md)). The test output is in
`src/experiments/px-col-004/test/`, with the independent verifier log in
`verification.log`. Selections were hashed before any total stopping time was
computed: SHA-256 `f05e206bd34fb938a35e16b5c7794e9a99cc30441bb26bb42a8c175bd44d4162`.

## Primary endpoint: met

At B = 1,024, halving gave higher pooled tie-fair hits per charged transition
than odd32 in **24 of 24** test windows. The median ratio was **1.196** (range
1.086 to 1.297). The protocol required at least 18 of 24 and a median above 1.05.
Under no difference, 24 of 24 has one-sided sign-test probability 2^-24, about
6e-8.

By octave the median ratio is 1.197 at 2^25, 1.196 at 2^29, 1.184 at 2^33 and
1.202 at 2^37, with no trend in size. At B = 256, halving also wins 24 of 24
windows (median 1.183, range 1.086 to 1.353).

## Yield relative to the exact uniform expectation (B = 1,024, tie-fair)

| Window | uniform | odd32 | odd64 | halving | halving/odd32 |
| --- | ---: | ---: | ---: | ---: | ---: |
| 34,819,912 | 1.021 | 1.447 | 1.467 | 1.798 | 1.243 |
| 39,457,193 | 1.021 | 1.434 | 1.336 | 1.709 | 1.192 |
| 53,809,489 | 1.025 | 1.468 | 1.415 | 1.673 | 1.140 |
| 54,014,348 | 0.983 | 1.131 | 1.140 | 1.291 | 1.142 |
| 62,643,253 | 0.940 | 1.518 | 1.476 | 1.944 | 1.281 |
| 62,744,734 | 0.998 | 1.407 | 1.404 | 1.692 | 1.203 |
| 590,600,569 | 1.021 | 1.396 | 1.391 | 1.673 | 1.199 |
| 593,160,738 | 0.981 | 1.289 | 1.282 | 1.454 | 1.128 |
| 601,815,510 | 1.035 | 1.175 | 1.146 | 1.402 | 1.193 |
| 892,576,941 | 1.016 | 1.460 | 1.437 | 1.807 | 1.237 |
| 1,012,220,341 | 0.995 | 1.440 | 1.355 | 1.608 | 1.116 |
| 1,044,174,870 | 0.998 | 1.479 | 1.424 | 1.819 | 1.230 |
| 11,149,233,036 | 1.003 | 1.348 | 1.307 | 1.538 | 1.141 |
| 11,256,643,349 | 0.978 | 1.356 | 1.294 | 1.473 | 1.086 |
| 12,979,451,047 | 0.985 | 1.408 | 1.378 | 1.689 | 1.200 |
| 14,439,106,049 | 1.023 | 1.402 | 1.422 | 1.741 | 1.243 |
| 15,481,112,647 | 1.010 | 1.682 | 1.712 | 2.167 | 1.288 |
| 16,306,335,695 | 0.972 | 1.392 | 1.343 | 1.625 | 1.167 |
| 200,268,643,960 | 0.977 | 1.649 | 1.677 | 2.091 | 1.268 |
| 203,877,166,097 | 1.044 | 1.533 | 1.453 | 1.857 | 1.212 |
| 216,493,145,490 | 0.992 | 1.134 | 1.092 | 1.352 | 1.192 |
| 218,358,967,719 | 1.003 | 1.252 | 1.276 | 1.449 | 1.157 |
| 237,912,112,582 | 1.004 | 1.328 | 1.323 | 1.516 | 1.141 |
| 248,092,096,785 | 1.027 | 1.607 | 1.743 | 2.084 | 1.297 |

Medians across windows: uniform 1.003, odd32 1.407, odd64 1.384, halving 1.681.
The median mean hits per window are 51.35, 121.27, 157.51 and 195.74, against
51.28 expected for uniform.

## Secondary results

* **Staging, not prefix length, explains the gain.** A single 64-step prefix
  (odd64) beat odd32 in only 7 of 24 windows. It sees more of each orbit but
  pays 64 steps for every proposal.
* **Halving spends more and gains more.** Against odd32, its median charged
  work is 1.35 times higher and its median hits 1.63 times higher.
* **Label credit agrees.** With the PX-COL-002 smaller-input rule, the medians
  are halving 1.660, odd32 1.414 and uniform 1.006.
* **The windows vary widely.** odd32 ranges from 1.131 to 1.682. This matches
  the window heterogeneity noted in the literature review and is why the window
  is the unit of inference.

## Checks

`verify.py` imports nothing from the study code. It re-drew the 24 windows and
all pools, recomputed every prefix step by step, recomputed 2,400,000 total
stopping times by batched halving, and matched all 6,144 selections, run
records and summary aggregates exactly. The run with `--corrupt`, which perturbs
one stopping time, was rejected as required. Seven semantic tests pass,
including the overflow path for large iterates.

## What this does and does not show

* It shows that, for this finite retrieval task with every ordinary transition
  charged, staged prefix screening beats single-stage odd-count screening on 24
  prespecified windows from 3.5e7 to 2.5e11.
* The mechanism is the one the review predicted. Longer prefixes predict better
  (R^2 about 0.2 at 32 steps, about 0.4 at 64), and halving pays for the long
  prefix only on survivors. Successive halving itself is a standard
  elimination method for best-arm identification and hyperparameter search
  (Karnin, Koren and Somekh, ICML 2013, PMLR 28:1238-1246; Jamieson and Talwalkar,
  arXiv:1502.07943). The new part is the application and the measurement.
* Step counts do not price bit width, sorting or interpreter overhead. A
  record-search implementation may find that the checks cost more than they
  save; the cuda-collatz author reported this for exact record pruning. No
  wall-time claim is made.
* Labels are fixed, so the 32 seeds measure algorithmic variation only. No
  statement is made about inputs outside the windows, about record delays, or
  about the conjecture.
* The schedule (8x pool; 16, 32 and 64 steps) was chosen post hoc on the
  PX-COL-002 windows from three candidates. Other schedules were not tested
  prospectively.
