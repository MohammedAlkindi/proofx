# ProofX

ProofX is a static, research-focused web surface for presenting conjecture-engine work, findings, and collaboration information.

## Project Structure

```text
ProofX/
├── public/
├── src/
├── docs/
├── scripts/
├── .gitignore
├── README.md
├── vercel.json
└── LICENSE
```

- `public/`: deploy-ready pages, assets, PDF, and sitemap.
- `src/`: source styles/scripts/components/content.
- `docs/`: architecture, content strategy, and deployment notes.
- `scripts/`: helper scripts for build, link validation, and cleanup.

## Local Checks

```bash
./scripts/build.sh
./scripts/validate-links.sh
```

## Deployment

Deploy as a static site on Vercel or any static host.
