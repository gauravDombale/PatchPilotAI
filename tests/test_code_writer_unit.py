from __future__ import annotations

from pathlib import Path

from resolver.agents import code_writer
from resolver.state import AgentState
from resolver.tools.patching import check_unified_diff


def test_email_alias_fallback_patch_is_valid_and_targets_validators(tmp_path: Path) -> None:
    repo_dir = tmp_path / "repo"
    app_dir = repo_dir / "app"
    app_dir.mkdir(parents=True, exist_ok=True)
    (app_dir / "validators.py").write_text(
        'import re\n\nEMAIL_RE = re.compile(r"^[A-Za-z0-9._-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}$")\n',
        encoding="utf-8",
    )

    diff = code_writer._build_email_alias_fallback_patch(repo_dir)
    assert "app/validators.py" in diff
    assert "[A-Za-z0-9._+-]+" in diff

    ok, log = check_unified_diff(repo_dir, diff)
    assert ok, log


def test_email_alias_issue_detection_uses_issue_text() -> None:
    state: AgentState = {
        "issue": {
            "title": "Email validator rejects plus aliases",
            "body": "john+tag@example.com should be accepted",
        },
        "code_context": [],
        "test_log": "",
    }
    assert code_writer._issue_kind(state) == "email_plus_alias"
