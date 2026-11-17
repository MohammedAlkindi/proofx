import ProofX.Certificates

namespace ProofX

/-!
### Collatz Trajectory and Spectral Analysis

Trajectory iteration, odd/even step counts, the affine trajectory identity and
elementary bounds for the ordinary map `collatzStep` (`n / 2` or `3 * n + 1`),
in core Lean without Mathlib.

None of this is new mathematics. The identity `trajectory_expansion` is the
ordinary-map form of Terras (1976), Theorem 1.1, and Lagarias (1985), eqs.
(2.4)-(2.6), which are stated for the shortcut map `(3n + 1) / 2`. A Mathlib
formalization of the shortcut-map version exists in rwst/Collatz-Map-Basics
(`linear_decomposition`). See `docs/research/2026-11-literature-review.md`.
-/

/-- Iterate `collatzStep` for `i` steps starting at `n`. -/
def collatzIter (n : Nat) : Nat → Nat
  | 0 => n
  | i + 1 => collatzStep (collatzIter n i)

@[simp]
theorem collatzIter_zero (n : Nat) : collatzIter n 0 = n := rfl

@[simp]
theorem collatzIter_succ (n : Nat) (i : Nat) :
    collatzIter n (i + 1) = collatzStep (collatzIter n i) := rfl

/-- Parity bit (0 for even, 1 for odd) of the trajectory value at step `i`. -/
def parityAt (n : Nat) (i : Nat) : Nat :=
  collatzIter n i % 2

theorem parityAt_le_one (n : Nat) (i : Nat) : parityAt n i ≤ 1 := by
  dsimp [parityAt]
  omega

/-- Count of odd steps in the first `h` steps of the trajectory from `n`. -/
def oddCount (n : Nat) : Nat → Nat
  | 0 => 0
  | h + 1 => oddCount n h + parityAt n h

@[simp]
theorem oddCount_zero (n : Nat) : oddCount n 0 = 0 := rfl

@[simp]
theorem oddCount_succ (n : Nat) (h : Nat) :
    oddCount n (h + 1) = oddCount n h + parityAt n h := rfl

/-- The number of odd steps in `h` steps is at most `h`. -/
theorem oddCount_le (n : Nat) (h : Nat) : oddCount n h ≤ h := by
  induction h with
  | zero => simp [oddCount]
  | succ h ih =>
    dsimp [oddCount]
    have hp := parityAt_le_one n h
    omega

/-- Count of even steps in the first `h` steps: `m = h - k`. -/
def evenCount (n : Nat) (h : Nat) : Nat :=
  h - oddCount n h

/-- The number of even steps in `h` steps is at most `h`. -/
theorem evenCount_le (n : Nat) (h : Nat) : evenCount n h ≤ h := by
  dsimp [evenCount]
  omega

/-- Odd-count and even-count partition the `h` steps. -/
theorem oddCount_add_evenCount (n : Nat) (h : Nat) :
    oddCount n h + evenCount n h = h := by
  dsimp [evenCount]
  have hle := oddCount_le n h
  omega

/-- Horner displacement constant `C(σ)` accumulated along the trajectory of length `h`. -/
def hornerConstant (n : Nat) : Nat → Nat
  | 0 => 0
  | h + 1 =>
    if parityAt n h = 1 then
      3 * hornerConstant n h + 2 ^ (evenCount n h)
    else
      hornerConstant n h

@[simp]
theorem hornerConstant_zero (n : Nat) : hornerConstant n 0 = 0 := rfl

@[simp]
theorem hornerConstant_succ (n : Nat) (h : Nat) :
    hornerConstant n (h + 1) =
      if parityAt n h = 1 then
        3 * hornerConstant n h + 2 ^ (evenCount n h)
      else
        hornerConstant n h := rfl

