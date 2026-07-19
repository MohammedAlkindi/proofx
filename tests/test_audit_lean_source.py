"""Tests for the Lean source pre-scan.

The scan exists to fail fast on a barred construct. Its failure mode that
matters is the false positive: a check that flags the documentation explaining
why `native_decide` is barred gets ignored, and an ignored check is worse than
none. Most of these tests pin that behaviour.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))

from audit_lean_source import scan_file, strip_comments


class TestStripComments:
    def test_removes_line_comments(self):
        assert "sorry" not in strip_comments("def f := 1 -- sorry\n")

    def test_removes_block_comments(self):
        assert "sorry" not in strip_comments("/- sorry -/\ndef f := 1\n")

    def test_removes_doc_comments(self):
        assert "native_decide" not in strip_comments("/-- uses native_decide -/\ndef f := 1\n")

    def test_handles_nested_block_comments(self):
        source = "/- outer /- inner sorry -/ still comment -/\ndef f := 1\n"
        assert "sorry" not in strip_comments(source)
        assert "def f" in strip_comments(source)

    def test_preserves_code(self):
        assert "def f := 1" in strip_comments("def f := 1 -- note\n")

    def test_preserves_line_positions(self):
        source = "line1\n-- comment\nline3\n"
        assert len(strip_comments(source).splitlines()) == 3
        assert strip_comments(source).splitlines()[2] == "line3"

    def test_dashes_inside_code_are_not_a_comment(self):
        # A lone hyphen is not the start of a comment.
        assert "a - b" in strip_comments("def f := a - b\n")


class TestScanFile:
    def _write(self, tmp_path: Path, body: str) -> Path:
        path = tmp_path / "T.lean"
        path.write_text(body, encoding="utf-8")
        return path

    def test_flags_native_decide_in_code(self, tmp_path: Path):
        path = self._write(tmp_path, "theorem t : True := by\n  native_decide\n")
        findings = scan_file(path)
        assert len(findings) == 1
        assert findings[0][0] == 2
        assert findings[0][1] == "native_decide"

    def test_flags_sorry(self, tmp_path: Path):
        assert scan_file(self._write(tmp_path, "def f := sorry\n"))

    @pytest.mark.parametrize("token", ["sorry", "admit", "axiom", "unsafe", "native_decide"])
    def test_flags_each_barred_token(self, tmp_path: Path, token: str):
        assert scan_file(self._write(tmp_path, f"def f := {token}\n"))

    def test_ignores_tokens_in_comments(self, tmp_path: Path):
        body = (
            "/-- We bar `native_decide` because it trusts the compiler,\n"
            "and `sorry` because it admits anything. -/\n"
            "theorem t : 1 = 1 := by\n  rfl\n"
        )
        assert scan_file(self._write(tmp_path, body)) == []

    def test_ignores_token_as_substring(self, tmp_path: Path):
        # `decide` is fine; only `native_decide` is barred. Word boundaries.
        assert scan_file(self._write(tmp_path, "theorem t : 1 = 1 := by decide\n")) == []

    def test_reports_original_line_text_not_the_blanked_one(self, tmp_path: Path):
        path = self._write(tmp_path, "theorem t : True := by\n  native_decide\n")
        assert scan_file(path)[0][2] == "native_decide"


class TestRealSources:
    def test_repo_lean_sources_are_clean(self):
        root = Path(__file__).parents[1]
        findings = []
        for path in sorted((root / "ProofX").rglob("*.lean")):
            if path.name == "Audit.lean":
                continue  # necessarily names the axioms it allows
            findings.extend((path.name, *f) for f in scan_file(path))
        assert findings == [], f"barred constructs in committed Lean: {findings}"
