# PX-COL-003: prospective residue-stratified odd-count selection with charged screening

## 1. Scientific Objective and Evidence Boundary

PX-COL-003 is a prospective range-transfer experiment testing the effect of residue-stratified proposal distributions on prefix-based Collatz trajectory selection. It builds directly on the empirical findings of PX-COL-002 and the theoretical derivations in `docs/research/stage1_odd_count_drift_derivation.md`.

In PX-COL-002, the simpler prefix odd-count ablation (ranking proposals purely descending by the integer count $k$ of odd steps in a 32-step prefix) strictly outperformed ratio-based growth ranking ($R_h(n) = C^h(n)/n$) across all three fresh geometric ranges below $10^9$. 

Under Lagarias (1985, Theorem 2.1), the parity sequence $\vec{\sigma} \in \{0, 1\}^h$ of the first $h$ Collatz transitions is completely determined by $n \pmod{2^h}$. When proposals are drawn uniformly over an interval without modular balancing, proposals frequently clump into identical residue classes modulo $2^h$, inducing redundant evaluation of identical parity branches.

PX-COL-003 evaluates whether **residue stratification modulo $2^{32}$** suppresses proposal clumping and improves the efficiency of odd-count selection when evaluating large numbers above $10^{10}$.

This is an algorithmic selection benchmark on finite integer intervals, not a proof of the Collatz conjecture or a claim of infinite orbital convergence.

---

## 2. Experimental Intervals and Strata Partitioning

All evaluations use exact integer arithmetic with the standard Collatz transition function:
$$C(n) = \begin{cases} n / 2 & \text{if } n \equiv 0 \pmod 2 \\ 3n + 1 & \text{if } n \equiv 1 \pmod 2 \end{cases}$$
stopping upon first arrival at 1. Fuel bound is 250,000 transitions.

Three disjoint geometric test ranges are evaluated, selected without inspecting stopping-time outcomes:
* **Range 1 (R1)**: $[10,000,000,000, 10,000,099,999]$ (base 10 magnitude $10^{10}$, span 100,000)
* **Range 2 (R2)**: $[34,359,738,368, 34,359,838,367]$ (binary magnitude $2^{35}$, span 100,000)
* **Range 3 (R3)**: $[1,099,511,627,776, 1,099,511,727,775]$ (binary magnitude $2^{40}$, span 100,000)

### Stratification
Each interval of 100,000 inputs is partitioned into exactly 16 contiguous, non-overlapping strata of 6,250 inputs each:
$$\text{Stratum } s \in \{0, \dots, 15\}: \quad [\text{lower} + 6250 \cdot s, \; \text{lower} + 6250 \cdot (s + 1) - 1]$$

Within each stratum, the ground-truth target set consists of the 313 largest total stopping times (ties broken favoring smaller input values). This establishes:
* 313 targets per stratum
* $313 \times 16 = 5,008$ targets per interval
* Target labels are constructed strictly after policy selections are serialized and hashed.

---

## 3. Policy Specification and Quotas

For each selection budget $B \in \{64, 256, 1024\}$, each stratum receives a quota of $q = B / 16$ complete evaluations:
* $B = 64 \implies q = 4$
* $B = 256 \implies q = 16$
* $B = 1024 \implies q = 64$

An oversampling factor of 4 is fixed. For each stratum, a candidate proposal pool of size $4q$ distinct integers is drawn. Smaller budgets use nested prefixes of the $B=1024$ pool. 32 deterministic seeds ($0 \dots 31$) are evaluated.

### Sampler Specification
Seeds flow through NumPy `SeedSequence([0x50584333, phase_id, lower, seed, stratum])` using PCG64.
1. **Residue-Stratified Pool (New)**: Draws proposals while enforcing maximal residue diversity modulo $2^{32}$. When drawing $4q$ candidates from a stratum $[L, U]$, candidates are assigned distinct congruence classes modulo $2^{32}$ by rejecting proposals that collide with an already-sampled residue within the pool.
2. **Uniform Pool (Control)**: Draws uniform integer offsets from $[L, U]$ rejecting direct duplicates, exactly as in PX-COL-002.

### Policies Compared
1. **Odd-Count (Residue-Stratified)**: Propose from residue-stratified pool. Run prefix screening of length $h=32$. Rank proposals descending by integer odd-step count $k$, breaking ties by smaller input. Select top $q$ proposals per stratum.
2. **Odd-Count (Uniform Control)**: Propose from uniform pool. Run prefix screening of length $h=32$. Rank descending by odd-step count $k$, breaking ties by smaller input.
3. **Prefix Growth (Residue-Stratified)**: Propose from residue-stratified pool. Run prefix screening of length $h=32$. Rank descending by exact rational ratio $C^{32}(n)/n$, breaking ties by smaller input.
4. **Prefix Growth (Uniform Control)**: Propose from uniform pool. Rank descending by exact rational ratio $C^{32}(n)/n$, breaking ties by smaller input.
5. **Matched Uniform Expectation**: Realized uniform selection taking the first $q$ pool entries without prefix computation, compared against the exact theoretical expectation $\mathbb{E}[\text{hits}] = 313 \times (q / 6250) = 51.28192$ at $B=1024$.

---

## 4. Transition Accounting and Endpoints

### Cost Accounting
All integer transitions are charged:
* Every proposal evaluated during prefix screening incurs $h = 32$ transitions (or fewer if reaching 1 early). This includes discarded proposals that are not selected.
* Selected proposals reuse their 32-step prefix endpoints; continuations are charged from step 32 to 1. Prefixes are never charged twice.
* Total charged transitions = $\sum \text{screening steps} + \sum \text{selected continuation steps}$.

### Endpoints
* **Primary Endpoint**: At $B=1024$, the pooled hit rate per charged transition:
  $$\text{Yield Ratio} = \frac{\sum \text{Hits}_{\text{policy}} / \sum \text{Transitions}_{\text{policy}}}{\mathbb{E}[\text{Hits}_{\text{uniform}}] / \mathbb{E}[\text{Transitions}_{\text{uniform}}]}$$
* **Predeclared Success Criterion**: The residue-stratified odd-count policy must exceed the matched uniform baseline expectation in all three fresh test ranges ($R1, R2, R3$) and exceed the uniform-proposal odd-count policy in mean charged-transition yield.

---

## 5. Verification Gate and Reproducibility

1. Code and protocol hashes are committed before running fresh evaluations.
2. An independent checker script (`scripts/verify_col003_protocol.py`) verifies:
   - Interval non-overlap and stratum coverage.
   - Deterministic seed reproduction.
   - Exact tie-breaking and rank monotonicity.
   - Transition conservation and cost accounting.
3. All adverse comparisons and failure modes are retained and published in the final bundle.
