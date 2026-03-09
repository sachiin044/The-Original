"""GetLastPRTool — enriched output

Returns recent pull requests with all metadata fields required for LLM reasoning.
Calls fetch_repository_prs() from the existing pr_chat service — does NOT modify it.
"""

from __future__ import annotations

from typing import Any

from app.services.agent_tools.base import AgentTool
from app.services.pr_chat import fetch_repository_prs

_BODY_MAX_CHARS = 500  # trim PR body to keep LLM context lean


class GetLastPRTool(AgentTool):
    name = "GetLastPRTool"
    description = (
        "Fetches the most recent pull requests (open, closed, and merged) for "
        "the repository. Returns PR number, title, trimmed body, state, merge "
        "status, author, SHA, branch names, and timestamps. "
        "Use this when the query is about recent changes, merged code, "
        "PR review status, or what was shipped recently."
    )

    def __init__(self, owner: str, repo: str, token: str | None) -> None:
        self._owner = owner
        self._repo = repo
        self._token = token
        self._repo_full_name = f"{owner}/{repo}"

    def run(self, limit: int = 10, **_: Any) -> dict[str, Any]:
        """Fetch the most recent PRs with enriched metadata.

        Args:
            limit: Number of recent PRs to return (default 10).
        """
        self._log(f"{self._repo_full_name} (limit={limit})")

        try:
            raw_prs = fetch_repository_prs(
                repo_full_name=self._repo_full_name,
                github_token=self._token,
                limit=limit,
            )

            prs: list[dict[str, Any]] = []
            for pr in raw_prs:
                body_raw = pr.get("body") or ""
                body_trimmed = (
                    body_raw[:_BODY_MAX_CHARS]
                    + ("…" if len(body_raw) > _BODY_MAX_CHARS else "")
                )

                prs.append(
                    {
                        "pr_number": pr.get("number"),
                        "title": pr.get("title"),
                        "body": body_trimmed or None,
                        "state": pr.get("state"),
                        "merged": pr.get("merged_at") is not None,
                        "merged_at": pr.get("merged_at"),
                        "author_login": (pr.get("user") or {}).get("login"),
                        "head_sha": (
                            ((pr.get("head") or {}).get("sha") or "")[:7] or None
                        ),
                        "base_branch": (pr.get("base") or {}).get("ref"),
                        "head_branch": (pr.get("head") or {}).get("ref"),
                        "created_at": pr.get("created_at"),
                        "updated_at": pr.get("updated_at"),
                        "html_url": pr.get("html_url"),
                    }
                )

            open_count = sum(1 for p in prs if p["state"] == "open")
            merged_count = sum(1 for p in prs if p["merged"])

            result = {
                "total_fetched": len(prs),
                "open_count": open_count,
                "merged_count": merged_count,
                "prs": prs,
            }

            print(
                f"[AGENT TOOL] {self.name} → "
                f"{len(prs)} PRs ({open_count} open, {merged_count} merged)"
            )
            return result

        except Exception as exc:  # noqa: BLE001
            error_msg = f"GetLastPRTool error: {exc}"
            print(f"[AGENT TOOL] {self.name} → ERROR: {exc}")
            return {"error": error_msg}
