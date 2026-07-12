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

def hasDivisorUpTo (p : Nat) : Nat → Bool
  | 0 => false
  | 1 => false
  | d + 1 => decide (p % (d + 1) = 0) || hasDivisorUpTo p d

def isPrimeNat (p : Nat) : Bool :=
  decide (2 ≤ p) && !hasDivisorUpTo p (p - 1)

structure CollatzCertificate where
  start : Nat
  fuel : Nat
  checked : reachesOneWithin fuel start = true

def goldbachPair (n p q : Nat) : Bool :=
  decide (4 ≤ n) &&
    decide (n % 2 = 0) &&
    decide (p ≤ q) &&
    isPrimeNat p &&
    isPrimeNat q &&
    decide (p + q = n)

structure GoldbachCertificate where
  n : Nat
  p : Nat
  q : Nat
  checked : goldbachPair n p q = true

example : reachesOneWithin 0 1 = true := by
  native_decide

example : reachesOneWithin 111 27 = true := by
  native_decide

example : goldbachPair 28 5 23 = true := by
  native_decide

example : goldbachPair 100 3 97 = true := by
  native_decide

end ProofX
