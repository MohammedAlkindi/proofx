# Lean 4 Boundary

ProofX now has a small root Lean 4 package for bounded, kernel-checkable
artifacts. This is deliberately narrower than the Python research toolkit. Lean
files in this repository certify concrete statements about finite data or
explicit witnesses; they do not prove open conjectures.

## Scope

| Path | Role |
| --- | --- |
| `lean-toolchain` | Pins the Lean toolchain used by the root package. |
| `lakefile.lean` | Defines the root `ProofX` Lean library. |
| `lake-manifest.json` | Records the current Lake package manifest. |
| `ProofX.lean` | Imports the root Lean modules. |
| `ProofX/Certificates.lean` | Defines small certificate types for bounded Collatz and Goldbach checks. |
| `ProofX/Status.lean` | Mirrors run-status semantics in Lean. |
| `.github/workflows/lean.yml` | Runs the root Lake build in CI. |

`packages/germinal/` remains a separate vendored Lean project. Do not mix its
toolchain, Lake state, or proof obligations into the ProofX root package unless
that integration is designed explicitly.

## What Lean Certifies Here

The current root package covers two kinds of statements:

- A Collatz certificate states that one concrete starting value reaches `1`
  within a concrete fuel bound under the checked step function.
- A Goldbach certificate states that one concrete even number has one explicit
  prime-pair witness.

These are proof-carrying bounded artifacts. They are useful because the claim is
small enough to be checked by Lean, but they are not proofs of Collatz, Goldbach,
or the Riemann Hypothesis.

## Claim Discipline

Use these phrases for Lean artifacts:

- "Lean checked this bounded certificate."
- "This witness satisfies the encoded predicate."
- "This run produced a candidate that can be exported to a Lean-checkable
  artifact."

Do not use these phrases unless the repository actually contains the theorem and
the build checks it:

- "ProofX proved Collatz."
- "ProofX verified Goldbach."
- "The engine discovered a theorem."
- "The run result is formally certified."

The formal claim is the exact Lean statement that builds. Nothing outside that
statement inherits the same status.

## Acceptance Bar

A root Lean artifact is acceptable only when all of the following are true:

- The toolchain is pinned in `lean-toolchain`.
- The artifact builds with `lake build`.
- CI runs the same root package.
- No accepted proof contains `sorry`, `admit`, an unsound `axiom`, `unsafe`
  code introduced to bypass a proof obligation, or `native_decide`.
- Every proof is closed by the kernel. `native_decide` is barred specifically:
  it compiles the proposition to native code, evaluates it, and trusts the
  result through `Lean.ofReduceBool` and `Lean.trustCompiler`, widening the
  trusted computing base to the Lean compiler and runtime. "Lean checked this"
  must not quietly mean "the Lean compiler evaluated this."
- Any Python-generated certificate has a deterministic exporter and a documented
  schema.
- Public copy names the finite scope of the certificate.

For now, the root package has no Mathlib dependency. Add Mathlib only when a
specific theorem needs it, and commit the resulting Lake manifest state in the
same change.

## Local Commands

```bash
lake build
```

Useful source checks:

```bash
rg -n "\b(sorry|admit|axiom|unsafe|native_decide)\b" ProofX ProofX.lean lakefile.lean
```

This textual scan is a convenience, not the gate. It cannot see an axiom that
enters through a tactic rather than a token, which is exactly how
`native_decide` evaded the earlier version of this check. The real gate is
`ProofX/Audit.lean`, which walks the actual axiom dependencies of every theorem
in the `ProofX` namespace and fails `lake build` if one depends on anything
outside `propext`, `Classical.choice`, and `Quot.sound`.

Adding a proof that needs a new axiom means editing `allowedAxioms` in that
file, which is a deliberate, reviewable act rather than an oversight.

If Lean is not installed locally, CI is the source of truth for the root Lean
build until the local environment is configured with `elan`.
