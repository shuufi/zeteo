from __future__ import annotations

from pathlib import Path
import subprocess
import sys


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_admin_script_runs_when_executed_by_path():
    completed = subprocess.run(
        [sys.executable, "backend/scripts/admin.py"],
        cwd=REPO_ROOT,
        input="0\n",
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    assert "Zeteo Admin" in completed.stdout
