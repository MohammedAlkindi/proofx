# PX-COL-004: successive-halving prefix screening (protocol)

Frozen before any test label is computed. The freeze commit is the commit that
adds this file together with `src/experiments/px-col-004/` (study, verifier,
tests and development results). The test run must pass that commit's SHA as
`--freeze-commit`.

## Question

Does staged prefix screening retrieve upper-tail total stopping times at a
higher rate per charged ordinary transition than the single-stage odd-count
policy from PX-COL-002, on windows nobody has inspected?

Origin of the hypothesis: a post-hoc scan of the PX-COL-002 windows
(`scripts/research/col002_reanalysis/policies.py`; see
`docs/research/2026-11-literature-review.md`, Section 3.5). It is exploratory
evidence only. No prior source found ranks or screens inputs by prefix
statistics. Record searches use exact cut-offs against known records instead:
Leavens and Vermeulen (1992), Lemmas 20-21, and Roosendaal's cut-off technique.

## Map and labels

* C(n) = n/2 or 3n + 1, exact integers. tau(n) counts steps to the first 1.
* Each window is 100,000 consecutive inputs in 16 strata of 6,250. Each stratum
  has 313 target slots.
* **Primary credit, tie-fair.** An input strictly above the stratum's 313th
  largest tau counts 1. Inputs equal to that value share the remaining slots
  equally. Expected uniform hits are exactly 51.28192 per window at B = 1024.
* **Secondary credit, label.** The PX-COL-002 rule: top 313 by tau, ties broken
  toward smaller input. Reported for continuity only; it favors smaller inputs.

## Windows

* **Development:** the PX-COL-002 development windows starting at 100,001,
  400,001 and 800,001.
* **Test:** 24 windows from a seeded draw (`study.test_windows()`, seed =
  first 8 bytes of SHA-256("PX-COL-004 test windows v1")). Six per octave
  [2^e, 2^(e+1)) for e = 25, 29, 33, 37. Each window lies at least 100,000 away
  from the others, from the three PX-COL-002 fresh windows, and from the 12
  exploratory windows used in the review. The draw gives these lower bounds:
  34819912, 39457193, 53809489, 54014348, 62643253, 62744734, 590600569,
  593160738, 601815510, 892576941, 1012220341, 1044174870, 11149233036,
  11256643349, 12979451047, 14439106049, 15481112647, 16306335695,
  200268643960, 203877166097, 216493145490, 218358967719, 237912112582,
  248092096785.

## Pools and policies

For each window, seed 0-31 and stratum, NumPy PCG64 with
`SeedSequence([0x50584334, phase, lower, seed, stratum])` draws 512 distinct
offsets (the pool order) and 512 uniform tie-break keys. Budgets B = 256 and
1,024 give q = B/16 selections per stratum. All policies use nested prefixes of
the same ordered pool, so comparisons are paired.

| Policy | Rule |
| --- | --- |
| uniform | First q pool entries. No screening. |
| odd32 | First 4q entries, 32-step prefix, top q by odd count. This is baseline A, the PX-COL-002 ablation but with random tie-breaking. |
| odd64 | First 4q entries, 64-step prefix, top q by odd count. Ablation: a longer prefix without staging. |
| halving | First 8q entries. 16 steps, keep 4q by odd count; extend to 32, keep 2q; extend to 64, keep q. This is candidate B. |

* Ties inside an odd-count level go to the smaller tie-break key, never to the
  smaller input.
* A prefix stops at the first 1.

## Charged work

Every input pays for the prefix steps it actually ran, at its final depth.
Selected inputs then pay tau(n) minus their prefix steps for the continuation;
prefixes are never charged twice. Uniform pays tau(n) per selected input. Steps
are ordinary transitions. Bit width, sorting and interpreter time are not
priced, and no wall-time claim is made.

## Endpoints

* **Primary.** At B = 1,024, per test window: the ratio of pooled tie-fair hits
  per pooled charged transition, halving over odd32, over 32 seeds.
* **Success.** halving > odd32 in at least 18 of 24 windows (one-sided sign test
  p = 0.0113 under no difference), and a median ratio above 1.05. Both must
  hold.
* **Secondary, descriptive.**
  * Each policy's yield relative to the exact uniform expectation, per window
    and budget.
  * The B = 256 results.
  * Label-credit results.
  * odd64 against odd32.
* The window is the unit of inference. Seeds describe algorithmic variation on
  fixed labels and carry no confidence statement about integers outside the
  windows.

## Order of operations and checks

1. Pass 1 computes 64-step prefixes for all inputs and every selection, then
   writes `selections.jsonl.gz` and its SHA-256. No tau is computed before this
   point.
2. Pass 2 computes tau, the credits, costs and the summary.
3. `verify.py` imports nothing from `study.py`. It re-draws windows and pools,
   recomputes prefixes step by step and tau by batched halving, then rechecks
   every selection, run record and aggregate exactly. With `--corrupt` it must
   reject a perturbed stopping time.
4. Every window is reported, including adverse ones. A deviation from this
   protocol is logged in the results file, never silently fixed.

## Development results (frozen with this protocol)

B = 1,024, tie-fair yield relative to uniform expectation:

| Window | uniform | odd32 | odd64 | halving | halving/odd32 |
| --- | ---: | ---: | ---: | ---: | ---: |
| 100,001 | 0.964 | 1.376 | 1.215 | 1.654 | 1.202 |
| 400,001 | 0.967 | 1.419 | 1.228 | 1.620 | 1.142 |
| 800,001 | 1.001 | 1.347 | 1.253 | 1.625 | 1.207 |

Development used windows already seen in PX-COL-002 and in the review, so it
checks the implementation, not the hypothesis.

## Scope

This is a finite selection benchmark inside verified territory. It makes no
claim about the Collatz conjecture, and no record or verification bound.
