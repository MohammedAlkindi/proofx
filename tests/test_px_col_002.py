"""Run the frozen experimental policy's semantic tests without changing its bytes."""

import subprocess
import sys
import zipfile
from pathlib import Path


def test_frozen_prefix_policy_semantics(tmp_path):
    bundle = Path(__file__).resolve().parents[1] / "src/experiments/px-col-002/bundle.zip"
    with zipfile.ZipFile(bundle) as archive:
        for name in ("policy.py", "sampler.py", "test_policy.py"):
            (tmp_path / name).write_bytes(archive.read(name))
    completed = subprocess.run(
        [sys.executable, "-m", "unittest", "-v", "test_policy"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert "Ran 8 tests" in completed.stderr
