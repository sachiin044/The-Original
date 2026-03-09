"""Agent router — completely isolated from all existing routers.

Provides a single endpoint:
    POST /agent/chat

The endpoint accepts a natural language query about a registered repository
and delegates execution to GitHubAgentController (app/services/agent.py),
which uses GPT-4o-mini's native tool-calling API to autonomously decide
which GitHub tools to invoke, with timeout enforcement and failure recovery.

Authentication: same verify_api_key dependency used by all other endpoints.
No changes to the auth system are required.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.auth.dependency import verify_api_key
from app.services.agent import GitHubAgentController

router = APIRouter(prefix="/agent", tags=["Agent"])


# ── Request / Response schemas ─────────────────────────────────────────────

class InvestigateRequest(BaseModel):
    repo_id: str = Field(
        ...,
        description="The repo_id of a registered GitHub repository.",
        example="b44bd5ed97fb1c25",
    )
    query: str = Field(
        ...,
        description="Natural language question about the repository.",
        example="Why did the last CI build fail and are there any related open issues?",
    )


class StepRecord(BaseModel):
    iteration: int
    tool: str
    args: dict
    result: dict | None = None
    error: str | None = None
    duration_ms: int


class InvestigateResponse(BaseModel):
    answer: str
    steps: list[StepRecord]
    sources: list[str]
    tool_call_count: int
    iterations_used: int
    investigated_at: str


# ── Endpoint ───────────────────────────────────────────────────────────────

@router.post(
    "/chat",
    response_model=InvestigateResponse,
    summary="Autonomous GitHub Repository Investigation",
    description=(
        "Accepts a natural language query about a registered GitHub repository. "
        "An LLM-driven agent autonomously decides which tools to call "
        "(CI workflows, pull requests, issues, deployments), executes them "
        "sequentially with per-tool timeout enforcement and failure recovery, "
        "logs every step to the terminal, and returns one synthesised answer."
    ),
)
def investigate(
    data: InvestigateRequest,
    api_key_id: str = Depends(verify_api_key),
) -> InvestigateResponse:
    controller = GitHubAgentController()
    result = controller.investigate(
        api_key_id=api_key_id,
        repo_id=data.repo_id,
        query=data.query,
    )
    return InvestigateResponse(**result)
