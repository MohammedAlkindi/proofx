# GB-002: structural selection under matched size allocation

Status: prospective protocol. Commit this document and the machine-readable
protocol before computing GB-002 outcomes. Git history is the protocol record;
this is not registration with an independent registry. Amendments require a new
version, a reason, and a clear label distinguishing exploratory analyses.

## Question and scope

Does a priority policy based on four proposed structural families retrieve more
low observed-to-asymptotic Goldbach partition ratios than uniform or ascending
selection when all policies receive identical budgets within narrow size bands?
Which families contribute to any difference?

The finite evaluation intervals are [10002,12000], [15002,17000], and
[18002,20000], restricted to even integers. Each contains 1,000 inputs. They are
disjoint from GB-001's exhaustive reference. The middle interval includes 16384
so the power-of-two rule has support. Prior legacy searches may have visited
individual inputs here: these are not claimed to be globally unseen data.
No GB-002 outcomes have been used to choose these intervals.

This is a bounded computational-method study. It establishes neither a new
Goldbach verification bound nor progress toward a counterexample. Results do
not generalize automatically to larger integers, other objectives, or adaptive
searches.

## Frozen design

The canonical configuration is `codebase/protocols/gb-002-v1.json`, distributed
with the Python package. Its digest is recorded in every bundle.

- Split each interval into ten contiguous strata, each containing 100 evens.
- Budgets are 20, 50, and 100 distinct inputs, giving quotas 2, 5, and 10 per
  stratum. Every policy has the same exact quotas.
- Run 2,048 replicates with seeds 0 through 2047; no optional stopping or seed
  removal. A replicate is the uncertainty unit, not an individual integer.
- In each stratum, derive a PCG64DXSM stream from the seed, interval endpoints,
  and stratum lower endpoint, using NumPy's executable construction
  `Generator(PCG64DXSM(SeedSequence([seed, lower, upper, stratum_lower]))).random(N)`.
  Assign keys in increasing integer order. Draw one uniform key per input. Reuse those keys
  for all randomized policies (common random numbers).
- Select by stable ordering; break key ties by integer value. Smaller budgets
  take prefixes within each stratum of the same ranking.

Policies:

1. `uniform`: increasing random key, sampling without replacement.
2. `ascending`: increasing integer; deterministic, with no replicate uncertainty.
3. `priority`: earliest membership in the ordered families power of two, twice a
   prime, congruent to 2 modulo 30, congruent to 2 modulo 6; then the random key.
   Inputs in no family form a final uniform fallback group.
4. Four ablations, each removing exactly one family from that same ordering.

Test primality of n/2 for each input n in the stratum. This policy is an
explicitly versioned adaptation, not the GB-001 generator. The legacy generator
uses the upper quartile of its whole sieve for twice-prime candidates, which can
leave none within the search bound. Quotas and the corrected eligibility rule
change the algorithm; conclusions apply to GB-002's policy only. Overlapping
families and priority starvation can make an ablation inactive. Report family
support and identical-selection rates rather than treating that as missing data.

## Reference and endpoint

Count unordered pairs p <= q with p+q=n, including equal primes, using an exact
sieve. Retain the smallest witness. Use

`H(n) = C2 * n/log(n)^2 * product((p-1)/(p-2), odd prime p dividing n)`,

with the fixed GB-001 approximation `C2=0.6601618158`. For each stratum separately,
define targets as inputs at or below the fifth order statistic of G(n)/H(n),
including boundary ties. Publish the threshold and actual target count.
The oracle supplies evaluation labels only; selection receives integers, prime
membership, and random keys, never counts, ratios, or target labels.

Primary endpoint: hits divided by the total target count of the interval.
Store complete selections for the largest quota and derive every smaller budget
from those prefixes. Repeated candidates across budgets or replicates do not
constitute additional independent observations.

This evaluates selection quality under a fixed number of reference queries.
The runner may look up precomputed exact counts. It does not benchmark elapsed
search time, memory efficiency, or end-to-end computational cost.

## Analysis fixed before outcomes

For each interval and budget, report every policy's exact expected recall and
variance under ideal uniformly random within-bucket orderings, plus observed
replicate mean and standard deviation. Compute expectations with rational
arithmetic and publish numerator and denominator. Report differences of priority
against uniform, ascending, and each of four ablations: 54 contrasts in total.
Keep interval results separate; do not choose a best interval or seed. These
exact finite-domain quantities are primary; no significance test is needed for
their signs. Matching allocations across 100-even strata does not eliminate
possible residual size effects within a stratum.

Every policy partitions a stratum into ordered buckets. Fully selected buckets
contribute deterministic hits. Only the boundary bucket is partially selected.
For boundary size N, K targets and remaining quota q, its expected hits are
q*K/N and variance q*(K/N)*(1-K/N)*(N-q)/(N-1), with zero variance for
deterministic selection. Sum independent strata and divide by the total target
count (or its square for variance). Uniform has one bucket; ascending has
singleton buckets. Validate all policies by exhaustive tiny-population enumeration.

Simulation is an implementation cross-check. Compare each exact contrast with
the following simultaneous Monte Carlo interval; a mismatch must be investigated
and reported, not hidden by changing seeds. Ideal random orderings and finite
pseudorandom keys are distinct: key ties use the declared deterministic rule.

For each contrast, let d_s be the paired recall difference, in [-1,1], with mean
m and unbiased sample variance v. Set L=log(4*M/alpha), M=54, alpha=0.05, and

`radius = sqrt(2*v*L/R) + 14*L/(3*(R-1))`.

Clip [m-radius,m+radius] to [-1,1]. This applies
[Maurer and Pontil (2009), Theorem 4](https://www.cs.mcgill.ca/~colt2009/papers/012.pdf)
to (d+1)/2, with a union bound over both tails and all contrasts. Under independent
replicate sampling, simultaneous coverage is at least 95%. Intervals can be
conservative; crossing zero is inconclusive, not evidence of equivalence.
Pseudorandom streams approximate the independent draws assumed by the bound.
These intervals quantify Monte Carlo uncertainty conditional on the fixed
integers, not uncertainty about other domains or mathematical conjectures.

Call an exact contrast positive, zero, or negative by its rational value. A claim
of higher expected recall than both baselines throughout this design requires
strictly positive exact contrasts against both in every interval/budget cell.
Report all failures of that criterion. Monte Carlo intervals quantify simulation
error only, not uncertainty in the exactly computed expectations. Ablations measure
effects within this ordering, not intrinsic causal importance of a family.

## Reproduction and falsification requirements

- Publish protocol, exhaustive reference, every replicate's selections, analysis,
  source snapshot, dependency versions, and file hashes, including negative runs.
- Independently reconstruct primes by trial division and recount every pair and
  witness; recompute targets, budgets, summaries, and uncertainty from raw data.
- Replay each policy from its recorded seeds to detect fabricated selections.
  Policy replay shares the specified policy implementation; the exact-count
  cross-check does not share the engine sieve.
- Check corruption even when an attacker updates file checksums: altered counts,
  missing or duplicate replicates, wrong quotas, and altered analysis must fail.
- Use hand-computable populations for the statistics and endpoint tests, and
  negative controls for absent/overlapping families.
- A reproduction compares scientific artifact hashes. Timestamps, source revision,
  dependency metadata, and archive bytes may differ and must remain visible.
- A hash establishes artifact identity, not authorship, peer review, or a theorem.

Any exploratory extensions follow a separate protocol version and cannot replace
this complete result bundle.
