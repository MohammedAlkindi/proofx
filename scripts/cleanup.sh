#!/usr/bin/env bash
set -euo pipefail

deep=false
if [[ "${1:-}" == "--deep" ]]; then
  deep=true
fi

rm -rf \
  .cache \
  .logs \
  .mypy_cache \
  .pytest_cache \
  .ruff_cache \
  .hypothesis \
  .tox \
  .nox \
  htmlcov \
  build \
  dist \
  .coverage \
  coverage.xml

if [[ "$deep" == true ]]; then
  rm -rf .venv frontend
fi

find . -path './.git' -prune -o -type d -name '__pycache__' -prune -exec rm -rf {} +
find . -path './.git' -prune -o \( -name '.DS_Store' -o -name 'Thumbs.db' -o -name '*.pyc' \) -type f -delete
