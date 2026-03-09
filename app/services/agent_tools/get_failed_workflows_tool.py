"""GetFailedWorkflowsTool — enriched output

Returns structured CI/CD data with all evidence fields required for LLM reasoning.
Calls GitHubActionsClient without modifying it.
"""

from __future__ import annotations

from typing import Any

from app.services.agent_tools.base import AgentTool
from app.utils.github_actions_client import GitHubActionsClient


class GetFailedWorkflowsTool(AgentTool):
    name = "GetFailedWorkflowsTool"
    description = (
        "Fetches GitHub Actions workflows and recent runs for the repository. "
        "Returns structured run records including status, conclusion, failure "
        "details, actor, event type, and SHA. Also detects flaky jobs. "
        "Use this when the query is about CI failures, broken builds, "
        "workflow status, pipeline errors, or who triggered a run."
    )

    def __init__(self, owner: str, repo: str, token: str) -> None:
        self._owner = owner
        self._repo = repo
        self._token = token

    def run(self, per_page: int = 10, **_: Any) -> dict[str, Any]:
        """Fetch workflow runs and return an enriched failure summary.

        Args:
            per_page: Number of recent runs to inspect per workflow (default 10).
        """
        self._log(f"{self._owner}/{self._repo} (per_page={per_page})")

        try:
            gh = GitHubActionsClient(token=self._token)

            # 1. List workflows
            workflows_payload = gh.list_workflows(self._owner, self._repo)
            workflows = workflows_payload.get("workflows", [])

            # Build a quick lookup: workflow_id → workflow_name
            workflow_name_map: dict[str, str] = {
                str(w["id"]): w.get("name", "unknown")
                for w in workflows
            }

            all_runs: list[dict[str, Any]] = []
            jobs_by_run: dict[str, list[dict[str, Any]]] = {}

            # 2. Fetch runs for first 5 workflows
            for wf in workflows[:5]:
                wf_id = str(wf["id"])
                try:
                    runs_payload = gh.list_workflow_runs(
                        self._owner, self._repo,
                        workflow_id=wf_id,
                        per_page=per_page,
                    )
                    runs = runs_payload.get("workflow_runs", [])
                    all_runs.extend(runs)

                    # 3. Fetch jobs for up to 5 runs per workflow
                    for run in runs[:5]:
                        rid = str(run["id"])
                        try:
                            jobs_payload = gh.list_run_jobs(
                                self._owner, self._repo, rid
                            )
                            jobs_by_run[rid] = jobs_payload.get("jobs", [])
                        except Exception:
                            jobs_by_run[rid] = []
                except Exception:
                    pass

            # 4. Build enriched run records
            run_records: list[dict[str, Any]] = []
            for r in all_runs:
                run_id = str(r.get("id"))
                jobs = jobs_by_run.get(run_id, [])

                # Derive failure_reason from failed job steps
                failure_reason: str | None = None
                if r.get("conclusion") == "failure":
                    failed_jobs = [
                        j for j in jobs if j.get("conclusion") == "failure"
                    ]
                    if failed_jobs:
                        job_name = failed_jobs[0].get("name", "unknown job")
                        # Try to find first failed step
                        steps = failed_jobs[0].get("steps") or []
                        failed_step = next(
                            (
                                s.get("name")
                                for s in steps
                                if s.get("conclusion") == "failure"
                            ),
                            None,
                        )
                        failure_reason = (
                            f"Job '{job_name}' failed"
                            + (f" at step '{failed_step}'" if failed_step else "")
                        )

                run_records.append(
                    {
                        "workflow_id": str(r.get("workflow_id")) if r.get("workflow_id") else None,
                        "workflow_name": workflow_name_map.get(
                            str(r.get("workflow_id")), r.get("name")
                        ),
                        "run_id": run_id,
                        "status": r.get("status"),
                        "conclusion": r.get("conclusion"),
                        "failure_reason": failure_reason,
                        "head_sha": (r.get("head_sha") or "")[:7] or None,
                        "actor_login": (r.get("actor") or {}).get("login"),
                        "event": r.get("event"),
                        "created_at": r.get("created_at"),
                        "updated_at": r.get("updated_at"),
                        "html_url": r.get("html_url"),
                    }
                )

            # 5. Detect flaky jobs
            job_outcomes: dict[str, set[str]] = {}
            for run_jobs in jobs_by_run.values():
                for job in run_jobs:
                    name = job.get("name") or "unknown"
                    conclusion = job.get("conclusion") or "unknown"
                    job_outcomes.setdefault(name, set()).add(conclusion)

            flaky_jobs = [
                name for name, outcomes in job_outcomes.items()
                if len(outcomes) > 1
            ]

            failed_records = [r for r in run_records if r["conclusion"] == "failure"]

            result = {
                "workflow_count": len(workflows),
                "workflows": [
                    {
                        "id": str(w.get("id")),
                        "name": w.get("name"),
                        "state": w.get("state"),
                        "path": w.get("path"),
                    }
                    for w in workflows
                ],
                "total_runs_inspected": len(run_records),
                "failed_run_count": len(failed_records),
                "failed_runs": failed_records[:10],
                "all_runs": run_records[:20],  # cap payload for LLM context
                "flaky_jobs": flaky_jobs,
            }

            print(
                f"[AGENT TOOL] {self.name} → "
                f"{len(failed_records)} failed / {len(run_records)} total runs, "
                f"{len(flaky_jobs)} flaky jobs"
            )
            return result

        except Exception as exc:  # noqa: BLE001
            error_msg = f"GetFailedWorkflowsTool error: {exc}"
            print(f"[AGENT TOOL] {self.name} → ERROR: {exc}")
            return {"error": error_msg}
