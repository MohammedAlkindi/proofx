#!/usr/bin/env bash
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$root"

PY=python3
python3 --version >/dev/null 2>&1 || PY=python

export PYTHONUTF8=1

"$PY" -m codebase.cli falsify \
  --budget 500 \
  --seed 42 \
  --target both \
  --top-k 25 \
  --save-ledger results/ledger.jsonl \
  --output-json src/static/results.json

"$PY" "$root/scripts/build_site.py"
