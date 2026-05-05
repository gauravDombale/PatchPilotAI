from __future__ import annotations

import subprocess
from pathlib import Path


def check_unified_diff(repo_dir: Path, diff: str) -> tuple[bool, str]:
    proc = subprocess.run(
        ["git", "apply", "--check", "-"],
        cwd=repo_dir,
        input=diff,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    if proc.returncode == 0:
        return True, proc.stdout.strip()
    return False, proc.stdout.strip()


def apply_unified_diff(repo_dir: Path, diff: str) -> tuple[bool, str]:
    proc = subprocess.run(
        ["git", "apply", "--whitespace=fix", "-"],
        cwd=repo_dir,
        input=diff,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    if proc.returncode == 0:
        return True, proc.stdout.strip()
    return False, proc.stdout.strip()
