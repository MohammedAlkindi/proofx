# Research Standards

ProofX documentation and public copy should make the project easier to trust by
stating less, more precisely.

## Claim Levels

Use the weakest accurate claim.

| Level | Acceptable wording | Evidence required |
| --- | --- | --- |
| Implementation behavior | "The CLI writes a JSONL ledger." | Code path or test. |
| Run result | "No counterexample was found in this run." | Command, seed, budget, code revision, and ledger. |
| Bounded check | "All candidates in this finite set satisfied the checked predicate." | Predicate definition, checker code, and input set. |
| Mathematical theorem | "The statement is proved." | Formal proof or conventional proof reviewed outside this repository. |

Most ProofX results are run results or bounded checks. They are not theorem
claims.

## Required Context For Published Results

Every public result should include or link to:

- Engine name and version or commit SHA.
- Exact command.
- Budget and target.
- RNG seed.
- Dependency lockfile or environment description.
- Full JSONL ledger when practical.
- Explanation of what the score means and what it does not mean.

If any of these are missing, label the result as a sample, demo, or illustrative
output.

## Language To Prefer

Use:

- "directed search"
- "candidate ranking"
- "near-miss score"
- "unrefuted at this budget"
- "bounded computation"
- "ledger"
- "replay"
- "numerical diagnostic"

Avoid:

- "proof-grade"
- "verified conjecture"
- "validated result"
- "truth signal"
- "FAANG-tier"
- "operator-grade"
- "breakthrough"
- "autonomous discovery"
- "guaranteed identical" unless the exact environment is pinned

## Frontend Copy Rules

The static site should not outrun the repository.

- Do not publish performance numbers unless there is a checked benchmark page
  or ledger behind them.
- Do not imply patent, enterprise, or production readiness unless the supporting
  material exists in the repo.
- Do not call browser demos verification engines. They are small inspectors.
- Keep investment and partnership copy minimal and factual.
- Preserve the distinction between ProofX and Germinal.

## Lean 4 Boundary

The root ProofX project now has a small Lean 4 package for bounded
certificates. Germinal remains a separate vendored Lean 4 experiment pipeline.

Root Lean artifacts are first-class source files. They require a pinned
toolchain, CI coverage, and no accepted `sorry` proofs. A Lean certificate may
support a finite claim, such as a concrete Collatz trajectory or a concrete
Goldbach witness. It does not upgrade a Python search result into a theorem
unless the exact theorem is stated and proved in Lean.

See [lean4.md](lean4.md) for the current certificate scope and acceptance bar.
