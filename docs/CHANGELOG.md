# Changelog

All notable changes to ProofX are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versioning follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- `codebase/lean_export.py` and `python -m codebase.cli export lean`, turning ledger rows into kernel-checkable Lean certificates with a deterministic, provenance-stamped generated module
- `ProofX/Generated/LedgerCertificates.lean`, 500 generated theorems covering the `--seed 42 --budget 500` ledger
- `ProofX/Audit.lean`, a build-time axiom audit that fails `lake build` if any theorem in the `ProofX` namespace depends on an axiom outside `propext`, `Classical.choice`, and `Quot.sound`
- `ProofX.IsPrime` and `isPrime_of_isPrimeWithBound`, proving that an exporter-supplied divisor bound discharges primality without a Mathlib dependency
- `details.witness` on Goldbach ledger rows, recording the prime pair the search found
- `LEDGER_SCHEMA_VERSION` (`proofx.ledger.v2`); rows previously carried no version field
- `certificates` job in `ci.yml`, regenerating the ledger from seed and failing on certificate drift
- `tests/` directory with unit tests for CollatzX, GoldbachX, and ReimannX engines

### Changed
- Lean certificates close with `decide` rather than `native_decide`, so the kernel rather than the compiler checks them, and are named theorems rather than anonymous examples so `#print axioms` can reach them
- `goldbachPair` takes the two trial-division bounds as additional arguments

### Fixed
- `native_decide` widened the trusted computing base to the Lean compiler and runtime via `Lean.ofReduceBool` and `Lean.trustCompiler` while passing the documented `rg` audit, which scans for tokens that the tactic never introduces
- `pyproject.toml` with packaging metadata plus pytest, mypy, and ruff configuration
- `.pre-commit-config.yaml` with ruff, mypy, and standard file hygiene hooks
- `.github/workflows/ci.yml` with lint, format, type-check, and test jobs for Python 3.13
- `.github/workflows/lean.yml` with a Lake build for the root Lean package
- `.github/dependabot.yml` with automated weekly dependency updates for pip and GitHub Actions
- `requirements-dev.txt` for pytest, coverage, ruff, and mypy
- `scripts/cleanup.ps1` and expanded `scripts/cleanup.sh` for local cache and scratch-folder cleanup
- `packages/README.md` documenting Germinal as an isolated vendored package
- `src/monitoring.js` for frontend error tracking (opt-in via `window.__SENTRY_DSN__`)
- Sentry `<script>` tag injected into all main public pages
- Pinned versions for all runtime Python dependencies in `requirements.txt`

---

## [0.3.0] - 2026-04-18

### Added
- User-friendly auth/error pages (`auth-error.html`, HTTP 400-501)
- Consolidated markdown documentation under `/docs`

## [0.2.0] - 2025-12-01

### Added
- CollatzX engine: advanced analytics, bifurcation analysis, boundary detection, rare event detection
- GoldbachX engine: symbolic reasoner, partition enumerator, sieve engine, sequence generator
- ReimannX engine: contour truth scanner, Keiper-Li coefficients, prime echos, Turing threshold, zero properties, zeta mirror

### Changed
- Migrated from single-file scripts to modular engine architecture

## [0.1.0] - 2025-09-01

### Added
- Initial ProofX static site deployed on Vercel
- Research pages for Collatz, Goldbach, and Riemann conjectures
- Security headers via `vercel.json` (X-Frame-Options, nosniff, Referrer-Policy)

[Unreleased]: https://github.com/MohammedAlkindi/ProofX/compare/v0.3.0...HEAD
[0.3.0]: https://github.com/MohammedAlkindi/ProofX/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/MohammedAlkindi/ProofX/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/MohammedAlkindi/ProofX/releases/tag/v0.1.0
