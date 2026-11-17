# ProofX Collatz: next steps (November 2026)

Ranked by expected value per unit of work. The evidence for each claim is in
`2026-11-literature-review.md`. "Not already done" means not found in the
sources listed there.

## 1. Run PX-COL-004: successive-halving prefix screening, prospectively (recommended)

**Question.** Does multi-stage screening beat the single-stage odd-count policy
in charged-transition yield on windows nobody has looked at?

**Design.**

* Freeze two policies:
  * Baseline A: odd count, h = 32, 4x pool.
  * Candidate B: successive halving. Screen 8q proposals for 16 steps, keep 4q
    by odd count, extend to 32, keep 2q, extend to 64, keep q.
  * Random tie-breaking inside k levels for both, from a seeded stream.
* Score with tie-fair credit: inputs strictly above the stratum threshold count
  1, and tied inputs share the remaining slots equally. Keep the label-based
  score as a secondary column for continuity with PX-COL-002.
* Use 24 or more windows of 100,000, placed by a seeded draw before any
  computation. Draw 6 or more per octave at 2^25, 2^29, 2^33 and 2^37. Keep the
  16 x 6,250 strata and q = 64 per stratum.
* Treat the window as the unit of analysis. Primary endpoint: the B/A ratio of
  pooled tie-fair hits per charged transition, per window. Success is B > A in
  at least 18 of 24 windows (one-sided sign test, p about 0.011) and a median
  ratio above 1.05. Report every window.
* Commit the freeze, hashes and window list before generating labels, as in
  PX-COL-002.

**Why it is not already done.** No source ranks or screens inputs by short
prefix statistics (ledger rows 4, 14-17, 20-23). Successive halving is a
standard bandit and hyperparameter method (row 27), but it has not been applied
here. PX-COL-002 compared only single-stage policies.

**What would matter.** Post hoc, B gained 15-20% over A in all six known windows
(tie-fair yield 1.51-1.65 against 1.32-1.43). If that holds prospectively, the
result is a real methodological improvement with a clear mechanism: R^2 rises
from about 0.2 at h = 32 to about 0.4 at h = 64, and halving pays for the longer
prefix only on survivors. A null result is also informative, because it would
show the six-window gain was window-specific.

**Cost.** The labels need tau for 2.4 million inputs near 2^37. That takes minutes
with the existing exact evaluator. No new mathematics is needed.

## 2. Publish a correction to PX-COL-002 (cheap, do first)

Add a tie-fair reanalysis to the preprint and the experiment page. It should
say that 39.5% of targets are tie-broken by input size, that ascending
selection's yield advantage mostly disappears (1.666 and 1.610 become 1.136 and
1.072), and that the odd-count advantage over growth is about half the
published size. Keep the original tables.

**Why.** The paper's conclusion points readers at "local structure exposed by
ascending selection". That pointer is mostly an artifact. Correcting it before
anyone builds on it protects the paper's credibility, which rests on careful
claims.

## 3. Test the model-vs-data enrichment gap (small research question)

The random-parity model predicts odd-count enrichment of 1.90-2.01 over uniform.
Observed is 2.28-2.47. The model also overstates the spread of tau. Measure the
gap across the 24 PX-COL-004 windows, in the same run.

**Why it is not already done.** The stochastic-model papers compare means and
extreme constants with data (rows 5-7). I found no comparison of conditional
remaining-time variance given a prefix.

**What would matter.** A stable gap would be a concrete, citable deviation of real
orbits from the independent-parity model at the scale of 32-64 steps. It could
be explained by the Syracuse residue bias mod 3 (Tao, row 11) or by the forced
even step after 3n+1. A gap that disappears across windows closes the question.

## 4. Lean: sharp bound and the parity-determination lemma (hygiene)

Prove in core Lean:

* c(sigma) <= 2^(m+1-k) (3^k - 2^k) for k >= 1.
* The ordinary-map form of Terras Thm 1.2: if n1 = n2 mod 2^(h+1), the first h
  parities agree.

**Why it is not already done.** rwst/Collatz-Map-Basics proves the shortcut-map
versions with Mathlib (row 24). No ordinary-map sharp bound was found.

**What would matter.** Modestly. It makes `Trajectory.lean` state the facts the
experiments rely on. It is not research novelty, and the docs should not present
it as such.

## 5. Withdrawn: PX-COL-003 as written

Do not run it. Stratifying 6,250 consecutive integers mod 2^32 does nothing, the
sampler's default modulus (2^8) disagrees with the protocol, and the motivating
"clumping" theorem is false. The protocol file is kept with a withdrawal notice
so the history stays readable. If residue structure is to be tested, the
meaningful version is a complete residue system mod 2^r for r <= 8 per stratum,
as a secondary arm inside PX-COL-004, with a stated reason to expect a gain.
