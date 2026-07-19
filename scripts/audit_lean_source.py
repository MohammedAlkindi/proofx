#!/usr/bin/env python3
"""Scan Lean sources for barred constructs, ignoring comments.

This is the fast textual pre-check, not the gate. The real enforcement is
`ProofX/Audit.lean`, which walks each declaration's actual axiom dependencies
during `lake build` and therefore sees constructs a textual scan cannot -- an
axiom introduced by a tactic, for instance.

A naive `rg` for these tokens matches the prose in doc comments that explains
why they are barred, which is why this strips comments first. A check that
cries wolf on its own documentation gets ignored, and an ignored check is worse
than no check.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

BARRED = ("sorry", "admit", "axiom", "unsafe", "native_decide")

DEFAULT_TARGETS = ("ProofX", "ProofX.lean", "lakefile.lean")

# `axiom` is legitimate inside the audit module itself, which necessarily names
# the axioms it allows.
EXEMPT = {Path("ProofX/Audit.lean")}


def strip_comments(source: str) -> str:
    """Blank out Lean comments, preserving line and column positions.

    Handles `--` line comments and nestable `/- -/` block comments, including
    the `/-- -/` doc form. Characters are replaced with spaces rather than
    removed so reported line numbers still match the file.
    """
    out = list(source)
    i = 0
    depth = 0
    n = len(source)
    while i < n:
        if depth == 0 and source.startswith("--", i):
            while i < n and source[i] != "\n":
                out[i] = " "
                i += 1
        elif source.startswith("/-", i):
            depth += 1
            out[i] = out[i + 1] = " "
            i += 2
        elif depth > 0 and source.startswith("-/", i):
            depth -= 1
            out[i] = out[i + 1] = " "
            i += 2
        elif depth > 0:
            if source[i] != "\n":
                out[i] = " "
            i += 1
        else:
            i += 1
    return "".join(out)


def scan_file(path: Path) -> list[tuple[int, str, str]]:
    """Return (line number, token, line text) for each barred token in code."""
    source = path.read_text(encoding="utf-8")
    code = strip_comments(source)
    original = source.splitlines()
    findings: list[tuple[int, str, str]] = []
    for lineno, line in enumerate(code.splitlines(), start=1):
        for token in BARRED:
            if re.search(rf"\b{re.escape(token)}\b", line):
                findings.append((lineno, token, original[lineno - 1].strip()))
    return findings


def iter_lean_files(targets: list[str]) -> list[Path]:
    files: list[Path] = []
    for target in targets:
        path = Path(target)
        if path.is_dir():
            files.extend(sorted(path.rglob("*.lean")))
        elif path.suffix == ".lean" and path.exists():
            files.append(path)
    return files


def main(argv: list[str]) -> int:
    targets = argv[1:] or list(DEFAULT_TARGETS)
    failed = False
    for path in iter_lean_files(targets):
        if Path(*path.parts) in EXEMPT:
            continue
        for lineno, token, text in scan_file(path):
            print(f"{path.as_posix()}:{lineno}: barred construct `{token}`: {text}")
            failed = True

    if failed:
        print("\nSee docs/lean4.md. Proofs must be kernel-checked.", file=sys.stderr)
        return 1
    print("No barred constructs in Lean sources.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
