from __future__ import annotations

from typing import Any

from langchain_openai import ChatOpenAI
from pydantic import SecretStr
from pydantic import BaseModel

from resolver.config import get_settings
from resolver.state import AgentState


class PlanSchema(BaseModel):
    steps: list[str]


def _fallback_plan(state: AgentState) -> list[str]:
    issue = state["issue"]
    base = [
        f"Inspect relevant files for issue #{issue['number']}",
        "Apply a minimal targeted code fix",
        "Add regression tests for expected behavior",
        "Run pytest and iterate on failures",
    ]
    if state.get("test_result") == "fail":
        base.insert(0, "Analyze test failure log and revise patch strategy")
    return base


def run(state: AgentState) -> AgentState:
    settings = get_settings()
    if not settings.has_openai_key:
        return {"plan": _fallback_plan(state)}

    model = ChatOpenAI(
        model=settings.default_model,
        api_key=SecretStr(settings.openai_api_key.get_secret_value() if isinstance(settings.openai_api_key, SecretStr) else settings.openai_api_key),
        temperature=0,
        model_kwargs={"max_tokens": 2000},
        timeout=60,
    ).with_structured_output(PlanSchema)

    issue = state["issue"]
    context = "\n\n".join(f"{c['path']}\n{c['code'][:500]}" for c in state.get("code_context", []))
    prior_failure = state.get("test_log", "")[:2000]
    prompt = (
        f"Issue: {issue['title']}\n{issue.get('body','')}\n\n"
        f"Retrieved context:\n{context}\n\n"
        f"Prior pytest output (if any):\n{prior_failure}\n\n"
        "Return a short ordered implementation plan."
    )
    try:
        result: Any = model.invoke(prompt)
        return {"plan": result.steps}
    except Exception as exc:
        return {
            "plan": _fallback_plan(state),
            "errors": [*(state.get("errors", [])), f"planner_error: {exc}"],
        }
