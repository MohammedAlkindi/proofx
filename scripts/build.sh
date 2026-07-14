#!/usr/bin/env bash
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

PY=python3
python3 --version >/dev/null 2>&1 || PY=python

npm --prefix "$root" run build:ts
"$PY" "$root/scripts/build_site.py"
