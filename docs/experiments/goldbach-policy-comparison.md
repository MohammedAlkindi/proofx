# GB-001: bounded Goldbach policy comparison

## Question and scope

With the same candidate budget, which selection policy finds more of the
smallest observed-to-asymptotic partition ratios in a fixed finite domain?
This protocol compares selection policies, not primality algorithms. It does
not test an ability to find a counterexample to Goldbach, and does not establish
that a policy will generalize to larger inputs.

The initial configuration is all even integers from 4 through 10,000, inclusive;
64 distinct evaluations per policy; and seeds 0, 1, and 2. The implementation
accepts even upper bounds through 20,000 so the complete reference and an
independent recount remain practical. There is no early stopping on a good score.

## Definitions

`G(n)` counts prime pairs `(p, q)` with `p <= q` and `p + q = n`, including equal
primes. The reference uses a complete sieve through the upper domain bound.
For each even `n`, compute the leading unordered Hardy–Littlewood approximation:

```text
H(n) = C2 * n / log(n)^2 * product((p-1)/(p-2), over distinct odd primes dividing n)
C2 = 0.6601618158
ratio(n) = G(n) / H(n)
```

The primary metric is recall of the domain's bottom 5% of ratios, including all
ties at the boundary. The exhaustive reference establishes this set only for
evaluation. Policies cannot read the reference or its threshold. Report each
seed separately, along with minimum and median ratio, median candidate, and
number of zero-partition candidates. The asymptotic expression has substantial
finite-size error; a small ratio is a property of this chosen metric.

## Policies and fairness

- **Directed:** existing ProofX sparse-family generator: powers of two, twice
  upper-quartile sieve primes where in range, residue 2 modulo 30, then residue
  2 modulo 6. If these families exhaust the domain, fill the remaining budget
  with a seeded shuffle of unvisited even integers.
- **Uniform:** sample without replacement from the same domain with NumPy's
  seeded generator.
- **Sequential:** inspect the smallest even integers first. It is deterministic;
  repeated seed rows are the same control, not independent replicates.

Every policy receives the same bound and unique-candidate budget. Selection is
followed by the same exact partition counter and ratio calculation. The directed
policy is a bounded adaptation of the search generator; it does not run the
full feature-scoring pipeline. Its twice-prime family may be empty for a given
sieve/domain combination. This is part of the method being measured.

The manifest records shared sieve time and exhaustive-reference time separately.
Per-run elapsed time includes selection, exact counts, and ratios; excludes
imports, sieve setup, the reference, and output I/O. Policy order is fixed.
These timings are diagnostics, not statistically controlled speed comparisons.

## Run and inspect

Install the pinned Python dependencies in a virtual environment as described
in the repository README. Then run these single-line, cross-shell commands:

```sh
python -m codebase.cli benchmark goldbach --max-n 10000 --budget 64 --seeds 0 1 2 --output-dir results/goldbach-comparison
python -m codebase.cli benchmark verify results/goldbach-comparison
```

The output directory must be new. It contains `manifest.json`, the complete
`reference.jsonl`, and a ledger per policy/seed. All numeric outcomes are stored,
including negative results. The manifest records the command, source revision,
tracked-tree state, source hashes, interpreter, dependencies, platform, and
SHA-256 hashes of the data files. Each JSONL row contains the candidate, exact
count, smallest witness pair, expected count, and ratio.

Verification checks the complete artifact set, checksums, domain, unique budgets,
summaries, and every reference count and witness using independent trial-division
primality. It also recalculates the asymptotic expression. It does not authenticate
the author, prove timing measurements, or certify that a claimed policy produced
its ledger. Re-run the experiment and compare artifact hashes for that last check.
Different timestamps, environment metadata, and elapsed times are expected;
candidate-ledger hashes should match under the recorded implementation and RNG.

## Interpretation and next experiments

Report the result even if uniform or sequential selection wins. Three seeds
are a small descriptive comparison; do not attach significance or superiority
claims. Candidate sizes differ across policies, so inspect median candidate and
repeat on prespecified size bands before drawing conclusions about structure.
The evaluation metric resembles the search heuristic, which favors alignment
with that heuristic rather than independent scientific discovery.

Useful follow-ups are held-out size intervals, more prespecified seeds,
family ablations, alternative asymptotic approximations, and an independently
implemented checker. A change in scoring or counting convention requires a new
artifact and explicit comparison, not replacing the old sample.

## References

- Borwein, Choi, Martin and Samuels, [Polynomials whose reducibility is related
  to the Goldbach conjecture](https://personal.math.ubc.ca/~gerg/papers/downloads/PWCRGC.pdf),
  definition of the ordered count and Conjecture 3.3. ProofX counts unordered pairs.
- Oliveira e Silva, [Goldbach conjecture verification](https://sweet.ua.pt/tos/goldbach.html),
  for an established computation project and its published data. GB-001 is a
  small methodological exercise and is not an extension of those bounds.

See [Goldbach counting and score conventions](../engines/goldbach.md) and
[research standards](../research-standards.md).
