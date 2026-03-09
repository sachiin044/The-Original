"""GetIssueDetailsTool — enriched output

Returns recent issues with all metadata fields required for LLM reasoning.
Calls fetch_repository_issues() from the existing issues_chat service — does NOT modify it.
"""

from __future__ import annotations

from typing import Any

from app.services.agent_tools.base import AgentTool
from app.services.issues_chat import fetch_repository_issues

_BODY_MAX_CHARS = 500  # trim issue body to keep LLM context lean


class GetIssueDetailsTool(AgentTool):
    name = "GetIssueDetailsTool"
    description = (
        "Fetches recent GitHub issues for the repository. Returns issue numbers, "
        "titles, trimmed body, state (open/closed), author, labels, comment count, "
        "and timestamps. Use this when the query is about bugs, feature requests, "
        "reported problems, open issues, or any tracked work items."
    )

    def __init__(self, owner: str, repo: str, token: str | None) -> None:
        self._owner = owner
        self._repo = repo
        self._token = token
        self._repo_full_name = f"{owner}/{repo}"

    def run(self, limit: int = 20, **_: Any) -> dict[str, Any]:
        """Fetch recent issues with enriched metadata.

        Args:
            limit: Number of recent issues to return (default 20).
        """
        self._log(f"{self._repo_full_name} (limit={limit})")

        try:
            raw_issues = fetch_repository_issues(
                repo_full_name=self._repo_full_name,
                github_token=self._token,
                limit=limit,
            )

            issues: list[dict[str, Any]] = []
            for issue in raw_issues:
                body_raw = issue.get("body") or ""
                body_trimmed = (
                    body_raw[:_BODY_MAX_CHARS]
                    + ("…" if len(body_raw) > _BODY_MAX_CHARS else "")
                )

                issues.append(
                    {
                        "issue_number": issue.get("number"),
                        "title": issue.get("title"),
                        "body": body_trimmed or None,
                        "state": issue.get("state"),
                        "author_login": (issue.get("user") or {}).get("login"),
                        "labels": [
                            lbl.get("name")
                            for lbl in (issue.get("labels") or [])
                            if lbl.get("name")
                        ],
                        "comments": issue.get("comments", 0),
                        "created_at": issue.get("created_at"),
                        "updated_at": issue.get("updated_at"),
                        "html_url": issue.get("html_url"),
                    }
                )

            open_count = sum(1 for i in issues if i["state"] == "open")
            closed_count = sum(1 for i in issues if i["state"] == "closed")

            result = {
                "total_fetched": len(issues),
                "open_count": open_count,
                "closed_count": closed_count,
                "issues": issues,
            }

            print(
                f"[AGENT TOOL] {self.name} → "
                f"{len(issues)} issues ({open_count} open, {closed_count} closed)"
            )
            return result

        except Exception as exc:  # noqa: BLE001
            error_msg = f"GetIssueDetailsTool error: {exc}"
            print(f"[AGENT TOOL] {self.name} → ERROR: {exc}")
            return {"error": error_msg}