/-- Key inductive bound: `2 * C(σ) ≤ (3^k - 1) * 2^m`. -/
theorem two_mul_hornerConstant_le (n : Nat) (h : Nat) :
    2 * hornerConstant n h ≤ (3 ^ (oddCount n h) - 1) * 2 ^ (evenCount n h) := by
  induction h with
  | zero =>
    dsimp [hornerConstant, oddCount, evenCount]
    omega
  | succ h ih =>
    dsimp [hornerConstant, oddCount]
    have hp := parityAt_le_one n h
    have hle := oddCount_le n h
    by_cases hpar : parityAt n h = 1
    · rw [if_pos hpar]
      rw [hpar]
      have heven : evenCount n (h + 1) = evenCount n h := by
        dsimp [evenCount, oddCount]
        rw [hpar]
        omega
      rw [heven]
      have hpow : 3 ^ (oddCount n h + 1) = 3 * 3 ^ (oddCount n h) := by
        rw [Nat.pow_succ, Nat.mul_comm]
      rw [hpow]
      have h1 : 2 * (3 * hornerConstant n h + 2 ^ evenCount n h) =
          3 * (2 * hornerConstant n h) + 2 * (2 ^ evenCount n h) := by omega
      have h2 : (3 * 3 ^ oddCount n h - 1) * 2 ^ evenCount n h =
          3 * ((3 ^ oddCount n h - 1) * 2 ^ evenCount n h) + 2 * (2 ^ evenCount n h) := by
        have hdist : 3 * ((3 ^ oddCount n h - 1) * 2 ^ evenCount n h) =
            (3 * (3 ^ oddCount n h - 1)) * 2 ^ evenCount n h := by rw [Nat.mul_assoc]
        have hdist2 : (3 * (3 ^ oddCount n h - 1)) * 2 ^ evenCount n h + 2 * (2 ^ evenCount n h) =
            (3 * (3 ^ oddCount n h - 1) + 2) * 2 ^ evenCount n h := by rw [← Nat.add_mul]
        have hpos3 : 1 ≤ 3 ^ oddCount n h := Nat.one_le_pow (oddCount n h) 3 (by decide)
        have hid : 3 * (3 ^ oddCount n h - 1) + 2 = 3 * 3 ^ oddCount n h - 1 := by omega
        rw [hdist, hdist2, hid]
      rw [h1, h2]
      omega
    · have hpar0 : parityAt n h = 0 := by omega
      rw [if_neg hpar]
      rw [hpar0, Nat.add_zero]
      have heven : evenCount n (h + 1) = evenCount n h + 1 := by
        dsimp [evenCount, oddCount]
        rw [hpar0]
        omega
      rw [heven]
      have hpow2 : 2 ^ (evenCount n h + 1) = 2 * 2 ^ (evenCount n h) := by
        rw [Nat.pow_succ, Nat.mul_comm]
      rw [hpow2]
      have hmul : (3 ^ oddCount n h - 1) * (2 * 2 ^ evenCount n h) =
          2 * ((3 ^ oddCount n h - 1) * 2 ^ evenCount n h) := by
        rw [Nat.mul_left_comm]
      rw [hmul]
      omega

/--
Affine trajectory identity for the ordinary map: after `h` steps with `k` odd
and `m = h - k` even steps, `2 ^ m * C^h(n) = 3 ^ k * n + c(σ)`.

This is what ties `hornerConstant` to the trajectory; the bounds below are
statements about the trajectory only through this identity.
-/
theorem trajectory_expansion (n h : Nat) :
    2 ^ evenCount n h * collatzIter n h = 3 ^ oddCount n h * n + hornerConstant n h := by
  induction h with
  | zero => simp [evenCount, oddCount, hornerConstant, collatzIter]
  | succ h ih =>
    have hp := parityAt_le_one n h
    have hle := oddCount_le n h
    by_cases hpar : parityAt n h = 1
    · have hodd : collatzIter n h % 2 = 1 := hpar
      have hstep : collatzIter n (h + 1) = 3 * collatzIter n h + 1 := by
        simp [collatzIter, collatzStep, hodd]
      have hk : oddCount n (h + 1) = oddCount n h + 1 := by simp [oddCount, hpar]
      have hm : evenCount n (h + 1) = evenCount n h := by
        unfold evenCount; rw [hk]; omega
      rw [hstep, hm, hk, hornerConstant_succ, if_pos hpar, Nat.pow_succ]
      generalize hx : collatzIter n h = x at ih ⊢
      generalize hE : 2 ^ evenCount n h = E at ih ⊢
      generalize hP : 3 ^ oddCount n h = P at ih ⊢
      generalize hC : hornerConstant n h = C at ih ⊢
      have e1 : E * (3 * x + 1) = 3 * (E * x) + E := by
        rw [Nat.mul_add, Nat.mul_one, Nat.mul_left_comm]
      have e2 : P * 3 * n = 3 * (P * n) := by
        rw [Nat.mul_comm P 3, Nat.mul_assoc]
      rw [e1, e2, ih]
      omega
    · have hpar0 : parityAt n h = 0 := by omega
      have heven : collatzIter n h % 2 = 0 := hpar0
      have hstep : collatzIter n (h + 1) = collatzIter n h / 2 := by
        simp [collatzIter, collatzStep, heven]
      have hk : oddCount n (h + 1) = oddCount n h := by simp [oddCount, hpar0]
      have hm : evenCount n (h + 1) = evenCount n h + 1 := by
        unfold evenCount; rw [hk]; omega
      rw [hstep, hm, hk, hornerConstant_succ, if_neg hpar, Nat.pow_succ]
      have hx2 : 2 * (collatzIter n h / 2) = collatzIter n h := by omega
      rw [Nat.mul_assoc, hx2, ih]

