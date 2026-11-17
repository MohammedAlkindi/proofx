# Why prefix odd count predicts total stopping time (ordinary map)

This replaces an earlier draft of the same name. That draft was generated from
model memory, used the shortcut map, and contained false statements; see
Section 4 of `2026-11-literature-review.md`. Everything below is elementary or
classical. Nothing here is a new theorem.

## Setting

C(n) = n/2 for even n and 3n + 1 for odd n. For a prefix of h steps from n,
let k be the number of odd steps, m = h - k the number of halvings, and
x_h = C^h(n), assuming 1 is not reached first.

## 1. Affine identity

2^m x_h = 3^k n + c, where c = sum_j 3^(k-1-j) 2^(m_j) and m_j is the number of
halvings before the j-th odd step.

This is Terras (1976) Thm 1.1 and Lagarias (1985) eqs. (2.4)-(2.6), rewritten
from the shortcut map. It is proved in `ProofX/Trajectory.lean` as
`trajectory_expansion`.

## 2. Bounds on c

Each odd step except possibly the last is followed by a halving. For k >= 1 this
gives

0 <= c <= 2^(m+1-k) (3^k - 2^k),

and the upper bound is attained when the odd steps come as late as the
constraint allows. Lean proves it as `hornerConstant_sharp` (in the form
c 2^k + 2^(m+1) 2^k <= 2^(m+1) 3^k), alongside the weaker c < 3^k 2^m
(`hornerConstant_lt`). Attainment is checked by brute force for h <= 12
(`scripts/research/col002_reanalysis/horner.py`). It is the ordinary-map analogue
of Rozier and Terracol (2026) Thm 2.4.

Hence 3^k n <= 2^m x_h < 3^k (n + 2^m) (`trajectory_endpoint_bounds`), so

ln x_h = ln n + k ln 3 - m ln 2 + delta, with 0 <= delta < ln(1 + 2^m / n).

## 3. Ranking by ratio is ranking by k, almost

At fixed h, raising k by one multiplies 3^k / 2^(h-k) by 6. The correction factor
1 + c/(3^k n) is below 1 + 2^m/n, which is under 6 whenever 2^m < 5n. For the
PX-COL-002 windows (n >= 2^21, m around 21 on average) that holds for nearly all
inputs. So C^h(n)/n and k give the same order except within a k level. There,
growth orders by c/n and odd count orders by smaller n. In PX-COL-002 the two
methods selected the same input 81-82% of the time.

## 4. Size of the effect

Under the stationary random-parity model, an ordinary step is odd with
probability 1/3 and the mean log change per step is ln(3/4)/3. The expected
remaining time from x is then about (3 / ln(4/3)) ln x = 10.43 ln x. This
constant is derived here from the shortcut-map constant 2/ln(4/3) of
Kontorovich and Lagarias (arXiv:0910.1944), not quoted from a source.

With n nearly fixed within a stratum, one more odd step raises ln x_h by ln 6.
The model therefore predicts that tau(n) rises by 10.43 ln 6 = 18.68 per extra
odd step in the prefix. On the PX-COL-002 fresh windows the fitted slopes are
18.17, 18.58 and 20.44.

## 5. What does not follow

* No sufficiency or optimality statement. k explains about 17-22% of the
  within-stratum variance of tau at h = 32.
* Nothing about residue classes beyond this: the h-step prefix is a function of
  n mod 2^(m+1). Any two inputs in a stratum of 6,250 consecutive integers are
  already distinct mod 2^13, so stratifying them mod 2^32 changes nothing.
