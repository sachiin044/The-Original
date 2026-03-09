"""app/services/agent.py — GitHub Investigation Agent Controller

This is the main agent controller implementing:
  - Tool registry (all 4 GitHub investigation tools as callable+schema objects)
  - LLM-driven tool-selection loop using GPT-4o-mini native tool-calling API
  - Structured execution logging with canonical log messages
  - Max iteration guard (default 8)
  - Per-tool timeout enforcement via concurrent.futures
  - Tool failure recovery (errors are captured and fed back to the LLM)
  - Credential resolution (isolated — no import from any existing service class)

The LLM decides which tools to call based solely on the user's query and the
tool result history.  No keyword detection, no static routing.

Used exclusively by app/routers/agent.py — no other file imports this.
"""

from __future__ import annotations

import concurrent.futures
import json
import logging
import time
from datetime import datetime
from typing import Any
from urllib.parse import urlparse

from fastapi import HTTPException
from langchain_core.messages import (
    AIMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)
from langchain_core.tools import StructuredTool
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from app.core.db import get_supabase
from app.utils.crypto import decrypt_token

# Concrete tool implementations — imported but never modified
from app.services.agent_tools.get_failed_workflows_tool import GetFailedWorkflowsTool
from app.services.agent_tools.get_deployment_info_tool import GetDeploymentInfoTool
from app.services.agent_tools.get_last_pr_tool import GetLastPRTool
from app.services.agent_tools.get_issue_details_tool import GetIssueDetailsTool

logger = logging.getLogger("explaingithub.agent")

# ── Constants ──────────────────────────────────────────────────────────────
MAX_ITERATIONS: int = 8          # hard recursion cap
TOOL_TIMEOUT_SECONDS: float = 25.0  # per-tool wall-clock limit

_SYSTEM_PROMPT = (
    "You are an autonomous GitHub repository investigation agent. "
    "You have access to specialised tools that fetch live data from GitHub. "
    "For each user question, call ONLY the tools that are necessary to "
    "gather evidence. Do NOT guess or fabricate data — every claim must be "
    "grounded in tool output. "
    "Once you have enough information, produce a concise, actionable final "
    "answer. Stop calling tools as soon as you are ready to answer."
)


# ── Pydantic input schemas for each tool ──────────────────────────────────

class _WorkflowInput(BaseModel):
    per_page: int = Field(
        default=10,
        description="Number of recent workflow runs to inspect per workflow (1-25).",
    )


class _DeploymentInput(BaseModel):
    limit: int = Field(
        default=5,
        description="Maximum number of recent deployments to return (1-20).",
    )


class _PRInput(BaseModel):
    limit: int = Field(
        default=10,
        description="Number of most-recent pull requests to fetch (1-50).",
    )


class _IssueInput(BaseModel):
    limit: int = Field(
        default=20,
        description="Number of most-recent issues to fetch (1-100).",
    )


# ── Execution step record ─────────────────────────────────────────────────

class ExecutionStep(BaseModel):
    iteration: int
    tool: str
    args: dict
    result: dict | None = None
    error: str | None = None
    duration_ms: int


# ── Main controller ───────────────────────────────────────────────────────