/-- Non-negativity of the Horner constant. -/
theorem hornerConstant_nonneg (n : Nat) (h : Nat) :
    0 ≤ hornerConstant n h := by
  omega

/-- Strict upper bound: `hornerConstant n h < 3 ^ k * 2 ^ m`. -/
theorem hornerConstant_lt (n : Nat) (h : Nat) :
    hornerConstant n h < 3 ^ (oddCount n h) * 2 ^ (evenCount n h) := by
  have hih := two_mul_hornerConstant_le n h
  have hP : 0 < 3 ^ oddCount n h := Nat.pow_pos (by decide)
  have hE : 0 < 2 ^ evenCount n h := Nat.pow_pos (by decide)
  have hdist : (3 ^ oddCount n h - 1) * 2 ^ evenCount n h =
      3 ^ oddCount n h * 2 ^ evenCount n h - 2 ^ evenCount n h := by
    rw [Nat.sub_mul, Nat.one_mul]
  have hlt : (3 ^ oddCount n h - 1) * 2 ^ evenCount n h <
      2 * (3 ^ oddCount n h * 2 ^ evenCount n h) := by
    rw [hdist]
    have hle : 2 ^ evenCount n h ≤ 3 ^ oddCount n h * 2 ^ evenCount n h := by
      calc 2 ^ evenCount n h = 1 * 2 ^ evenCount n h := (Nat.one_mul _).symm
        _ ≤ 3 ^ oddCount n h * 2 ^ evenCount n h := Nat.mul_le_mul_right _ hP
    omega
  have h2C : 2 * hornerConstant n h < 2 * (3 ^ oddCount n h * 2 ^ evenCount n h) := by omega
  exact Nat.lt_of_mul_lt_mul_left h2C

/-- Non-strict upper bound: `hornerConstant n h ≤ 3 ^ k * 2 ^ m`. -/
theorem hornerConstant_le (n : Nat) (h : Nat) :
    hornerConstant n h ≤ 3 ^ (oddCount n h) * 2 ^ (evenCount n h) :=
  Nat.le_of_lt (hornerConstant_lt n h)

/-- Lower bound on the Horner displacement constant. -/
theorem horner_lower_bound (n : Nat) (h : Nat) :
    0 ≤ hornerConstant n h :=
  hornerConstant_nonneg n h

/-- Upper bound on the Horner displacement constant: `C(σ) < 3^k * 2^m`. -/
theorem horner_upper_bound (n : Nat) (h : Nat) :
    hornerConstant n h < 3 ^ (oddCount n h) * 2 ^ (evenCount n h) :=
  hornerConstant_lt n h

/--
Two-sided endpoint bound from the identity and the Horner bound:
`3 ^ k * n ≤ 2 ^ m * C^h(n) < 3 ^ k * (n + 2 ^ m)`. So within a narrow input
range the endpoint is fixed by `k` up to the factor `1 + 2 ^ m / n`.
-/
theorem trajectory_endpoint_bounds (n h : Nat) :
    3 ^ oddCount n h * n ≤ 2 ^ evenCount n h * collatzIter n h ∧
      2 ^ evenCount n h * collatzIter n h < 3 ^ oddCount n h * (n + 2 ^ evenCount n h) := by
  have hid := trajectory_expansion n h
  have hlt := hornerConstant_lt n h
  rw [hid, Nat.mul_add]
  omega

