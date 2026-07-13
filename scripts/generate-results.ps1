$ErrorActionPreference = "Stop"
$root = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
Set-Location $root

$env:PYTHONUTF8 = "1"
$pythonPackageRoot = Join-Path $root "packages/python"
$env:PYTHONPATH = if ($env:PYTHONPATH) {
  "$pythonPackageRoot$([IO.Path]::PathSeparator)$env:PYTHONPATH"
} else {
  $pythonPackageRoot
}

python -m codebase.cli falsify `
  --budget 500 `
  --seed 42 `
  --target both `
  --top-k 25 `
  --save-ledger results/ledger.jsonl `
  --output-json src/results.json

python "$root/scripts/build_site.py"
