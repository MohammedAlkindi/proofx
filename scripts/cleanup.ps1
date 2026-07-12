param(
    [switch]$Deep
)

$ErrorActionPreference = "Stop"
$root = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path

$targets = @(
    ".cache",
    ".logs",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".hypothesis",
    ".tox",
    ".nox",
    "htmlcov",
    "build",
    "dist",
    ".coverage",
    "coverage.xml"
)

if ($Deep) {
    $targets += @(".venv", "frontend")
}

foreach ($relative in $targets) {
    $candidate = Join-Path $root $relative
    if (-not (Test-Path -LiteralPath $candidate)) {
        continue
    }

    $resolved = (Resolve-Path -LiteralPath $candidate).Path
    if (-not ($resolved.Equals($root, [System.StringComparison]::OrdinalIgnoreCase) -or $resolved.StartsWith($root + [System.IO.Path]::DirectorySeparatorChar, [System.StringComparison]::OrdinalIgnoreCase))) {
        throw "Refusing to remove outside repository: $resolved"
    }

    Remove-Item -LiteralPath $resolved -Recurse -Force
}

$pycacheDirs = Get-ChildItem -LiteralPath $root -Recurse -Force -Directory -Filter "__pycache__" |
    Where-Object {
        $_.FullName.StartsWith($root + [System.IO.Path]::DirectorySeparatorChar, [System.StringComparison]::OrdinalIgnoreCase) -and
        -not $_.FullName.StartsWith((Join-Path $root ".git") + [System.IO.Path]::DirectorySeparatorChar, [System.StringComparison]::OrdinalIgnoreCase)
    }
foreach ($dir in $pycacheDirs) {
    Remove-Item -LiteralPath $dir.FullName -Recurse -Force
}

$fileNames = @(".DS_Store", "Thumbs.db")
foreach ($name in $fileNames) {
    Get-ChildItem -LiteralPath $root -Recurse -Force -File -Filter $name |
        Where-Object {
            $_.FullName.StartsWith($root + [System.IO.Path]::DirectorySeparatorChar, [System.StringComparison]::OrdinalIgnoreCase) -and
            -not $_.FullName.StartsWith((Join-Path $root ".git") + [System.IO.Path]::DirectorySeparatorChar, [System.StringComparison]::OrdinalIgnoreCase)
        } |
        ForEach-Object { Remove-Item -LiteralPath $_.FullName -Force }
}

Get-ChildItem -LiteralPath $root -Recurse -Force -File -Filter "*.pyc" |
    Where-Object {
        $_.FullName.StartsWith($root + [System.IO.Path]::DirectorySeparatorChar, [System.StringComparison]::OrdinalIgnoreCase) -and
        -not $_.FullName.StartsWith((Join-Path $root ".git") + [System.IO.Path]::DirectorySeparatorChar, [System.StringComparison]::OrdinalIgnoreCase)
    } |
    ForEach-Object { Remove-Item -LiteralPath $_.FullName -Force }