/--
Monotonicity of the leading coefficient in the odd-step count.
For fixed trajectory length `h` and odd counts `k1 < k2 ≤ h`,
`3 ^ k1 * 2 ^ (h - k2) < 3 ^ k2 * 2 ^ (h - k1)`.
-/
theorem spectral_monotone {h k1 k2 : Nat} (hk : k1 < k2) (hk2 : k2 ≤ h) :
    3 ^ k1 * 2 ^ (h - k2) < 3 ^ k2 * 2 ^ (h - k1) := by
  have h3 : 3 ^ k1 < 3 ^ k2 := Nat.pow_lt_pow_right (by decide) hk
  have hdiff : h - k2 ≤ h - k1 := by omega
  have h2 : 2 ^ (h - k2) ≤ 2 ^ (h - k1) := Nat.pow_le_pow_right (by decide) hdiff
  have hpos : 0 < 2 ^ (h - k1) := Nat.pow_pos (by decide)
  exact Nat.mul_lt_mul_of_lt_of_le h3 h2 hpos

/-- Non-strict spectral monotonicity. -/
theorem spectral_monotone_le {h k1 k2 : Nat} (hk : k1 ≤ k2) (hk2 : k2 ≤ h) :
    3 ^ k1 * 2 ^ (h - k2) ≤ 3 ^ k2 * 2 ^ (h - k1) := by
  rcases Nat.lt_or_eq_of_le hk with hlt | heq
  · exact Nat.le_of_lt (spectral_monotone hlt hk2)
  · subst heq
    exact Nat.le_refl _

/-- `1` when the step just taken (step `h - 1`) was odd, else `0`. -/
def lastOdd (n : Nat) : Nat → Nat
  | 0 => 0
  | h + 1 => parityAt n h

/-- An odd step `3x + 1` always produces an even value. -/
theorem parityAt_succ_of_odd {n h : Nat} (hpar : parityAt n h = 1) : parityAt n (h + 1) = 0 := by
  have hodd : collatzIter n h % 2 = 1 := hpar
  show collatzIter n (h + 1) % 2 = 0
  simp only [collatzIter_succ, collatzStep, hodd]
  simp
  omega

theorem hornerConstant_eq_zero_of_oddCount_eq_zero {n h : Nat} (h0 : oddCount n h = 0) :
    hornerConstant n h = 0 := by
  have hb := two_mul_hornerConstant_le n h
  rw [h0] at hb
  simp at hb
  omega

