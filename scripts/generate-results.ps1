$ErrorActionPreference = "Stop"
$root = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
Set-Location $root

$env:PYTHONUTF8 = "1"

python -m codebase.cli falsify `
  --budget 500 `
  --seed 42 `
  --target both `
  --top-k 25 `
  --save-ledger results/ledger.jsonl `
  --output-json src/static/results.json

python "$root/scripts/build_site.py"
