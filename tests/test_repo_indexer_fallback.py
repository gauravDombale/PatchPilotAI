from __future__ import annotations

from pathlib import Path

from resolver.tools.repo_indexer import RepoIndexer


def test_local_retrieval_fallback_returns_context_when_no_query_match(tmp_path: Path) -> None:
    repo_dir = tmp_path / "repo"
    app_dir = repo_dir / "app"
    tests_dir = repo_dir / "tests"
    app_dir.mkdir(parents=True, exist_ok=True)
    tests_dir.mkdir(parents=True, exist_ok=True)

    (app_dir / "validators.py").write_text("def is_valid_email(x):\n    return '+' in x\n", encoding="utf-8")
    (tests_dir / "test_app.py").write_text("def test_x():\n    assert True\n", encoding="utf-8")

    docs = RepoIndexer()._retrieve_local(query="no-match-term-123", repo_dir=repo_dir, k=4)
    assert len(docs) > 0
    assert any(str(d.metadata.get("path", "")).startswith("app/") for d in docs)


def test_collect_files_excludes_virtualenv_content(tmp_path: Path) -> None:
    repo_dir = tmp_path / "repo"
    app_dir = repo_dir / "app"
    venv_dir = repo_dir / ".venv" / "lib"
    app_dir.mkdir(parents=True, exist_ok=True)
    venv_dir.mkdir(parents=True, exist_ok=True)

    (app_dir / "validators.py").write_text("def is_valid_email(x):\n    return True\n", encoding="utf-8")
    (venv_dir / "noise.py").write_text("def should_not_be_seen():\n    return False\n", encoding="utf-8")

    files = RepoIndexer()._collect_files(repo_dir)
    rel_paths = {str(path.relative_to(repo_dir)) for path in files}
    assert "app/validators.py" in rel_paths
    assert ".venv/lib/noise.py" not in rel_paths
