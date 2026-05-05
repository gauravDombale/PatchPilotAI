from __future__ import annotations

from _pytest.monkeypatch import MonkeyPatch

from resolver.tools.github_tools import GitHubTools


def test_authenticated_clone_url_uses_token(monkeypatch: MonkeyPatch) -> None:
    class FakeSettings:
        github_token = "ghp_test_token"
        has_github_token = True

    monkeypatch.setattr("resolver.tools.github_tools.get_settings", lambda: FakeSettings())

    tools = GitHubTools()
    url = tools.get_authenticated_clone_url(
        repo_full_name="owner/repo",
        clone_url="https://github.com/owner/repo.git",
    )
    assert url == "https://x-access-token:ghp_test_token@github.com/owner/repo.git"
