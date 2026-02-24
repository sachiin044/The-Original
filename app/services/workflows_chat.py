from __future__ import annotations

from datetime import datetime
from typing import Any
from urllib.parse import urlparse

from fastapi import HTTPException
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

from app.core.db import get_supabase
from app.utils.crypto import decrypt_token
from app.utils.github_actions_client import GitHubActionsClient

supabase = get_supabase()

SYSTEM_PROMPT = (
    "You are a senior CI/CD investigator for GitHub Actions. "
    "Use only the provided JSON context. Be concise, accurate, and actionable. "
    "If evidence is limited, clearly say what is unknown."
)


class WorkflowChatService:
    """Business logic for GitHub Actions chat analysis."""

    def __init__(self):
        self.llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.1)

    def answer_question(
        self,
        *,
        api_key_id: str,
        repo_id: str,
        question: str,
        workflow_id: str | None,
        run_id: str | None,
        include_logs: bool,
    ) -> dict[str, Any]:
        owner, repo, token = self._resolve_repo_and_token(
            api_key_id=api_key_id,
            repo_id=repo_id,
        )

        gh = GitHubActionsClient(token=token)
        context = self._build_context(
            gh=gh,
            owner=owner,
            repo=repo,
            workflow_id=workflow_id,
            run_id=run_id,
            include_logs=include_logs,
        )

        answer = self._ask_llm(question=question, context=context)
        return {
            "answer": answer,
            "sources": context["sources"],
            "metadata": {
                "run_count": context["metadata"]["run_count"],
                "workflow_name": context["metadata"].get("workflow_name"),
            },
        }

    def _resolve_repo_and_token(self, *, api_key_id: str, repo_id: str) -> tuple[str, str, str]:
        key_resp = (
            supabase.table("api_keys")
            .select("user_email")
            .eq("id", api_key_id)
            .execute()
        )
        if not key_resp.data:
            raise HTTPException(status_code=401, detail="Invalid API key context")

        user_email = key_resp.data[0]["user_email"]

        repo_resp = (
            supabase.table("repos")
            .select("repo_url, credential_id")
            .eq("repo_id", repo_id)
            .execute()
        )
        if not repo_resp.data:
            raise HTTPException(status_code=404, detail="Repository not registered")

        repo_row = repo_resp.data[0]
        credential_id = repo_row.get("credential_id")
        if not credential_id:
            raise HTTPException(
                status_code=400,
                detail="No GitHub credential attached to repository. Attach credential_id first.",
            )

        cred_resp = (
            supabase.table("credentials")
            .select("provider, status, user_email, encrypted_token")
            .eq("id", credential_id)
            .execute()
        )
        if not cred_resp.data:
            raise HTTPException(status_code=404, detail="Attached credential not found")

        cred = cred_resp.data[0]
        if cred.get("user_email") != user_email:
            raise HTTPException(status_code=403, detail="Credential does not belong to this API key owner")

        if cred.get("provider") != "github":
            raise HTTPException(status_code=400, detail="Attached credential is not a GitHub credential")

        if cred.get("status") == "revoked":
            raise HTTPException(status_code=400, detail="Attached GitHub credential is revoked")

        token = decrypt_token(cred["encrypted_token"])
        owner, repo = self._parse_owner_repo(repo_row["repo_url"])

        return owner, repo, token

    def _parse_owner_repo(self, repo_url: str) -> tuple[str, str]:
        parsed = urlparse(repo_url)
        path = parsed.path.strip("/")
        if path.endswith(".git"):
            path = path[:-4]

        parts = path.split("/")
        if len(parts) < 2:
            raise HTTPException(status_code=400, detail="Unable to parse owner/repo from repo_url")

        return parts[0], parts[1]

    def _build_context(
        self,
        *,
        gh: GitHubActionsClient,
        owner: str,
        repo: str,
        workflow_id: str | None,
        run_id: str | None,
        include_logs: bool,
    ) -> dict[str, Any]:
        workflows_payload = gh.list_workflows(owner, repo)
        workflows = workflows_payload.get("workflows", [])

        sources = ["/actions/workflows"]
        workflow_name = None
        runs: list[dict[str, Any]] = []
        jobs_by_run: dict[str, list[dict[str, Any]]] = {}

        if run_id:
            run = gh.get_run(owner, repo, run_id)
            runs = [run]
            sources.append(f"/actions/runs/{run_id}")

            jobs_payload = gh.list_run_jobs(owner, repo, run_id)
            jobs_by_run[str(run_id)] = jobs_payload.get("jobs", [])
            sources.append(f"/actions/runs/{run_id}/jobs")

            if include_logs:
                run["logs_excerpt"] = gh.get_run_logs(owner, repo, run_id)[:5000]
                sources.append(f"/actions/runs/{run_id}/logs")

            workflow_name = run.get("name")

        elif workflow_id:
            runs_payload = gh.list_workflow_runs(owner, repo, workflow_id=workflow_id, per_page=25)
            runs = runs_payload.get("workflow_runs", [])
            sources.append(f"/actions/workflows/{workflow_id}/runs")

            for run in runs[:10]:
                rid = str(run["id"])
                jobs_payload = gh.list_run_jobs(owner, repo, rid)
                jobs_by_run[rid] = jobs_payload.get("jobs", [])

            wf = next((w for w in workflows if str(w.get("id")) == str(workflow_id)), None)
            workflow_name = wf.get("name") if wf else None

        else:
            for wf in workflows[:5]:
                wf_id = str(wf["id"])
                runs_payload = gh.list_workflow_runs(owner, repo, workflow_id=wf_id, per_page=5)
                wf_runs = runs_payload.get("workflow_runs", [])
                runs.extend(wf_runs)
                sources.append(f"/actions/workflows/{wf_id}/runs")

        workflow_summary = {
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
        }

        runs_summary = [self._summarize_run(r) for r in runs]
        job_summary = self._summarize_jobs(jobs_by_run)
        failure_patterns = self._extract_failure_patterns(runs_summary, jobs_by_run)

        return {
            "workflow_summary": workflow_summary,
            "runs_summary": runs_summary,
            "job_summary": job_summary,
            "failure_patterns": failure_patterns,
            "sources": sources,
            "metadata": {
                "run_count": len(runs_summary),
                "workflow_name": workflow_name,
            },
        }

    def _summarize_run(self, run: dict[str, Any]) -> dict[str, Any]:
        started_at = run.get("run_started_at")
        updated_at = run.get("updated_at")
        duration_seconds = self._duration_seconds(started_at, updated_at)

        return {
            "id": str(run.get("id")),
            "name": run.get("name"),
            "status": run.get("status"),
            "conclusion": run.get("conclusion"),
            "event": run.get("event"),
            "branch": run.get("head_branch"),
            "created_at": run.get("created_at"),
            "run_started_at": started_at,
            "duration_seconds": duration_seconds,
            "run_attempt": run.get("run_attempt"),
            "html_url": run.get("html_url"),
        }

    def _summarize_jobs(self, jobs_by_run: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
        by_name: dict[str, dict[str, Any]] = {}

        for run_jobs in jobs_by_run.values():
            for job in run_jobs:
                name = job.get("name") or "unknown"
                duration = self._duration_seconds(job.get("started_at"), job.get("completed_at"))
                bucket = by_name.setdefault(name, {"durations": [], "conclusions": []})
                if duration is not None:
                    bucket["durations"].append(duration)
                if job.get("conclusion"):
                    bucket["conclusions"].append(job.get("conclusion"))

        summarized = []
        for name, metrics in by_name.items():
            durations = metrics["durations"]
            avg_duration = sum(durations) / len(durations) if durations else None
            summarized.append(
                {
                    "job_name": name,
                    "observations": len(metrics["conclusions"]),
                    "avg_duration_seconds": avg_duration,
                    "conclusions": metrics["conclusions"],
                }
            )

        summarized.sort(key=lambda item: item.get("avg_duration_seconds") or 0, reverse=True)
        return {
            "jobs": summarized,
            "slowest_job": summarized[0] if summarized else None,
        }

    def _extract_failure_patterns(
        self,
        runs_summary: list[dict[str, Any]],
        jobs_by_run: dict[str, list[dict[str, Any]]],
    ) -> dict[str, Any]:
        failed_runs = [r for r in runs_summary if r.get("conclusion") == "failure"]

        job_outcomes: dict[str, set[str]] = {}
        for run_jobs in jobs_by_run.values():
            for job in run_jobs:
                name = job.get("name") or "unknown"
                outcome = job.get("conclusion") or "unknown"
                job_outcomes.setdefault(name, set()).add(outcome)

        flaky_jobs = [name for name, outcomes in job_outcomes.items() if len(outcomes) > 1]

        return {
            "failed_run_count": len(failed_runs),
            "failed_run_ids": [r["id"] for r in failed_runs],
            "flaky_jobs": flaky_jobs,
        }

    def _ask_llm(self, *, question: str, context: dict[str, Any]) -> str:
        response = self.llm.invoke(
            [
                SystemMessage(content=SYSTEM_PROMPT),
                HumanMessage(
                    content=(
                        "Question:\n"
                        f"{question}\n\n"
                        "Structured workflow context (JSON):\n"
                        f"{context}"
                    )
                ),
            ]
        )
        return response.content

    def _duration_seconds(self, started_at: str | None, ended_at: str | None) -> int | None:
        if not started_at or not ended_at:
            return None

        try:
            start = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
            end = datetime.fromisoformat(ended_at.replace("Z", "+00:00"))
            return max(int((end - start).total_seconds()), 0)
        except Exception:
            return None
