import Lake
open Lake DSL

package proofx where
  version := v!"0.1.0"

@[default_target]
lean_lib ProofX where
  roots := #[`ProofX]
  leanOptions := #[
    ⟨`autoImplicit, false⟩,
    ⟨`pp.unicode.fun, true⟩
  ]
