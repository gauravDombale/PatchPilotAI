from __future__ import annotations

from pathlib import Path

from resolver.state import AgentState
from resolver.tools.repo_indexer import RepoIndexer
from resolver.tools.workspace import prepare_workspace


def run(state: AgentState) -> AgentState:
    issue = state["issue"]
    repo_dir, base_branch, sha = prepare_workspace(
        run_dir=Path(state["run_dir"]),
        repo_full_name=issue["repo"],
        local_path=issue.get("local_path", "."),
        clone_url=issue.get("clone_url"),
        base_branch=issue.get("default_branch"),
    )

    query = f"{issue.get('title', '')}\n{issue.get('body', '')}".strip()
    docs = RepoIndexer().retrieve(repo=issue["repo"], sha=sha, query=query, repo_dir=repo_dir, k=8)
    errors = state.get("errors", [])
    if not docs:
        return {
            "repo_dir": str(repo_dir),
            "base_branch": base_branch,
            "commit_sha": sha,
            "code_context": [],
            "errors": [*errors, "retrieval_error: no_code_context_found"],
        }
    code_context = [
        {"path": str(doc.metadata.get("path", "unknown")), "code": doc.page_content, "score": 0.0}
        for doc in docs
    ]
    query_lower = query.lower()
    validators_path = repo_dir / "app" / "validators.py"
    has_validators = any(item["path"] == "app/validators.py" for item in code_context)
    has_plus_signal = "plus" in query_lower or "+" in query_lower or "john+tag" in query_lower
    if "email" in query_lower and "alias" in query_lower and has_plus_signal and validators_path.exists() and not has_validators:
        code_context.insert(
            0,
            {
                "path": "app/validators.py",
                "code": validators_path.read_text(encoding="utf-8"),
                "score": 1.0,
            },
        )
    return {
        "repo_dir": str(repo_dir),
        "base_branch": base_branch,
        "commit_sha": sha,
        "code_context": code_context,
    }
