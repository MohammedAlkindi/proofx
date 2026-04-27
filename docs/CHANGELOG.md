# Changelog

All notable changes to ProofX are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versioning follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- `tests/` directory with unit tests for CollatzX, GoldbachX, and ReimannX engines
- `pyproject.toml` with pytest, mypy, and ruff configuration
- `.pre-commit-config.yaml` with ruff, mypy, and standard file hygiene hooks
- `.github/ci.yml` — full CI pipeline: lint, type-check, test (Python 3.10/3.11), security audit
- `.github/dependabot.yml` — automated weekly dependency updates for pip and GitHub Actions
- `public/monitoring.js` — Sentry frontend error tracking (opt-in via `window.__SENTRY_DSN__`)
- Sentry `<script>` tag injected into all main public pages
- Pinned versions for all 19 Python dependencies in `requirements.txt`

---

## [0.3.0] — 2026-04-18

### Added
- User-friendly auth/error pages (`auth-error.html`, HTTP 400–501)
- Consolidated markdown documentation under `/docs`

## [0.2.0] — 2025-12-01

### Added
- CollatzX engine: advanced analytics, bifurcation analysis, boundary detection, rare event detection
- GoldbachX engine: symbolic reasoner, partition enumerator, sieve engine, sequence generator
- ReimannX engine: contour truth scanner, Keiper-Li coefficients, prime echos, Turing threshold, zero properties, zeta mirror

### Changed
- Migrated from single-file scripts to modular engine architecture

## [0.1.0] — 2025-09-01

### Added
- Initial ProofX static site deployed on Vercel
- Research pages for Collatz, Goldbach, and Riemann conjectures
- Security headers via `vercel.json` (X-Frame-Options, nosniff, Referrer-Policy)

[Unreleased]: https://github.com/MohammedAlkindi/ProofX/compare/v0.3.0...HEAD
[0.3.0]: https://github.com/MohammedAlkindi/ProofX/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/MohammedAlkindi/ProofX/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/MohammedAlkindi/ProofX/releases/tag/v0.1.0
