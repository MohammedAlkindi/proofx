import Lean
import ProofX.Certificates
import ProofX.Status

/-!
Build-time axiom audit for ProofX artifacts.

`docs/lean4.md` bars any accepted proof that depends on an unsound axiom, and
documents an `rg` scan for the tokens `sorry`, `admit`, `axiom`, and `unsafe`.
That scan has a hole: `native_decide` introduces `Lean.ofReduceBool` and
`Lean.trustCompiler` without any of those tokens appearing in the source, so a
purely textual check passes over it in silence.

This module closes the hole by inspecting the actual axiom dependencies of
every theorem in the `ProofX` namespace. It runs as part of `lake build`, so a
regression fails the build rather than requiring anyone to read CI output.
-/

open Lean Elab Command

namespace ProofX.Audit

/--
Axioms an accepted ProofX proof may depend on.

These three are Lean's standard classical foundation and are sound. A proof
closed by `decide` reduces to `of_decide_eq_true (Eq.refl true)` and should
depend on none of them, but library lemmas may legitimately pull them in.

Deliberately absent: `Lean.ofReduceBool` and `Lean.trustCompiler`, which
`native_decide` introduces and which widen the trusted computing base to the
Lean compiler and runtime; and `sorryAx`, which admits anything.
-/
def allowedAxioms : Array Name :=
  #[``propext, ``Classical.choice, ``Quot.sound]

/--
Fail the build if any theorem under the `ProofX` namespace depends on an axiom
outside `allowedAxioms`.
-/
elab "#auditAxioms" : command => do
  let env ← getEnv
  let mut offenders : Array (Name × Name) := #[]
  for (declName, info) in env.constants.toList do
    if (`ProofX).isPrefixOf declName && !declName.isInternal then
      -- Every declaration, not only theorems: `sorry` in a `def` that a proof
      -- later depends on is just as unsound, and costs nothing extra to check.
      match info with
      | .axiomInfo _ => pure ()
      | _ =>
        let axs ← liftCoreM <| collectAxioms declName
        for ax in axs do
          unless allowedAxioms.contains ax do
            offenders := offenders.push (declName, ax)
  unless offenders.isEmpty do
    let lines := offenders.toList.map fun (d, a) => s!"  {d} depends on {a}"
    throwError "ProofX axiom audit failed:\n{String.intercalate "\n" lines}\n\n\
      Accepted proofs may depend only on: {allowedAxioms.toList}\n\
      See docs/lean4.md."

#auditAxioms

end ProofX.Audit
