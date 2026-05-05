from pathlib import Path

from resolver.graph import build_graph


def test_graph_smoke(tmp_path: Path) -> None:
    graph = build_graph()
    source_repo = tmp_path / "source"
    source_repo.mkdir(parents=True, exist_ok=True)
    (source_repo / "app.py").write_text("def add(a, b):\n    return a + b\n", encoding="utf-8")
    run_dir = tmp_path / "run"
    run_dir.mkdir(parents=True, exist_ok=True)

    out = graph.invoke(
        {
            "issue": {
                "repo": "owner/repo",
                "number": 1,
                "title": "sample",
                "body": "sample body",
                "local_path": str(source_repo),
            },
            "test_result": "unrun",
            "retries": 0,
            "errors": [],
            "run_dir": str(run_dir),
        },
        config={"configurable": {"thread_id": "smoke-1"}},
    )
    assert "test_result" in out
