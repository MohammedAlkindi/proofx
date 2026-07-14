$ErrorActionPreference = "Stop"
$root = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path

npm --prefix "$root" run build:ts
python "$root/scripts/build_site.py"
