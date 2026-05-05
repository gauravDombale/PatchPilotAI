from __future__ import annotations

from typing import Any

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from resolver.agents import code_reader, code_writer, planner, pr_opener, test_writer
from resolver.state import AgentState


def route_after_tests(state: AgentState) -> str:
    if state.get("test_result") == "pass":
        return "pr_opener"
    if state.get("retries", 0) >= 2:
        return END
    return "planner"


def build_graph() -> Any:
    g = StateGraph(AgentState)
    g.add_node("code_reader", code_reader.run)
    g.add_node("planner", planner.run)
    g.add_node("code_writer", code_writer.run)
    g.add_node("test_writer", test_writer.run)
    g.add_node("pr_opener", pr_opener.run)

    g.add_edge(START, "code_reader")
    g.add_edge("code_reader", "planner")
    g.add_edge("planner", "code_writer")
    g.add_edge("code_writer", "test_writer")
    g.add_conditional_edges(
        "test_writer",
        route_after_tests,
        {"pr_opener": "pr_opener", "planner": "planner", END: END},
    )
    g.add_edge("pr_opener", END)

    return g.compile(checkpointer=MemorySaver())
