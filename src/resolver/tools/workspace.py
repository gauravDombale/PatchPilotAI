from __future__ import annotations

import shutil
from pathlib import Path

from git import InvalidGitRepositoryError, Repo


def prepare_workspace(
    run_dir: Path,
    repo_full_name: str,
    local_path: str,
    clone_url: str | None,
    base_branch: str | None,
) -> tuple[Path, str, str]:
    repo_dir = run_dir / "repo"
    if repo_dir.exists():
        shutil.rmtree(repo_dir)

    candidate_local = Path(local_path).resolve()
    if local_path not in {"", "."} and candidate_local.exists():
        shutil.copytree(candidate_local, repo_dir)
        try:
            repo = Repo(repo_dir)
        except InvalidGitRepositoryError:
            repo = Repo.init(repo_dir)
            repo.index.add(["."])
            repo.index.commit("chore: initialize local workspace for resolver")
    else:
        if not clone_url:
            clone_url = f"https://github.com/{repo_full_name}.git"
        repo = Repo.clone_from(clone_url, repo_dir)

    selected_base = base_branch or _detect_base_branch(repo)
    if selected_base in repo.heads:
        repo.git.checkout(selected_base)
    sha = repo.head.commit.hexsha
    return repo_dir, selected_base, sha


def _detect_base_branch(repo: Repo) -> str:
    for name in ("main", "master"):
        if name in repo.heads:
            return name
    return repo.active_branch.name
