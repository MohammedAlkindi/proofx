# GB-002 implementation handoff

Branch: `codex/feat-controlled-experiments`.
Review: https://github.com/MohammedAlkindi/proofx/pull/57
This work requires review and merge; it is not a claim that production already
serves the new page. The previous GB-001 work was merged in pull request 56.

## Durable record

- `gb-002-protocol.md`: prospective design, committed at `63bedbc` before outcomes.
- `gb-002-results.md`: outcomes, negative findings, interpretation, reproduction.
- `packages/python/codebase/protocols/gb-002-v1.json`: executable protocol record.
- `packages/python/codebase/protocols/registry.json`: versioned artifact identity.
- `src/experiments/gb-002/`: analysis, manifest, protocol, complete ZIP containing
  raw selections, reference inputs, and implementation snapshots.
- `study.py`, `study_stats.py`, `study_check.py`: generation, exact moments,
  separate arithmetic check. `experiments.py`: safe extraction and reproduction.
- `src/pages/research/`: source of the interactive study page. Rebuild generated
  HTML with `npm run build:ts` and `python scripts/build_site.py`.

## Validation completed locally

Python 3.13.13: 431 tests passed, 75.94% coverage. Ruff lint and formatting,
mypy, TypeScript compilation, research-page interaction tests, and 250 internal
link checks passed. The page was loaded in a real browser; interval/budget
selection and rendered results were checked. A full responsive or site-wide
security audit was not completed in this change.

A clean wheel installed outside the checkout with only ProofX and NumPy
reproduced both GB-001 and GB-002 with byte-identical scientific artifacts.
An independent implementation checked 3,000 counts/witnesses, 63 rational
means/variances, 54 contrasts, and all 43,008 replicate rows and their simulation
summaries. All 54 diagnostic intervals contained the exact contrasts.

The CI workflow also includes a Linux core-install reproduction job. Consult
the pull request's current checks for its latest result rather than inferring
CI status from this static note.

## Resume safely

Read `CLAUDE.md`, inspect Git status, and check pull request 57 before editing.
The pre-existing untracked `contextbill-report.html` is unrelated; leave it alone.
Do not alter the frozen study to improve results. A new domain or policy choice
requires a new protocol version and clear separation from these outcomes.

Next research question: prospectively evaluate the reduced policy on new
domains; removing twice-prime improved every current cell. Runtime efficiency
needs its own cost-controlled experiment. Neither result establishes progress
toward disproving Goldbach or guarantees a recruiting outcome.

Test environments used here live outside the checkout under
`C:/Users/alkin/wt/proofx-study-env` and `C:/Users/alkin/wt/proofx-core-check`.
Use a fresh explicit pytest `--basetemp` under `~/wt` if shared temporary-directory
cleanup stalls after tests finish. No credentials or external services are
required for reproduction from the checked-in ZIP.
