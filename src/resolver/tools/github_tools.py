from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import quote

from github import Github
from github.GithubException import GithubException

from resolver.config import get_settings


@dataclass
class IssueData:
    repo: str
    number: int
    title: str
    body: str
    clone_url: str | None = None
    default_branch: str | None = None


class GitHubTools:
    def __init__(self) -> None:
        settings = get_settings()
        token = settings.github_token if settings.has_github_token else ""
        self.client = Github(token) if token else None

    def get_issue(self, repo_full_name: str, issue_number: int) -> IssueData:
        if not self.client:
            return IssueData(
                repo=repo_full_name,
                number=issue_number,
                title=f"Issue {issue_number}",
                body="No GitHub token provided. Running in local simulation mode.",
            )
        repo = self.client.get_repo(repo_full_name)
        issue = repo.get_issue(number=issue_number)
        return IssueData(
            repo=repo_full_name,
            number=issue_number,
            title=issue.title,
            body=issue.body or "",
            clone_url=repo.clone_url,
            default_branch=repo.default_branch,
        )

    def get_authenticated_clone_url(
        self,
        repo_full_name: str,
        clone_url: str | None = None,
    ) -> str | None:
        settings = get_settings()
        if not settings.has_github_token:
            return None
        if not clone_url:
            clone_url = f"https://github.com/{repo_full_name}.git"
        token = quote(settings.github_token, safe="")
        return clone_url.replace("https://", f"https://x-access-token:{token}@")

    def open_pr(
        self,
        repo_full_name: str,
        branch: str,
        title: str,
        body: str,
        base: str,
    ) -> str:
        if not self.client:
            return f"https://github.com/{repo_full_name}/pull/mock-{branch}"
        try:
            repo = self.client.get_repo(repo_full_name)
            pr = repo.create_pull(title=title, body=body, head=branch, base=base)
            return pr.html_url
        except GithubException:
            return f"https://github.com/{repo_full_name}/pull/mock-{branch}"
