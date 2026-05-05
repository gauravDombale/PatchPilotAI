from resolver.state import AgentState


def test_state_typing_shape() -> None:
    state: AgentState = {
        "issue": {"repo": "a/b", "number": 1, "title": "t", "body": "b"},
        "test_result": "unrun",
    }
    assert state["issue"]["number"] == 1
