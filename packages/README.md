# Packages

This directory is for vendored or separately operated projects.

## `germinal/`

`packages/germinal/` is the old Germinal project preserved as a separate
subtree-style package. Keep it isolated from ProofX-root work unless a task
explicitly crosses that boundary.

ProofX's root Lean package lives in `ProofX/`, with entry points at
`ProofX.lean`, `lakefile.lean`, `lake-manifest.json`, and `lean-toolchain`.
Do not move Germinal files back to the repository root.
