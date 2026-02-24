from __future__ import annotations

from typing import Any
import requests


class GitHubActionsClient:
    """Small reusable GitHub Actions REST client using an injected PAT."""

    def __init__(self, token: str, timeout_s: int = 20):
        self.base_url = "https://api.github.com"
        self.timeout_s = timeout_s
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            }
        )

    def _get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        response = self.session.get(
            f"{self.base_url}{path}",
            params=params,
            timeout=self.timeout_s,
        )

        if response.status_code >= 400:
            detail = response.text
            raise RuntimeError(f"GitHub API error {response.status_code}: {detail}")

        return response.json()

    def _get_text(self, path: str, params: dict[str, Any] | None = None) -> str:
        response = self.session.get(
            f"{self.base_url}{path}",
            params=params,
            timeout=self.timeout_s,
        )

        if response.status_code >= 400:
            detail = response.text
            raise RuntimeError(f"GitHub API error {response.status_code}: {detail}")

        return response.text

    def list_workflows(self, owner: str, repo: str) -> dict[str, Any]:
        return self._get(f"/repos/{owner}/{repo}/actions/workflows")

    def list_workflow_runs(
        self,
        owner: str,
        repo: str,
        workflow_id: str,
        per_page: int = 20,
    ) -> dict[str, Any]:
        return self._get(
            f"/repos/{owner}/{repo}/actions/workflows/{workflow_id}/runs",
            params={"per_page": per_page},
        )

    def get_run(self, owner: str, repo: str, run_id: str) -> dict[str, Any]:
        return self._get(f"/repos/{owner}/{repo}/actions/runs/{run_id}")

    def list_run_jobs(self, owner: str, repo: str, run_id: str) -> dict[str, Any]:
        return self._get(f"/repos/{owner}/{repo}/actions/runs/{run_id}/jobs")

    def get_run_logs(self, owner: str, repo: str, run_id: str) -> str:
        # GitHub may redirect for logs. requests follows redirects by default.
        return self._get_text(f"/repos/{owner}/{repo}/actions/runs/{run_id}/logs")