class GitHubAgentController:
    """LLM-driven autonomous GitHub investigation controller.

    Call ``investigate()`` with a repo_id and natural-language query.
    The controller resolves credentials, instantiates tools, then runs
    the tool-calling loop until the LLM produces a final text answer.
    """

    def __init__(self) -> None:
        self._supabase = get_supabase()
        self._llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

    # =========================================================================
    # Public API
    # =========================================================================

    def investigate(
        self,
        *,
        api_key_id: str,
        repo_id: str,
        query: str,
    ) -> dict[str, Any]:
        """Run the autonomous investigation loop.

        Returns
        -------
        dict with keys:
            answer          – final synthesised text
            steps           – list of ExecutionStep dicts
            sources         – deduplicated list of tools that were called
            tool_call_count – integer
            iterations_used – integer
            investigated_at – ISO-8601 UTC timestamp
        """
        self._log_info("Analyzing query…")
        self._log_info(f"Query: {query!r}")

        # 1. Resolve repo credentials
        owner, repo, token = self._resolve_credentials(
            api_key_id=api_key_id, repo_id=repo_id
        )
        self._log_info(f"Repository resolved: {owner}/{repo}")

        # 2. Build tool registry
        tool_instances, lc_tools = self._build_tool_registry(owner, repo, token)
        llm_with_tools = self._llm.bind_tools(lc_tools)

        # 3. Initialise message history
        messages: list = [
            SystemMessage(content=_SYSTEM_PROMPT),
            HumanMessage(content=query),
        ]

        steps: list[dict[str, Any]] = []
        sources: list[str] = []
        iteration = 0

        # ── Tool-calling loop ─────────────────────────────────────────────
        while iteration < MAX_ITERATIONS:
            iteration += 1
            self._log_info(f"[Iteration {iteration}/{MAX_ITERATIONS}] Querying LLM…")

            response: AIMessage = llm_with_tools.invoke(messages)
            messages.append(response)

            tool_calls = getattr(response, "tool_calls", None) or []

            if not tool_calls:
                # LLM has stopped calling tools → final answer is ready
                self._log_info("Generating final answer…")
                break

            # Execute every tool the LLM requested in this iteration
            for tc in tool_calls:
                tool_name: str = tc["name"]
                tool_args: dict = tc.get("args", {})
                tool_call_id: str = tc["id"]

                self._log_info(f"Tool selected: {tool_name}")
                self._log_info(f"Executing tool… (args={tool_args})")

                step, tool_message = self._execute_tool(
                    iteration=iteration,
                    tool_name=tool_name,
                    tool_args=tool_args,
                    tool_call_id=tool_call_id,
                    tool_instances=tool_instances,
                )

                self._log_info(f"Tool completed: {tool_name} ({step['duration_ms']}ms)")

                steps.append(step)
                sources.append(tool_name)
                messages.append(tool_message)
        else:
            # Iteration cap reached — force a final-answer pass without tools
            self._log_info(
                f"Max iterations ({MAX_ITERATIONS}) reached — generating final answer…"
            )
            plain_llm = self._llm  # no tools bound
            response = plain_llm.invoke(messages)
            messages.append(response)

        # ── Extract final answer ──────────────────────────────────────────
        final_answer = self._extract_final_answer(messages)

        self._log_info(
            f"Investigation complete — {len(steps)} tool call(s) across "
            f"{iteration} iteration(s)."
        )

        return {
            "answer": final_answer,
            "steps": steps,
            "sources": list(dict.fromkeys(sources)),   # ordered dedup
            "tool_call_count": len(steps),
            "iterations_used": iteration,
            "investigated_at": datetime.utcnow().isoformat() + "Z",
        }

    # =========================================================================
    # Tool execution with timeout + failure recovery
    # =========================================================================

    def _execute_tool(
        self,
        *,
        iteration: int,
        tool_name: str,
        tool_args: dict,
        tool_call_id: str,
        tool_instances: dict[str, Any],
    ) -> tuple[dict[str, Any], ToolMessage]:
        """Execute one tool call, enforcing timeout and recovering from errors.

        Always returns a (step_dict, ToolMessage) pair — never raises.
        """
        t_start = time.monotonic()
        instance = tool_instances.get(tool_name)

        result: dict[str, Any]
        error: str | None = None

        if instance is None:
            error = f"Unknown tool '{tool_name}' — not in registry."
            result = {"error": error}
        else:
            try:
                result = self._run_with_timeout(instance, tool_args)
            except concurrent.futures.TimeoutError:
                error = (
                    f"Tool '{tool_name}' timed out after "
                    f"{TOOL_TIMEOUT_SECONDS:.0f}s."
                )
                result = {"error": error}
                self._log_warn(f"TIMEOUT: {error}")
            except Exception as exc:  # noqa: BLE001
                error = f"Tool '{tool_name}' raised an unexpected error: {exc}"
                result = {"error": error}
                self._log_warn(f"FAILURE: {error}")

        duration_ms = int((time.monotonic() - t_start) * 1000)

        step: dict[str, Any] = {
            "iteration": iteration,
            "tool": tool_name,
            "args": tool_args,
            "result": result if not error else None,
            "error": error,
            "duration_ms": duration_ms,
        }

        tool_message = ToolMessage(
            content=json.dumps(result, default=str),
            tool_call_id=tool_call_id,
        )

        return step, tool_message

    def _run_with_timeout(
        self,
        instance: Any,
        tool_args: dict,
    ) -> dict[str, Any]:
        """Run instance.run(**tool_args) with a hard wall-clock timeout."""
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(instance.run, **tool_args)
            return future.result(timeout=TOOL_TIMEOUT_SECONDS)

    # =========================================================================
    # Tool registry
    # =========================================================================

    def _build_tool_registry(
        self, owner: str, repo: str, token: str
    ) -> tuple[dict[str, Any], list[StructuredTool]]:
        """Instantiate all tools and return (instance_map, langchain_tools)."""

        tool_configs: list[tuple[str, Any, type[BaseModel]]] = [
            (
                "GetFailedWorkflowsTool",
                GetFailedWorkflowsTool(owner, repo, token),
                _WorkflowInput,
            ),
            (
                "GetDeploymentInfoTool",
                GetDeploymentInfoTool(owner, repo, token),
                _DeploymentInput,
            ),
            (
                "GetLastPRTool",
                GetLastPRTool(owner, repo, token),
                _PRInput,
            ),
            (
                "GetIssueDetailsTool",
                GetIssueDetailsTool(owner, repo, token),
                _IssueInput,
            ),
        ]

        instance_map: dict[str, Any] = {}
        lc_tools: list[StructuredTool] = []

        for name, instance, schema in tool_configs:
            instance_map[name] = instance

            # Closure trick to avoid late-binding issue in lambda
            def _make_fn(inst: Any) -> Any:
                def _fn(**kwargs: Any) -> str:
                    r = inst.run(**kwargs)
                    return json.dumps(r, default=str)
                return _fn

            lc_tools.append(
                StructuredTool.from_function(
                    func=_make_fn(instance),
                    name=name,
                    description=instance.description,
                    args_schema=schema,
                )
            )

        return instance_map, lc_tools

    # =========================================================================
    # Credential resolution (fully isolated — no import from other services)
    # =========================================================================

    def _resolve_credentials(
        self, *, api_key_id: str, repo_id: str
    ) -> tuple[str, str, str]:
        """Returns (owner, repo, decrypted_token) or raises HTTPException."""

        key_resp = (
            self._supabase.table("api_keys")
            .select("user_email")
            .eq("id", api_key_id)
            .execute()
        )
        if not key_resp.data:
            raise HTTPException(status_code=401, detail="Invalid API key context")

        user_email = key_resp.data[0]["user_email"]

        repo_resp = (
            self._supabase.table("repos")
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
                detail="No GitHub credential attached to this repository.",
            )

        cred_resp = (
            self._supabase.table("credentials")
            .select("provider, status, user_email, encrypted_token")
            .eq("id", credential_id)
            .execute()
        )
        if not cred_resp.data:
            raise HTTPException(status_code=404, detail="Attached credential not found")

        cred = cred_resp.data[0]

        if cred.get("user_email") != user_email:
            raise HTTPException(
                status_code=403,
                detail="Credential does not belong to this API key owner",
            )
        if cred.get("provider") != "github":
            raise HTTPException(
                status_code=400,
                detail="Attached credential is not a GitHub credential",
            )
        if cred.get("status") == "revoked":
            raise HTTPException(
                status_code=400,
                detail="Attached GitHub credential is revoked",
            )

        token = decrypt_token(cred["encrypted_token"])
        owner, repo = self._parse_owner_repo(repo_row["repo_url"])
        return owner, repo, token

    def _parse_owner_repo(self, repo_url: str) -> tuple[str, str]:
        path = urlparse(repo_url).path.strip("/").removesuffix(".git")
        parts = path.split("/")
        if len(parts) < 2:
            raise HTTPException(
                status_code=400,
                detail="Unable to parse owner/repo from repo_url",
            )
        return parts[0], parts[1]

    # =========================================================================
    # Helpers
    # =========================================================================

    @staticmethod
    def _extract_final_answer(messages: list) -> str:
        """Walk messages in reverse; return the first plain AI text response."""
        for msg in reversed(messages):
            if isinstance(msg, AIMessage) and not getattr(msg, "tool_calls", None):
                content = msg.content
                if isinstance(content, list):
                    # Handle structured content blocks (OpenAI format)
                    texts = [
                        block.get("text", "")
                        for block in content
                        if isinstance(block, dict) and block.get("type") == "text"
                    ]
                    return " ".join(texts).strip()
                if isinstance(content, str) and content.strip():
                    return content.strip()
        return "Investigation complete, but no textual answer was produced."

    @staticmethod
    def _log_info(message: str) -> None:
        line = f"[AGENT] {message}"
        print(line)
        logger.info(line)

    @staticmethod
    def _log_warn(message: str) -> None:
        line = f"[AGENT][WARN] {message}"
        print(line)
        logger.warning(line)
