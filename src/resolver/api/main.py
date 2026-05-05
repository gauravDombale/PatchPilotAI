from __future__ import annotations

import json
from collections.abc import AsyncGenerator
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from github.GithubException import GithubException, UnknownObjectException
from pydantic import BaseModel

from resolver.config import configure_runtime_env, get_settings
from resolver.graph import build_graph
from resolver.tools.github_tools import GitHubTools

configure_runtime_env()

app = FastAPI(title="Multi-Agent Issue Resolver")
graph = build_graph()


class ResolveRequest(BaseModel):
    repo: str
    issue_number: int
    local_path: str = "."


@app.post("/resolve")
async def resolve(req: ResolveRequest) -> StreamingResponse:
    try:
        issue = GitHubTools().get_issue(req.repo, req.issue_number)
    except UnknownObjectException as exc:
        raise HTTPException(
            status_code=404,
            detail=f"Issue not found or token lacks access for {req.repo}#{req.issue_number}",
        ) from exc
    except GithubException as exc:
        code = exc.status if isinstance(exc.status, int) and exc.status > 0 else 502
        raise HTTPException(
            status_code=code,
            detail=f"GitHub API error while reading issue: {exc.data}",
        ) from exc
    thread_id = str(uuid4())
    settings = get_settings()
    run_dir = Path(settings.work_dir) / thread_id
    run_dir.mkdir(parents=True, exist_ok=True)

    initial_state = {
        "issue": {
            "repo": issue.repo,
            "number": issue.number,
            "title": issue.title,
            "body": issue.body,
            "clone_url": issue.clone_url,
            "default_branch": issue.default_branch,
            "local_path": req.local_path,
        },
        "test_result": "unrun",
        "retries": 0,
        "errors": [],
        "run_dir": str(run_dir),
    }

    async def events() -> AsyncGenerator[str, None]:
        async for event in graph.astream(
            initial_state,
            config={"configurable": {"thread_id": thread_id}},
            stream_mode="updates",
        ):
            yield f"data: {json.dumps(event, default=str)}\n\n"

    return StreamingResponse(events(), media_type="text/event-stream", headers={"x-thread-id": thread_id})


@app.get("/runs/{thread_id}")
async def get_run(thread_id: str) -> dict[str, object]:
    snapshot = graph.get_state(config={"configurable": {"thread_id": thread_id}})
    return {"thread_id": thread_id, "state": snapshot.values if snapshot else {}}
