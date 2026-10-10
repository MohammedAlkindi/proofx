"""Goldbach-only workflows should not load the Collatz analytics stack."""

import subprocess
import sys


def test_goldbach_does_not_import_collatz_analytics():
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import sys; "
            "from codebase.FalsificationEngine.FalsificationEngine import GoldbachFalsifier; "
            "assert GoldbachFalsifier(sieve_limit=10)._partition_count_and_witness(10)[0] == 2; "
            "assert 'codebase.CollatzX.Analytics.Analytics' not in sys.modules; "
            "assert 'torch' not in sys.modules",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=90,
    )
    assert result.returncode == 0, result.stdout + result.stderr
