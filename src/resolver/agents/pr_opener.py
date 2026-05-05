from __future__ import annotations

from pathlib import Path

from git import Repo

from resolver.state import AgentState
from resolver.tools.github_tools import GitHubTools


def run(state: AgentState) -> AgentState:
    issue = state["issue"]
    repo_dir = Path(state["repo_dir"])
    repo = Repo(repo_dir)
    github_tools = GitHubTools()

    run_suffix = Path(state["run_dir"]).name[:8]
    branch = f"bot/issue-{issue['number']}-{run_suffix}"
    repo.git.checkout("-B", branch)

    if repo.is_dirty(untracked_files=True):
        repo.git.add(A=True)
        repo.index.commit(f"fix: resolve issue #{issue['number']}")

    pushed = False
    errors = state.get("errors", [])
    try:
        auth_url = github_tools.get_authenticated_clone_url(
            repo_full_name=issue["repo"],
            clone_url=issue.get("clone_url"),
        )
        if auth_url:
            if "origin" in [remote.name for remote in repo.remotes]:
                repo.git.remote("set-url", "--push", "origin", auth_url)
            else:
                repo.create_remote("origin", auth_url)
        repo.git.push("--set-upstream", "origin", branch)
        pushed = True
    except Exception as exc:
        pushed = False
        errors = [*errors, f"push_failed: {exc}"]

    pr_title = f"fix: resolve issue #{issue['number']}"
    pr_body = f"Automated fix for issue #{issue['number']}\n\nCloses #{issue['number']}"
    pr_url = github_tools.open_pr(
        repo_full_name=issue["repo"],
        branch=branch,
        title=pr_title,
        body=pr_body,
        base=state.get("base_branch", "main"),
    )

    if not pushed and not any(err.startswith("push_failed:") for err in errors):
        errors = [*errors, "push_failed: branch commit created locally; remote push unavailable"]

    return {"pr_url": pr_url, "head_branch": branch, "errors": errors}
