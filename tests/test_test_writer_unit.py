from __future__ import annotations

from pathlib import Path

from _pytest.monkeypatch import MonkeyPatch

import resolver.agents.test_writer as test_writer


def test_normalize_python_source_strips_markdown_fences() -> None:
    src = """```python\nimport pytest\n\ndef test_x():\n    assert True\n```"""
    out = test_writer.normalize_python_source(src)
    assert "```" not in out
    assert "def test_x" in out


def test_run_handles_fenced_generation_without_syntax_error(
    tmp_path: Path, monkeypatch: MonkeyPatch
) -> None:
    repo_dir = tmp_path / "repo"
    repo_dir.mkdir(parents=True, exist_ok=True)
    (repo_dir / "pyproject.toml").write_text("[project]\nname='x'\nversion='0.0.1'\n", encoding="utf-8")

    class FakeSettings:
        default_model = "gpt-4o-mini"
        openai_api_key = "sk-test"
        has_openai_key = True

    class FakeResp:
        content = """```python\nimport pytest\n\ndef test_generated():\n    assert True\n```"""

    class FakeModel:
        def invoke(self, _prompt: str) -> FakeResp:
            return FakeResp()

    monkeypatch.setattr(test_writer, "get_settings", lambda: FakeSettings())
    monkeypatch.setattr(test_writer, "ChatOpenAI", lambda **kwargs: FakeModel())

    def fake_pytest(_repo_dir: Path, test_target: str | None = None) -> tuple[str, str]:
        generated = (repo_dir / "tests" / "test_generated_issue_1.py").read_text(encoding="utf-8")
        assert "```" not in generated
        assert test_target == "tests/test_generated_issue_1.py"
        return "pass", "ok"

    monkeypatch.setattr(test_writer, "run_pytest", fake_pytest)

    out = test_writer.run(
        {
            "issue": {"number": 1, "title": "t", "body": "b"},
            "repo_dir": str(repo_dir),
            "errors": [],
            "retries": 0,
        }
    )
    assert out["test_result"] == "pass"


def test_invalid_generated_tests_fallback_to_safe_template(
    tmp_path: Path, monkeypatch: MonkeyPatch
) -> None:
    repo_dir = tmp_path / "repo"
    repo_dir.mkdir(parents=True, exist_ok=True)

    class FakeSettings:
        default_model = "gpt-4o-mini"
        openai_api_key = "sk-test"
        has_openai_key = True

    class FakeResp:
        content = "def test_bad(:\n    pass"

    class FakeModel:
        def invoke(self, _prompt: str) -> FakeResp:
            return FakeResp()

    monkeypatch.setattr(test_writer, "get_settings", lambda: FakeSettings())
    monkeypatch.setattr(test_writer, "ChatOpenAI", lambda **kwargs: FakeModel())
    monkeypatch.setattr(test_writer, "run_pytest", lambda _repo_dir, test_target=None: ("pass", "ok"))

    out = test_writer.run(
        {
            "issue": {"number": 1, "title": "t", "body": "b"},
            "repo_dir": str(repo_dir),
            "errors": [],
            "retries": 0,
        }
    )
    assert "test_parse_error" in "\n".join(out.get("errors", []))
    assert "def test_placeholder" in out["tests"]


def test_known_symbol_rewrite_maps_validate_email_to_is_valid_email() -> None:
    src = "from app.validators import validate_email\n\nassert validate_email('a') is True\n"
    out = test_writer._rewrite_known_symbols(src)
    assert "validate_email" not in out
    assert "is_valid_email" in out


def test_email_alias_fallback_tests_target_api_endpoint() -> None:
    src = test_writer._email_alias_fallback_tests()
    assert 'client.post("/users/validate"' in src
    assert "UserCreate" in src
    assert "is_valid_email" not in src
