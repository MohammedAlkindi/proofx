# ProofX Collatz work against the literature (November 2026)

Written 16 November 2026. It covers PX-COL-001/002 as published in the preprint
("Finite-prefix selection of long Collatz trajectories with ProofX", Drive copy
dated 10 November 2026), `ProofX/Trajectory.lean`, the PX-COL-003 protocol and
sampler from commit `8358686`, and the untracked note
`docs/research/stage1_odd_count_drift_derivation.md`.

Each source below is marked by how much of it was actually opened:

* **Full**: the text was read, at least the sections cited.
* **Part**: some pages or sections were read; the unread part is named.
* **Abstract**: only the abstract or a publisher summary was read.
* **Not accessed**: paywall or bot wall. Anything said about it is secondhand,
  and the secondhand source is named.

Nothing marked Not accessed is used as a primary citation for a claim.

Two map conventions matter throughout. The ordinary map is
C(n) = n/2 or 3n+1. The shortcut map is T(n) = n/2 or (3n+1)/2. Almost every
classical theorem is stated for T. ProofX measures C. A C-prefix of h steps
with m halvings is a T-prefix of length m, or m+1 when the last C-step is odd.

## 1. Source ledger

| # | Source | Opened | Key results, stated precisely | Bearing on ProofX |
| --- | --- | --- | --- | --- |
| 1 | R. Terras, "A stopping time problem on the positive integers", Acta Arith. 30 (1976) 241-252. [scan](https://matwbn.icm.edu.pl/ksiazki/aa/aa30/aa3034.pdf) | Part (pp. 241-248) | Thm 1.1: T^k n = lambda_k n + rho_k, with lambda_k = 3^{S_k}/2^k. Thm 1.2 and Cor 1.3: n and m share the length-k parity vector iff n = m mod 2^k, and all 2^k vectors occur. Thms 1.9 to 1.17: the density F(k) of {stopping time >= k} exists and tends to 0. All for T. | Prior source for the affine identity and the parity-vector bijection. Concerns first descent below n, not total stopping time. |
| 2 | C. J. Everett, Adv. Math. 25 (1977) 42-45 | Not accessed (403) | Via Lagarias's bibliography (#4): a density-1 descent result found independently of Terras. | Co-credit for density only. |
| 3 | J. C. Lagarias, "The 3x+1 problem and its generalizations", Amer. Math. Monthly 92 (1985) 3-23. [scan](https://web.williams.edu/Mathematics/sjmiller/public_html/1/addcomments/Lagarias_3x+1AndItsGeneralizations.pdf) | Part (pp. 5-9) | Eqs. (2.4)-(2.6): T^(k)(n) = lambda_k n + rho_k. **Theorem B**: Q_k(n) = sum x_i 2^i is periodic mod 2^k and induces a permutation of Z/2^k whose order is a power of 2 (proof sketched). Thm A: density, credited to Terras and Everett. Sec. 2.1 heuristic: a factor of 3/4 per odd-to-odd step, so total stopping time is on average a constant times log n. | The stage1 note cites a "Theorem 2.1" for the bijection. No such theorem exists; it is Theorem B, and it is Terras's result. |
| 4 | Lagarias, annotated bibliographies, [math/0309224](https://arxiv.org/abs/math/0309224) (1963-1999) and [math/0608208](https://arxiv.org/abs/math/0608208) (2000-2009) | Part (full PDFs text-searched, sampled entries) | Garner and Terras checked the coefficient-stopping-time conjecture. Huang-Wu: the residue/parity bijection is "implicit in Terras". Merlini-Sala: ordinary-map orbits predicted at most about 67.1 log n steps. Leavens-Vermeulen, Oliveira e Silva and Roosendaal ran record searches. No proof-assistant entries through 2009. | Prediction and record-finding are old topics. Ranking an interval by a short prefix is not listed. |
| 5 | A. V. Kontorovich and J. C. Lagarias, "Stochastic models for the 3x+1 and 5x+1 problems", [arXiv:0910.1944](https://arxiv.org/abs/0910.1944) | Part (Secs. 1-4, 6) | For T: mean total stopping time about (2/ln(4/3)) ln n = 6.95212 ln n, with a Gaussian limit (Borovkov-Pfeifer). Extremal constant gamma about 41.677647 at ones-ratio about 0.609. Best observed gamma 36.7169. Nothing about the average is proved rigorously. | Gives the model constant tested in Section 3.3. |
| 6 | J. C. Lagarias and A. Weiss, "The 3x+1 problem: two stochastic models", Ann. Appl. Probab. 2 (1992) 229-261 | Not accessed (Project Euclid stub; umich 403) | Constants above, via #5. | Cited only through #5. |
| 7 | A. A. Borovkov and D. Pfeifer, "Estimates for the Syracuse problem via a probabilistic model". [author preprint](https://uol.de/f/5/inst/mathe/personen/dietmar.pfeifer/Publ/P76_preprint.pdf) | Part (preprint, not the 2000 journal version) | Thm 5: a CLT for the model stopping time, with scale mu^{-3/2} sigma (ln a)^{1/2}, mu = (1/2) ln(4/3), sigma = (1/2) ln 3. Convergence rate O((ln a)^{-1/2}). | Model variance; see the enrichment gap in 3.3. |
| 8 | D. Applegate and J. C. Lagarias, "Lower bounds for the total stopping time of 3x+1 iterates", Math. Comp. 72 (2003). [arXiv:math/0103054](https://arxiv.org/abs/math/0103054) | Part (intro to Sec. 3) | Thm 1.1: infinitely many n with tau(n) >= 6.14316 ln n (T steps). The method is a backward search of pruned trees to depth 60, indexed by residues mod 3^{l+1}, with about 350 million trees in the certificate. | Large-tau inputs are built backward with residues mod 3^k, not ranked forward. Different objective, same quantity. |
| 9 | I. Krasikov and J. C. Lagarias, "Bounds for the 3x+1 problem using difference inequalities", [arXiv:math/0205002](https://arxiv.org/abs/math/0205002) | Abstract and intro | At least x^0.84 integers below x reach a given a. | Tree density only. Already cited in the preprint. |
| 10 | G. Wirsching, LNM 1681 (1998) | Not accessed | Via #4: Collatz graph, 3-adic counting, "heuristic principle". | None used. |
| 11 | T. Tao, "Almost all orbits of the Collatz map attain almost bounded values", Forum Math. Pi 10 (2022) e12. [arXiv:1909.03562](https://arxiv.org/abs/1909.03562) | Full (parts of the PDF) | Thm 1.3: Colmin(N) < f(N) for almost all N in logarithmic density, for any f tending to infinity. For a random odd N, the 2-adic valuation vector of the Syracuse iterates is within total variation 2^{-cn} of i.i.d. Geom(2). The Syracuse residues mod 3^n are not uniform. | Justifies treating early parities of typical inputs as nearly independent. Says nothing about the upper tail ProofX selects. |
| 12 | J. Simons and B. de Weger, Acta Arith. 117 (2005) 51-70; C. Hercher, "There are no Collatz m-cycles with m <= 91", J. Integer Seq. 26 (2023). [arXiv:2201.00406](https://arxiv.org/abs/2201.00406) | Simons-de Weger: search snippet only. Hercher: Full | Hercher: m >= 92, quoting Simons-de Weger m >= 68 (2005) and m >= 76 (2010). Cycle bounds use the verification limit X0 = 704 * 2^60. | Unrelated to selection. Listed because the stage1 note implies cycle theory supports it; it does not. |
| 13 | S. Eliahou, Discrete Math. 118 (1993) 45-56 | Search snippet only | Any nontrivial cycle has at least 17,087,915 elements. | Not used. |
| 14 | D. Barina, "Improved verification limit for the convergence of the Collatz conjecture", J. Supercomput. 81 (2025) 810. [PDF](https://www.fit.vut.cz/research/publication-file/c197809/298514/s11227-025-07337-0.pdf) | Full | Verified to 2^71 on the shortcut map. A 3^k preimage sieve (mod 9 removes 44.4%). A 2^k sieve with one bit per low-k-bit class that drops below its start or merges within k steps; the best size was 2^34 bits. Five new path records. | Residue screening mod 2^k is standard in verification, where it eliminates classes. ProofX uses residues for nothing yet; PX-COL-003 meant to, but wrongly (Section 4). |
| 15 | V. Angeltveit, [arXiv:2602.10466](https://arxiv.org/abs/2602.10466) (2026) | Part | Recursive bit-by-bit search with lookahead bitvectors, equivalent to a 2^86-bit sieve. Checking 2^(N+1) costs under twice checking 2^N. | Cited in the preprint. |
| 16 | T. Oliveira e Silva, verification page [sweet.ua.pt/tos/3x+1.html](http://sweet.ua.pt/tos/3x+1.html); Math. Comp. 68 (1999) | Page: Abstract (summary). Paper: Not accessed (AMS 403) | Verified to 5 * 2^60 (stopped 2009). The program sieves values whose stopping time is known to be under 40. | Record method only. |
| 17 | E. Roosendaal, "On the 3x+1 problem", [ericr.nl/wondrous](http://www.ericr.nl/wondrous/) (plain http) | Full (main page, delays.txt) | Ordinary map. Delay D, odd count O, even count E, completeness O/E < ln2/ln3, Gamma = E/ln N. Delay records near the ProofX windows: 1,723,519 (556), 2,298,025 (559); 31,466,382 (705), 36,791,535 (744); 268,549,803 (964), 537,099,606 (965). Records come from a merge sieve of width 2^25 that skips about 93% of inputs. | Same objective as ProofX (long ordinary delays per log n), computed on whole orbits. Cross-check passed: PX-COL-002 window maxima are 515, 687 and 585, each at or below the record bound for its range. |
| 18 | O. Rozier, [arXiv:1805.00133](https://arxiv.org/abs/1805.00133) | Abstract | Explicit inverse of the 2-adic parity-sequence map; ergodicity on small invariant sets. | Background on parity vectors. |
| 19 | O. Rozier and C. Terracol, "Paradoxical behavior in Collatz sequences", Discrete Math. 349 (2026) 115167. [arXiv:2502.00948](https://arxiv.org/abs/2502.00948) v5 | Full (PDF) | Shortcut map. Eq. (2): T^j(n) = (3^q/2^j) n + E_j(n). **Theorem 2.4** in v5 (the rwst blueprint cites it as Theorem 2.2): (3^q - 2^q)/2^j <= E_j <= (3/2)^q - 1. The upper bound is attained only for parity vector 0^{j-q}1^q, the lower only for 1^q 0^{j-q}. | The sharp form of the bound ProofX proved loosely. The ordinary-map analogue is in Section 3.1. |
| 20 | N. Bonacorsi and M. Bordoni, [arXiv:2603.04479](https://arxiv.org/abs/2603.04479) (2026) | Full (PDF) | Negative-binomial regression of total stopping time on log log n, with n mod 8 as a random effect, for n <= 1e7. Held-out log score -5.46 per observation; it beats odd-block generators. | Cheap-covariate prediction. Uses no prefix parity beyond n mod 8. |
| 21 | E. Melas and N. C. Poulios, J. Dynamics and Games (2026), doi:10.3934/jdg.2026037 | Abstract and tables | Logit and tree models of extreme stopping-time events: accuracy 69-81%, McFadden pseudo-R^2 0.127-0.185. Features include n mod 8 and sdt(n)/log2 n, so leakage needs checking. | Prediction of extremes. No prefix parity. |
| 22 | F. Charton and A. Narayanan, "Transformers know more than they can tell", [arXiv:2511.10811](https://arxiv.org/abs/2511.10811) (2025) | Abstract | Transformers predict "long Collatz steps" (shortcut map) with 99.7% accuracy in bases 24 and 32. They learn input classes by residue mod 2^p, which fixes loop lengths. | Shows the 2-adic class structure is what learners pick up. Does not address selection. |
| 23 | Other 2020-2026 arXiv items: 2605.13886 (finitary Terras density, paradoxical sequences), 2604.13082 (grokking delay), 2002.12762, 2209.03730, 2607.10041, 2007.06979 | Abstract | Parity-vector and 2-adic results; none selects inputs by prefix statistics. | Negative search result (four arXiv queries). |
| 24 | rwst/Collatz-Map-Basics, Lean 4 + Mathlib. [GitHub](https://github.com/rwst/Collatz-Map-Basics) | Full (`Decomposition.lean` read; file lists of `Terras.lean` and `Parity.lean`) | `linear_decomposition`: 2^k * T_iter k n = 3^(num_odd_steps k n) * n + decomposition_correction k n, over N, shortcut map. `T_congr` and the blueprint state Terras Thm 1.2. Also formalizes Rozier-Terracol lemmas. Zero `sorry` in these files. | Prior formalization of the identity ProofX proves, on the other map and with Mathlib. |
| 25 | google-deepmind/formal-conjectures, `CollatzConjecture.lean` | Full (file) | Statement only, proof `sorry`. | None. |
| 26 | Other Lean repositories: lechmazur/terras_density_one, mmusson/collatz, xrchz/CollatzLean, gotrevor/tao-collatz, LeeMarshall1113/collatz-m-cycles | README or file lists only | Various sorry-free claims. xrchz/CollatzLean claims `¬ Collatz.Conjecture` (witness-free). | Unaudited. The xrchz claim contradicts nothing proven but is extraordinary; it was not built or checked here and should not be repeated as fact. |
| 28 | G. T. Leavens and M. Vermeulen, "3x+1 search programs", tech report ISU TR92-01 (journal version: Computers Math. Applic. 1992). [TR PDF](https://www.cs.ucf.edu/~leavens/tech-reports/ISU/TR92-01/TR.pdf) | Part (tech report; journal version not accessed) | Lemma 20: "steps(k) <= p+steps(j)". Once an iterate falls to or below an input j whose delay is known, k can be dismissed when that bound cannot beat the record. About 15 steps per number on average, against about 276 for full orbits, when the earlier records are known. Lemma 21 drops inputs a priori by their low m-bit residue. | Exact, bound-based early abandonment for record search. This is the closest prior art to ProofX screening, but it needs a known record threshold and proves an input cannot win. ProofX ranks by a statistic with no threshold. |
| 29 | E. Roosendaal, technical page [ericr.nl/wondrous/techpage.html](http://www.ericr.nl/wondrous/techpage.html) | Full | "A cut-off technique is also applied at several points ... to terminate further processing of this number": once below a bound, delay is at most known delay plus steps so far, so the input is abandoned under a threshold. About a 10x gain; merge sieves skip roughly 89-93% of inputs. | Same family as #28. Exact pruning against records. |
| 30 | rogerdahl/cuda-collatz (GitHub README) | Full (README) | Early termination against the delay-record table was implemented, then disabled because checking cost more than it saved on GPU. | Pruning overhead can dominate. ProofX's step counts do not price comparison overhead, which is stated as a limitation. |
| 27 | K. Jamieson and A. Talwalkar, [arXiv:1502.07943](https://arxiv.org/abs/1502.07943); Z. Karnin, T. Koren and O. Somekh, ICML 2013 | Abstract (Jamieson-Talwalkar); Karnin et al. not reopened | Successive halving: allocate more budget to promising candidates in rounds. | Source of the screening method proposed in the next-steps note. |

Search coverage: four arXiv queries, a targeted search for pruning in record programs, GitHub code and repository search, and web
search. "Not found" below means not found by these searches.

## 2. What is already known

1. **The affine identity.** 2^m C^h(n) = 3^k n + c(sigma) is Terras 1976 Thm 1.1 and
   Lagarias 1985 (2.4)-(2.6), rewritten for the ordinary map. A Lean 4 + Mathlib
   proof for the shortcut map exists (#24). ProofX's `trajectory_expansion`
   (added in this session) is the ordinary-map version in core Lean. That is
   packaging, not new mathematics.
2. **Parity vectors and residues.** The first k shortcut parities are a
   bijection with n mod 2^k (Terras Thm 1.2, Cor 1.3; Lagarias Thm B). For the
   ordinary map, an h-step prefix with m halvings is fixed by n mod 2^(m+1).
3. **Bounds on the additive term.** Rozier-Terracol Thm 2.4 gives the sharp
   two-sided bound for T and its extremal parity vectors. ProofX's
   `hornerConstant_lt` (c < 3^k 2^m) is correct but loose (Section 3.1). The sharp
   ordinary-map bound is now proved as `hornerConstant_sharp`.
4. **Monotonicity in k.** `spectral_monotone` says 3^k 2^(h-k) grows with k. This
   is a one-line inequality and appears implicitly everywhere the leading
   coefficient lambda_k is used.
5. **Why the odd count predicts total stopping time.** Under the random-walk
   model (#5, #6, #7), remaining time is about c ln x, with c = 3/ln(4/3) =
   10.43 ordinary steps per unit of ln x. The value 3/ln(4/3) is derived here, not
   quoted: it is the T constant 2/ln(4/3) plus the odd steps, or equivalently
   drift ln(3/4)/3 per ordinary step under the stationary parity chain. Inside a
   narrow stratum, ln x_h moves by ln 6 per extra odd step, so the model
   predicts a slope of 10.43 * ln 6 = 18.68 steps of tau per extra odd step. The
   data match this (Section 3.3).
6. **Long-trajectory objectives.** Record tables and gamma statistics (#16, #17),
   backward constructions (#8) and statistical prediction (#20, #21) all exist.
   The preprint already says this and makes no priority claim for prefixes or
   prediction.

## 3. What this session found that is new

These come from the published PX-COL-002 bundle plus fresh computation. Scripts
are in `scripts/research/col002_reanalysis/`. Everything in 3.2 and 3.5 uses
windows whose labels were already published, so it is post hoc.

### 3.1 Sharp ordinary-map Horner bound

For the ordinary map with k >= 1 odd steps and m halvings in h steps:

c(sigma) <= 2^(m+1-k) * (3^k - 2^k)

The proof: every odd step except possibly the last is followed by a halving,
so the j-th odd step has at most m - (k-1-j) halvings before it. Summing the
geometric series gives 2^m * sum_{i<k} (2/3)^i * 3^{k-1} = 2^(m+1-k)(3^k - 2^k).
A brute-force check over all n < 2^(h+3) for h = 8, 10, 12 found no violation,
and the bound is attained for every (k, m) that occurs. At h = 10, k = 5, the
maximum is 422, against 3,872 for ProofX's current bound. This is the
ordinary-map analogue of Rozier-Terracol Thm 2.4. It was not found stated
anywhere, but it is an elementary corollary, not a research result.

### 3.2 PX-COL-002 targets are dominated by tie-breaking

Total stopping times are small integers with heavy ties. In the 48 fresh strata,
the 313th largest value is shared by 306 inputs on average, and 123.6 of the 313
target slots per stratum are filled by the "smaller input wins" rule. That is
5,935 of 15,024 fresh targets (39.5%).

Three of the seven methods also break ties toward smaller inputs: odd count,
growth and ascending. So part of their measured gain is agreement with the
labelling rule, not prediction. Tie-fair credit gives inputs strictly above the
threshold 1, and splits the remaining slots equally among tied inputs. The
expected uniform count stays 51.28 per window. Results at B = 1024 (32 seeds):

| Method | R1 label / tie-fair | R2 label / tie-fair | R3 label / tie-fair |
| --- | --- | --- | --- |
| Growth | 121.59 / 123.05 | 112.50 / 117.63 | 107.53 / 111.12 |
| Odd count | 130.34 / 126.53 | 125.62 / 125.22 | 117.34 / 116.85 |
| Ascending | 64.00 / 54.87 | 88.06 / 60.05 | 83.28 / 55.49 |
| Uniform | 50.66 / 50.87 | 52.38 / 52.98 | 50.38 / 49.95 |

Charged-transition yield relative to the uniform expectation:

| Method | R1 label / tie-fair | R2 label / tie-fair | R3 label / tie-fair |
| --- | --- | --- | --- |
| Growth | 1.264 / 1.279 | 1.262 / 1.319 | 1.251 / 1.293 |
| Odd count | 1.353 / 1.314 | 1.397 / 1.392 | 1.361 / 1.355 |
| Ascending | 1.243 / 1.066 | 1.666 / 1.136 | 1.610 / 1.072 |
| Input-bit priority | 1.185 / 1.175 | 1.392 / 1.298 | 1.293 / 1.288 |

My reproduction gives the published label yields exactly.

Consequences:

* The preprint says ascending selection is "more efficient in two intervals"
  and that its "local structure" deserves investigation. Most of that effect is
  the tie rule. About 80% of ascending's excess hits over uniform in R2 and R3
  disappears under tie-fair credit (35.7 to 7.1, and 32.9 to 5.5).
* Odd count still beats growth on paired seeds, by 3.49 (SE 0.78, 23 of 32 seeds
  favor odd count), 7.58 (SE 0.98, 30 of 32) and 5.72 (SE 0.94, 27 of 32). These
  gaps are about 40-60% of the published ones. The seed SEs only describe
  sampling variation on fixed labels.
* Growth and odd count pick the same input 81-82% of the time. The ratio
  C^32(n)/n orders first by k, because consecutive k differ by a factor of 6 in
  3^k/2^(h-k) while the additive term moves it by at most 1 + 2^m/n. The
  methods differ only in how they order inputs within a k level.

### 3.3 The stochastic model explains the effect, with a magnitude gap

* **Mean.** Mean total stopping time over each full window is 149.11, 177.66
  and 195.82. The model 10.43 ln n gives 152.04, 180.72 and 209.62. R3 sits 14
  steps low (see 3.4).
* **Slope.** Within strata, the least-squares slope of tau on the 32-step odd
  count is 18.17, 18.58 and 20.44, against the model's 18.68. R^2 is 0.223,
  0.172 and 0.220 at h = 32; 0.116, 0.088 and 0.110 at h = 16; and 0.430, 0.336
  and 0.365 at h = 64.
* **Enrichment.** A random-parity simulation of the same selection task
  (`modelpred.py`, no fitted parameters) predicts odd-count enrichment of 2.01,
  1.90 and 1.90 over uniform. The observed tie-fair enrichment is 2.47, 2.44 and
  2.28. The model also has a larger spread of tau (SD 67.8, 73.2, 78.4 against
  observed 60.7, 71.0, 68.9).

So the direction and the slope of the PX-COL-002 effect follow from the classical
model, but its size is about 20% larger than the model predicts.

A follow-up run explained the gap (`gap.py`, `scatter.py` and `hybrid.py` in
`scripts/research/col002_reanalysis/`):

* **Persistence.** Across 30 further windows at 2^23, 2^27 and 2^31, observed
  enrichment divided by model enrichment is 1.199 (SD 0.094). It is above 1 in
  29 of 30 windows, with no trend by octave.
* **Clustering.** With 6,250 inputs drawn at random from [2^e, 1.05 * 2^e)
  instead of contiguous strata, the ratio is 1.148 (SD 0.045). Shared
  trajectory suffixes inside a window explain about a quarter of the gap.
* **End phase.** A hybrid model runs the random walk until x < 2^CUT, then uses
  the exact tau of int(x). Its enrichment rises with CUT: about 1.95 at 4, 2.14
  at 8, 2.18 at 12 and 2.23 at 16. At CUT 12-16 it reaches the scattered data.
  Real stopping times of numbers below a few thousand are less spread than a
  random walk predicts, and that difference propagates into the conditional
  spread.

The gap comes from the model's end phase, the bottom of the Collatz tree, plus
within-window clustering. I found no source that quantifies this end-phase
effect. It is not new early-orbit structure. That closes
the question raised in the first version of this review.

### 3.4 Three 100,000-input windows carry less evidence than they look

Twelve fresh random windows, of the same shape at 2^21, 2^25, 2^29 and 2^33,
show no systematic within-stratum gradient: the lowest-quarter target share
averages 0.256 (SD 0.027). That SD is about 4.5 times what independent sampling
would give (about 0.006). Window means of tau also wander, with stratum-mean SDs
of 7 to 25 steps. Nearby integers share trajectory suffixes, so targets cluster.
Results from three windows should be read as three correlated observations, not
300,000 inputs. Inference should treat windows as the unit.

### 3.5 A better screening policy, found post hoc

Single-stage screening wastes its budget: a larger pool with the same prefix
loses yield (odd count h = 32 with 8x pools: 1.15-1.24 tie-fair). Successive
halving keeps the large pool cheap: screen 8q proposals for 16 steps, keep 4q,
extend to 32, keep 2q, extend to 64, keep q. It reached tie-fair yields of
1.578, 1.595 and 1.511 on the fresh windows, against 1.317, 1.345 and 1.315 for
the frozen odd-count design under the same simulated pools. On the development
windows it reached 1.653, 1.643 and 1.636, against 1.373, 1.430 and 1.376. Two
other halving schedules also beat the baseline. This was a post-hoc hypothesis.

**Prospective test (PX-COL-004).** Frozen at `13716c5` before any label was
computed, then run on 24 fresh windows from 3.5e7 to 2.5e11. Halving beat
odd32 in 24 of 24 windows, with a median tie-fair yield ratio of 1.196 (range
1.086 to 1.297); the frozen criterion was met. A single 64-step prefix beat
odd32 in only 7 of 24 windows. See `docs/experiments/px-col-004-results.md`.

## 4. Audit of ProofX claims

### Preprint (Drive, 10 November 2026)

The preprint is careful. It names the conventions, credits Terras, Lagarias,
Applegate-Lagarias and the prediction papers, and makes no priority claim. Two
items need correction:

1. **Ascending selection's yield advantage (Tables 4-5, Secs. 7.3, 9, 10)** is
   mostly a tie-break artifact (3.2). Conclusion 10 recommends investigating
   "the local structure exposed by ascending selection"; the evidence for that
   structure is weak.
2. **Odd count vs growth.** The ordering stands, but the gap is about half the
   published size once ties are scored fairly. The tie rule should be stated as
   a source of bias in any future protocol.

Not wrong, but worth adding: the slope agreement in 3.3 places the result inside
known theory, which strengthens the paper's modest framing.

### `docs/research/stage1_odd_count_drift_derivation.md` (Antigravity, untracked)

This note was written from model memory by a single API call, with no source
read. It is wrong in ways that matter:

* It dates itself "December 2026" and calls itself a technical report.
* Its map is the shortcut map T, but PX-COL-002 used the ordinary map C. Its
  slopes and spectral ratios (3/2 per odd step) are for T. For C at fixed h the
  ratio between consecutive k is 6.
* It cites "Lagarias 1985, Theorem 2.1" for the bijection. That is Theorem B,
  and the result is Terras's.
* Example 2.8 assigns arbitrary parity vectors to n = 1000 and n = 1001.
  Parities are determined by n, so the example is impossible as written.
* Theorem 3.3 calls k a "minimal sufficient statistic". Nothing statistical is
  proved; the argument only shows ranking by k matches the n-to-infinity limit.
* Theorem 3.5 asserts more than 10% boundary collisions with a "proof sketch"
  containing no computation. Section 3.2 shows the actual within-k ordering
  difference.
* Theorem 4.4 claims N = 100,000 > 2^h for h up to 32, so proposals must
  "clump". 100,000 < 2^17, and every set of distinct integers in a window of
  6,250 already has distinct residues mod 2^h for h >= 13.
* Theorem 4.8 ("necessity of modular control") has no proof.

The file is replaced in this commit by a short corrected derivation.

### `ProofX/Trajectory.lean` (commit `8358686`)

* All theorems are correct and kernel-checked, and the axiom audit passes.
* As committed, the Horner bounds were about a recursively defined number tied
  to the trajectory only by its definition. The identity connecting it to
  `collatzIter` was missing, and the module cited the stage1 note as its
  reference. This session added `trajectory_expansion` (the identity) and
  `trajectory_endpoint_bounds` (3^k n <= 2^m C^h(n) < 3^k (n + 2^m)), and
  corrected the references.
* Novelty: none mathematically. The ordinary map, the core-only setting and the
  explicit c(sigma) bound distinguish it from rwst/Collatz-Map-Basics. That is
  engineering, not research.

### PX-COL-003 protocol and sampler (commit `8358686`)

The design cannot answer its own question and is withdrawn before any run:

1. **Mod 2^32 stratification is vacuous.** Each stratum holds 6,250 consecutive
   integers, which are automatically distinct mod 2^32 (indeed mod 2^13). The
   "residue-stratified" pool has the same law as the uniform pool. Policies 1
   and 2 would differ only by their seed streams.
2. **Code and protocol disagree.** `residue_stratified_pools` defaults to h = 8,
   not 32. With h = 8 and B = 1024, the pool of 256 per stratum is a complete
   residue system mod 2^8. That is a different, real intervention, but not the
   preregistered one.
3. **The motivation is false.** It rests on stage1's clumping theorem (above).
   Under the ordinary map, a 32-step prefix depends on n mod 2^(m+1) with m
   about 21 halvings on average, so distinct residues mod 2^32 add nothing.
4. **It reuses the biased endpoint.** Labels still break ties toward smaller
   inputs, and odd count still breaks ties the same way.
5. **Three windows again**, despite the correlation shown in 3.4.

## 5. Not verified

* Lagarias-Weiss 1992, Everett 1977, Wirsching 1998, Oliveira e Silva 1999,
  Leavens-Vermeulen 1992, Garner 1981, Simons-de Weger 2005 and Eliahou 1993
  were not opened. They are cited only as named in other sources.
* The ordinary-map constant 3/ln(4/3) is derived, not quoted. It matches
  Merlini-Sala's 67.1 log n extreme constant (via #4) and the data.
* The enrichment-gap explanation in 3.3 rests on one family of simulations; the
  hybrid model was not tuned, but CUT was scanned at four values.
* Unaudited Lean repositories in row 26, including the claimed disproof.
