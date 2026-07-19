import Std

namespace ProofX

/-!
Small kernel-checkable certificate definitions for ProofX run artifacts.

These definitions intentionally verify concrete bounded claims. They do not
state or prove Collatz, Goldbach, the Riemann Hypothesis, or any other open
conjecture.
-/

def collatzStep (n : Nat) : Nat :=
  if n % 2 = 0 then n / 2 else 3 * n + 1

def reachesOneWithin : Nat → Nat → Bool
  | 0, n => n = 1
  | fuel + 1, n =>
      if n = 1 then
        true
      else
        reachesOneWithin fuel (collatzStep n)

/-- `hasDivisorUpTo p b` is `true` exactly when some `d` with `2 ≤ d ≤ b`
divides `p`.

The third pattern is `d + 2` rather than `d + 1` so the three cases do not
overlap. That keeps the generated equation lemmas unconditional, which the
induction in `hasDivisorUpTo_of_dvd` relies on. -/
def hasDivisorUpTo (p : Nat) : Nat → Bool
  | 0 => false
  | 1 => false
  | d + 2 => decide (p % (d + 2) = 0) || hasDivisorUpTo p (d + 1)

/-!
### Primality without Mathlib

`IsPrime` is defined here rather than imported. Mathlib would supply
`Nat.Prime` and a `sqrt`-bounded decidability instance, but it ships several
such instances whose kernel reduction behaviour differs sharply, and picking
the wrong one makes `decide` hang. Carrying the bound in the certificate
removes the question and keeps the Lake manifest empty. See
`docs/superpowers/specs/2026-07-19-lean-certificate-exporter-design.md`.
-/

/-- Primality, stated directly so this package needs no Mathlib dependency. -/
def IsPrime (p : Nat) : Prop :=
  2 ≤ p ∧ ∀ d, d ∣ p → d = 1 ∨ d = p

/-- Bounded primality test.

`b` comes from the exporter, which guarantees `p ≤ b * b`; verifying that
costs the kernel one multiplication, where computing `sqrt p` in Lean would
cost a soundness argument and a library dependency.

The `min b (p - 1)` matters: without it `p = 2` takes bound `b = 2` and would
be found to divide itself. -/
def isPrimeWithBound (p b : Nat) : Bool :=
  decide (2 ≤ p) && decide (p ≤ b * b) && !hasDivisorUpTo p (min b (p - 1))

/-!
### Soundness of the bounded primality test

`isPrimeWithBound` is a `Bool`. On its own a certificate closing with `decide`
says only "this decision procedure returned true." The theorem below is what
makes it mean *primality*, and it is proven once: every generated certificate
stays a cheap `decide`, while the soundness argument does not scale with the
number of certificates.
-/

/-- If `m` divides `p` and `2 ≤ m ≤ b`, the bounded search finds a divisor. -/
theorem hasDivisorUpTo_of_dvd {p : Nat} :
    ∀ b m : Nat, 2 ≤ m → m ≤ b → m ∣ p → hasDivisorUpTo p b = true := by
  intro b
  induction b with
  | zero =>
      intro m h2 hle _
      omega
  | succ c ih =>
      intro m h2 hle hdvd
      match c with
      | 0 => omega
      | e + 1 =>
          rw [hasDivisorUpTo]
          by_cases hm : m = e + 2
          · -- m is the top of the range: it divides p, so p % m = 0.
            obtain ⟨k, hk⟩ := hdvd
            have hmod : p % (e + 2) = 0 := by
              rw [hk, ← hm]
              exact Nat.mul_mod_right m k
            simp [hmod]
          · -- m sits below the top, so the recursive call finds it.
            have hle' : m ≤ e + 1 := by omega
            have hrec := ih m h2 hle' hdvd
            simp [hrec]

/-- A bound `b` with `p ≤ b * b` and no divisor at or below it implies `p` is
prime.

