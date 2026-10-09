# Quality scope

The root test suite enforces 60% coverage over the configured included modules.
That percentage does not describe every Python file in the repository. The
exclusions in `pyproject.toml` predate the research workbench; their original
per-module justification is not recorded, so this document does not invent one.

The benchmark runner and verifier are included in lint, formatting, types, and
coverage. Their tests cover exact small counts, reproducible ledgers, equal
budgets, exhausted candidate families, malformed configurations, immutable
output directories, independent recounting, corrupted artifacts, and the CLI.
Calibration tests cover held-out metrics, invalid labels, and the probability-1
ECE boundary. These checks are implementation evidence, not research validation.

| Area | Current gate exclusions | Work required before treating it as supported |
| --- | --- | --- |
| Collatz Bifurcation, Boundary, Pipeline, PrimeGraph, Processing, RareEvent | lint, types, coverage | Establish a runnable example and reference-output tests per module; then remove exclusions in separate reviewed changes. |
| Goldbach GoldbachReasoner, MetaVariant, SequenceGenerator | lint, types, coverage | Separate diagnostic or symbolic claims from exact computations; add fixtures and public API tests. |
| Riemann ContourTruth, PrimeEchos, TuringThreshold, ZeroProperties, ZetaMirror | lint, types, coverage | Document precision, algorithm assumptions, and independent numerical comparisons; remove placeholder verification/signing claims. |
| Unified CLI | types, coverage | Add command-level contract tests for legacy commands; benchmark execution already has a subprocess integration test. |
| Germinal | separate project | Use its own toolchain, tests, and operating rules. |

No exclusions or coverage thresholds were expanded for the workbench. For new
experiments, publish a protocol and checker, then add one small reference case
before a large run. A model-generated explanation or a passing test suite is
not a replacement for reviewing the mathematical definition being implemented.
