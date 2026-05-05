from typing import Annotated, Literal, TypedDict
from typing import Any

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class AgentState(TypedDict, total=False):
    issue: dict[str, Any]
    code_context: list[dict[str, Any]]
    plan: list[str]
    patch: str
    tests: str
    test_result: Literal["pass", "fail", "unrun"]
    test_log: str
    pr_url: str
    retries: int
    messages: Annotated[list[BaseMessage], add_messages]
    errors: list[str]
    run_dir: str
    repo_dir: str
    base_branch: str
    head_branch: str
    commit_sha: str
