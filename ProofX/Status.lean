namespace ProofX

/-!
Run-status vocabulary mirrored from the Python and documentation layers.

The key distinction is encoded directly: an unrefuted bounded run is a search
status, not a theorem claim.
-/

inductive RunStatus where
  | counterexampleFound
  | unrefutedAtBudget
  | error
  deriving DecidableEq, Repr

def RunStatus.isTheoremClaim : RunStatus → Bool
  | .counterexampleFound => false
  | .unrefutedAtBudget => false
  | .error => false

theorem unrefutedAtBudget_is_not_theorem_claim :
    RunStatus.isTheoremClaim .unrefutedAtBudget = false := by
  rfl

theorem counterexampleFound_is_not_theorem_claim :
    RunStatus.isTheoremClaim .counterexampleFound = false := by
  rfl

end ProofX
