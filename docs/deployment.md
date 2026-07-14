# Deployment

ProofX's public site is static. The deployed artifact lives under `src/` at the
repository root: generated HTML pages, `nav.js`, static assets, and site source
subdirectories (`components/`, `pages/`, `scripts/`) live in the same tree.
There is no server-rendered application in the root project, and Vercel has no
configured build command; it serves the committed deploy files under `src/`
as-is.

Site sources live in `src/components/`, `src/pages/<slug>/`, and
`src/scripts/`. Page scripts may be authored as TypeScript beside the page
source, for example `src/pages/ledger-viewer/script.ts`; the build emits the
matching `script.js` before the static HTML is assembled. `scripts/build_site.py`
(via `scripts/build.sh` / `scripts/build.ps1`) assembles those inputs into
generated files at the `src/` root. Static deploy files such as
`src/styles.css`, `src/monitoring.js`, `src/results.json`, error pages, and
`src/assets/` are maintained directly at their served paths.

Edit site sources under `src/components/`, `src/pages/`, or `src/scripts/`,
then rebuild. Do not hand-edit generated files such as `src/index.html` or
`src/nav.js`; the next build overwrites them.

## Files In Scope

| Path | Role |
| --- | --- |
| `src/components/_head.html`, `_nav.html`, `_footer.html` | Shared partials substituted into every generated page. |
| `src/pages/<slug>/meta.json` + `content.html` [+ `script.ts` / generated `script.js`] | Per-page source; `slug` matches the output filename. |
| `src/scripts/nav.js` | Source for generated navigation behavior (`src/nav.js`). |
| `package.json`, `package-lock.json`, `tsconfig.json` | Lightweight TypeScript toolchain for interactive static page scripts. |
| `src/styles.css`, `src/monitoring.js`, `src/results.json`, `src/assets/`, error pages | Hand-authored or generated static deploy files served directly by Vercel. |
| `src/*.html`, `src/nav.js` | Generated deploy artifact committed for Vercel. |
| `vercel.json` | Static routing, redirects, and security headers. |

## Before Deploying

Rebuild the site from source, then run the static checks that are available
in the local environment:

```bash
npm install
./scripts/build.sh
./scripts/validate-links.sh
```

Also manually inspect changed pages in a browser when copy length changes. Some
site sections use existing card widths and long headings can wrap poorly.

## Routing Notes

`vercel.json` controls extensionless routes such as `/collatzx` and `/results`.
Do not change rewrites or security headers as part of content-only work.

## Public-Claim Checklist

Before publishing a page, check that it does not:

- claim a conjecture has been proved or verified;
- publish unsupported throughput or range figures;
- describe demos as formal verification;
- imply enterprise readiness or IP status without evidence;
- hide failed or inconclusive runs.

When a result is illustrative, say so. When it comes from a real run, link the
ledger or include the reproduction command.
