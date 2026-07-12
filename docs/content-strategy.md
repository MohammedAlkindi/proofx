# Content Strategy

ProofX copy should sound like a careful research notebook, not a pitch deck.

## Voice

Use plain, specific language:

- "This run evaluated 500 candidates."
- "The candidate converged to 1 in 949 steps."
- "No counterexample was found at this budget."
- "The browser demo is capped for responsiveness."

Avoid broad claims:

- "proof-grade"
- "operator-grade"
- "world-class"
- "FAANG-tier"
- "breakthrough"
- "guaranteed"
- "validated conjecture"

## Page Roles

| Page | Job |
| --- | --- |
| Home | Explain what ProofX is and set expectations. |
| Engine pages | Describe the engine and provide bounded demos. |
| Results | Show sample or ledger-backed results with reproduction context. |
| Research | Link docs, assumptions, and collaboration paths. |
| Roadmap | State concrete engineering tasks, not grand milestones. |
| Contact | Offer a direct way to discuss research or code. |

## Result Copy Template

Use this pattern for public result summaries:

```text
This table is from `<command>` at seed `<seed>` with budget `<budget>`.
It reports the highest-scoring candidates found by the configured strategy.
No counterexample was found in this run. This is not a proof of the conjecture.
```

## Browser Demo Copy

Browser demos should be framed as small inspectors. They are useful for
education and quick checks, but they are not the same as the Python engine or a
formal proof system.

## Maintenance

When engine behavior changes, update docs and public copy together. If a page
uses a number, make sure the number can be traced to a command, ledger, paper, or
source comment.