theorem horner_sharp_inv (n h : Nat) :
    oddCount n h = 0 ∨
      hornerConstant n h * 2 ^ oddCount n h + 2 ^ (evenCount n h + lastOdd n h) * 2 ^ oddCount n h ≤
        2 ^ (evenCount n h + lastOdd n h) * 3 ^ oddCount n h := by
  induction h with
  | zero => left; rfl
  | succ h ih =>
    have hp := parityAt_le_one n h
    have hle := oddCount_le n h
    by_cases hpar : parityAt n h = 1
    · -- odd step: the previous step was even
      have he : lastOdd n h = 0 := by
        cases h with
        | zero => rfl
        | succ h' =>
          show parityAt n h' = 0
          have := parityAt_le_one n h'
          by_cases hq : parityAt n h' = 1
          · have := parityAt_succ_of_odd hq; omega
          · omega
      have hk : oddCount n (h + 1) = oddCount n h + 1 := by simp [oddCount, hpar]
      have hm : evenCount n (h + 1) = evenCount n h := by
        unfold evenCount; rw [hk]; omega
      have hl : lastOdd n (h + 1) = 1 := hpar
      right
      rw [hk, hm, hl, hornerConstant_succ, if_pos hpar, Nat.pow_succ, Nat.pow_succ, Nat.pow_succ]
      rw [he, Nat.add_zero] at ih
      generalize hA : 2 ^ evenCount n h = A at ih ⊢
      generalize hP : 2 ^ oddCount n h = P at ih ⊢
      generalize hQ : 3 ^ oddCount n h = Q at ih ⊢
      rcases ih with h0 | ih
      · have hc := hornerConstant_eq_zero_of_oddCount_eq_zero h0
        rw [hc]
        rw [h0, Nat.pow_zero] at hP hQ
        subst hP; subst hQ
        omega
      · generalize hC : hornerConstant n h = C at ih ⊢
        have t1 : C * (P * 2) = C * P * 2 := (Nat.mul_assoc C P 2).symm
        have t2 : A * (P * 2) = A * P * 2 := (Nat.mul_assoc A P 2).symm
        have t3 : A * 2 * (P * 2) = A * P * (2 * 2) := Nat.mul_mul_mul_comm A 2 P 2
        have t4 : A * 2 * (Q * 3) = A * Q * (2 * 3) := Nat.mul_mul_mul_comm A 2 Q 3
        rw [Nat.add_mul, Nat.mul_assoc 3 C (P * 2), t1, t2, t3, t4]
        omega
    · -- even step
      have hpar0 : parityAt n h = 0 := by omega
      have hk : oddCount n (h + 1) = oddCount n h := by simp [oddCount, hpar0]
      have hm : evenCount n (h + 1) = evenCount n h + 1 := by
        unfold evenCount; rw [hk]; omega
      have hl : lastOdd n (h + 1) = 0 := hpar0
      rcases ih with h0 | ih
      · left; rw [hk]; exact h0
      · right
        rw [hk, hm, hl, hornerConstant_succ, if_neg hpar]
        simp only [Nat.add_zero]
        have hPQ : 2 ^ oddCount n h ≤ 3 ^ oddCount n h := Nat.pow_le_pow_left (by decide) _
        have hle1 : lastOdd n h ≤ 1 := by
          cases h with
          | zero => simp [lastOdd]
          | succ h' => exact parityAt_le_one n h'
        generalize hP : 2 ^ oddCount n h = P at ih hPQ ⊢
        generalize hQ : 3 ^ oddCount n h = Q at ih hPQ ⊢
        generalize hC : hornerConstant n h = C at ih ⊢
        rcases Nat.lt_or_ge (lastOdd n h) 1 with h0 | h1
        · have hz : lastOdd n h = 0 := by omega
          rw [hz, Nat.add_zero] at ih
          rw [Nat.pow_succ]
          generalize hA : 2 ^ evenCount n h = A at ih ⊢
          have hAPQ : A * P ≤ A * Q := Nat.mul_le_mul_left A hPQ
          rw [Nat.mul_right_comm A 2 P, Nat.mul_right_comm A 2 Q]
          omega
        · have ho : lastOdd n h = 1 := by omega
          rw [ho] at ih
          exact ih

/--
Sharp bound on the Horner term for the ordinary map: with `k ≥ 1` odd steps
and `m` halvings, `c * 2^k ≤ 2^(m+1) * (3^k - 2^k)`, written without
subtraction. It is attained (checked by brute force for `h ≤ 12`). It is the
ordinary-map analogue of Rozier and Terracol (2026), Theorem 2.4.
-/
theorem hornerConstant_sharp {n h : Nat} (hk : 1 ≤ oddCount n h) :
    hornerConstant n h * 2 ^ oddCount n h + 2 ^ (evenCount n h + 1) * 2 ^ oddCount n h ≤
      2 ^ (evenCount n h + 1) * 3 ^ oddCount n h := by
  rcases horner_sharp_inv n h with h0 | inv
  · omega
  · have hPQ : 2 ^ oddCount n h ≤ 3 ^ oddCount n h := Nat.pow_le_pow_left (by decide) _
    have hle1 : lastOdd n h ≤ 1 := by
      cases h with
      | zero => simp [lastOdd]
      | succ h' => exact parityAt_le_one n h'
    generalize hP : 2 ^ oddCount n h = P at inv hPQ ⊢
    generalize hQ : 3 ^ oddCount n h = Q at inv hPQ ⊢
    generalize hC : hornerConstant n h = C at inv ⊢
    rcases Nat.lt_or_ge (lastOdd n h) 1 with h0 | h1
    · have hz : lastOdd n h = 0 := by omega
      rw [hz, Nat.add_zero] at inv
      rw [Nat.pow_succ]
      generalize hA : 2 ^ evenCount n h = A at inv ⊢
      have hAPQ : A * P ≤ A * Q := Nat.mul_le_mul_left A hPQ
      rw [Nat.mul_right_comm A 2 P, Nat.mul_right_comm A 2 Q]
      omega
    · have ho : lastOdd n h = 1 := by omega
      rw [ho] at inv
      exact inv

end ProofX
