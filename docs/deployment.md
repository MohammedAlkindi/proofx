# Deployment

ProofX's public site is static. The deployed artifact is the `public/`
directory. There is no server-rendered application in the root project.

## Files In Scope

| Path | Role |
| --- | --- |
| `public/*.html` | Deployed pages. |
| `public/styles.css` | Shared deployed stylesheet. Preserve unless the task is visual design. |
| `public/monitoring.js` | Client-side monitoring hook. |
| `public/assets/` | Icons, PDFs, and other static assets. |
| `vercel.json` | Static routing, redirects, and security headers. |

## Before Deploying

Run the static checks that are available in the local environment:

```bash
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