The argument: any nontrivial divisor `d` of `p` pairs with `e = p / d`. If both
exceeded `b` then `p = d * e > b * b ≥ p`, so the smaller one lies in the
searched range and `hasDivisorUpTo` would have found it. -/
theorem isPrime_of_isPrimeWithBound {p b : Nat} (h : isPrimeWithBound p b = true) :
    IsPrime p := by
  unfold isPrimeWithBound at h
  simp only [Bool.and_eq_true, decide_eq_true_eq,
    Bool.not_eq_eq_eq_not, Bool.not_true] at h
  obtain ⟨⟨hp2, hpb⟩, hnd⟩ := h
  refine ⟨hp2, ?_⟩
  intro d hdvd
  -- `by_contra` and `push_neg` are Mathlib tactics and this package has no
  -- Mathlib dependency, so the contradiction is set up with core `by_cases`.
  by_cases hd1 : d = 1
  · exact Or.inl hd1
  by_cases hdp : d = p
  · exact Or.inr hdp
  exfalso
  obtain ⟨e, he⟩ := hdvd
  -- Neither factor is degenerate.
  have hd0 : d ≠ 0 := by
    intro h0
    rw [h0, Nat.zero_mul] at he
    omega
  have hd2 : 2 ≤ d := by omega
  have he0 : e ≠ 0 := by
    intro h0
    rw [h0, Nat.mul_zero] at he
    omega
  have he1 : e ≠ 1 := by
    intro h1
    rw [h1, Nat.mul_one] at he
    exact hdp he.symm
  have he2 : 2 ≤ e := by omega
  -- Each factor is bounded by p, and neither equals p.
  have hdle : d ≤ p := by
    calc d = d * 1 := (Nat.mul_one d).symm
      _ ≤ d * e := Nat.mul_le_mul_left d (by omega)
      _ = p := he.symm
  have hele : e ≤ p := by
    calc e = 1 * e := (Nat.one_mul e).symm
      _ ≤ d * e := Nat.mul_le_mul_right e (by omega)
      _ = p := he.symm
  have hene : e ≠ p := by
    intro hep
    rw [hep] at he
    -- he : p = d * p, and d ≥ 2 with p > 0 makes the right side strictly larger.
    have hlt : p < d * p := by
      calc p = 1 * p := (Nat.one_mul p).symm
        _ < d * p := (Nat.mul_lt_mul_right (by omega : 0 < p)).mpr (by omega)
    rw [← he] at hlt
    exact Nat.lt_irrefl p hlt
  -- At least one factor lies in the searched range: if both exceeded b then
  -- p = d * e > b * b >= p.
  have hsplit : d ≤ b ∨ e ≤ b := by
    by_cases hdle : d ≤ b
    · exact Or.inl hdle
    by_cases hele : e ≤ b
    · exact Or.inr hele
    exfalso
    have hdb : b < d := Nat.not_le.mp hdle
    have heb : b < e := Nat.not_le.mp hele
    have hstep : b * b < d * e := by
      calc b * b ≤ b * e := Nat.mul_le_mul_left b (Nat.le_of_lt heb)
        _ < d * e := (Nat.mul_lt_mul_right (by omega : 0 < e)).mpr hdb
    rw [← he] at hstep
    exact Nat.lt_irrefl p (Nat.lt_of_le_of_lt hpb hstep)
  -- Either way `hasDivisorUpTo` would have reported it.
  rcases hsplit with hdb | heb
  · have : d ≤ min b (p - 1) := Nat.le_min.mpr ⟨hdb, by omega⟩
    rw [hasDivisorUpTo_of_dvd (min b (p - 1)) d hd2 this ⟨e, he⟩] at hnd
    exact Bool.noConfusion hnd
  · have hedvd : e ∣ p := ⟨d, by rw [he]; exact Nat.mul_comm d e⟩
    have : e ≤ min b (p - 1) := Nat.le_min.mpr ⟨heb, by omega⟩
    rw [hasDivisorUpTo_of_dvd (min b (p - 1)) e he2 this hedvd] at hnd
    exact Bool.noConfusion hnd

structure CollatzCertificate where
  start : Nat
  fuel : Nat
  checked : reachesOneWithin fuel start = true

def goldbachPair (n p q bp bq : Nat) : Bool :=
  decide (4 ≤ n) &&
    decide (n % 2 = 0) &&
    decide (p ≤ q) &&
    isPrimeWithBound p bp &&
    isPrimeWithBound q bq &&
    decide (p + q = n)

structure GoldbachCertificate where
  n : Nat
  p : Nat
  q : Nat
  bp : Nat
  bq : Nat
  checked : goldbachPair n p q bp bq = true

/-!
## Worked certificates

These are named rather than anonymous so `#print axioms` can audit them, and
they close with `decide` rather than `native_decide` so the kernel — not the
compiler — does the checking. See `docs/lean4.md`.
-/

theorem collatz_1_terminates : reachesOneWithin 0 1 = true := by
  decide

theorem collatz_27_terminates : reachesOneWithin 111 27 = true := by
  decide

-- Bounds are the smallest b with p ≤ b * b: 5 ≤ 3², 23 ≤ 5², 3 ≤ 2², 97 ≤ 10².
theorem goldbach_28_witness : goldbachPair 28 5 23 3 5 = true := by
  decide

theorem goldbach_100_witness : goldbachPair 100 3 97 2 10 = true := by
  decide

/-! ### The soundness theorem in use

These confirm that a `decide`-checked bound really does discharge `IsPrime`,
rather than the theorem merely type-checking in the abstract. `isPrime_2` pins
the degenerate case: the bound equals `p`, and only the `min b (p - 1)` in
`isPrimeWithBound` keeps 2 from counting as its own divisor. -/

theorem isPrime_2 : IsPrime 2 :=
  isPrime_of_isPrimeWithBound (by decide : isPrimeWithBound 2 2 = true)

theorem isPrime_3 : IsPrime 3 :=
  isPrime_of_isPrimeWithBound (by decide : isPrimeWithBound 3 2 = true)

theorem isPrime_97 : IsPrime 97 :=
  isPrime_of_isPrimeWithBound (by decide : isPrimeWithBound 97 10 = true)

end ProofX
