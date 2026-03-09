"""GetDeploymentInfoTool — enriched output

Returns structured deployment and environment data.
Uses direct GitHub REST API calls (no existing service covers this domain).
No existing file is modified.
"""

from __future__ import annotations

from typing import Any

import requests

from app.services.agent_tools.base import AgentTool

_GITHUB_API_BASE = "https://api.github.com"


class GetDeploymentInfoTool(AgentTool):
    name = "GetDeploymentInfoTool"
    description = (
        "Fetches recent GitHub deployments and environments for the repository. "
        "Returns deployment IDs, environment names, deployment state, creator, "
        "SHA, ref, and timestamps. Use this when the query is about deployments, "
        "production status, staging environments, or release history."
    )

    def __init__(self, owner: str, repo: str, token: str) -> None:
        self._owner = owner
        self._repo = repo
        self._token = token
        self._headers = {
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
        }

    def run(self, limit: int = 5, **_: Any) -> dict[str, Any]:
        """Fetch recent deployments and environments.

        Args:
            limit: Max number of deployments to return (default 5).
        """
        self._log(f"{self._owner}/{self._repo} (limit={limit})")

        try:
            deployments = self._fetch_deployments(limit=limit)
            environments = self._fetch_environments()

            result = {
                "deployment_count": len(deployments),
                "deployments": deployments,
                "environment_count": len(environments),
                "environments": environments,
            }

            print(
                f"[AGENT TOOL] {self.name} → "
                f"{len(deployments)} deployments, {len(environments)} environments"
            )
            return result

        except Exception as exc:  # noqa: BLE001
            error_msg = f"GetDeploymentInfoTool error: {exc}"
            print(f"[AGENT TOOL] {self.name} → ERROR: {exc}")
            return {"error": error_msg}

    # ── Private helpers ────────────────────────────────────────────────────

    def _fetch_deployments(self, limit: int) -> list[dict[str, Any]]:
        url = f"{_GITHUB_API_BASE}/repos/{self._owner}/{self._repo}/deployments"
        resp = requests.get(
            url,
            headers=self._headers,
            params={"per_page": limit},
            timeout=20,
        )

        if resp.status_code == 404:
            return []
        if resp.status_code >= 400:
            raise RuntimeError(f"GitHub API {resp.status_code}: {resp.text[:200]}")

        raw = resp.json()
        deployments: list[dict[str, Any]] = []

        for d in raw[:limit]:
            deployment_id = d.get("id")
            state = self._fetch_latest_status(deployment_id)
            sha_raw = d.get("sha") or ""

            deployments.append(
                {
                    "deployment_id": deployment_id,
                    "environment": d.get("environment"),
                    "state": state,
                    "creator_login": (d.get("creator") or {}).get("login"),
                    "sha": sha_raw[:7] if sha_raw else None,
                    "ref": d.get("ref"),
                    "created_at": d.get("created_at"),
                    "updated_at": d.get("updated_at"),
                    "description": d.get("description") or None,
                    "html_url": (
                        f"https://github.com/{self._owner}/{self._repo}"
                        f"/deployments/{d.get('environment')}"
                    ),
                }
            )

        return deployments

    def _fetch_latest_status(self, deployment_id: int | None) -> str | None:
        if not deployment_id:
            return None
        url = (
            f"{_GITHUB_API_BASE}/repos/{self._owner}/{self._repo}"
            f"/deployments/{deployment_id}/statuses"
        )
        try:
            resp = requests.get(url, headers=self._headers, timeout=10)
            if resp.status_code == 200:
                statuses = resp.json()
                if statuses:
                    return statuses[0].get("state")
        except Exception:
            pass
        return None

    def _fetch_environments(self) -> list[dict[str, Any]]:
        url = f"{_GITHUB_API_BASE}/repos/{self._owner}/{self._repo}/environments"
        try:
            resp = requests.get(url, headers=self._headers, timeout=20)
            if resp.status_code in (404, 403):
                return []
            if resp.status_code >= 400:
                return []
            data = resp.json()
            envs = data.get("environments") or []
            return [
                {
                    "id": e.get("id"),
                    "name": e.get("name"),
                    "url": e.get("html_url"),
                    "created_at": e.get("created_at"),
                    "updated_at": e.get("updated_at"),
                }
                for e in envs
            ]
        except Exception:
            return []
