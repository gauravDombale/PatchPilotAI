from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Literal


def run_pytest(repo_dir: Path, test_target: str | None = None) -> tuple[Literal["pass", "fail"], str]:
    cmd = ["pytest", "-x"]
    if test_target:
        cmd.append(test_target)
    proc = subprocess.run(
        cmd,
        cwd=repo_dir,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        check=False,
    )
    return ("pass" if proc.returncode == 0 else "fail", proc.stdout)
