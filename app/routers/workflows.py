from fastapi import APIRouter, Depends

from app.auth.dependency import RequireWorkflowChatScopes
from app.auth.rate_limit import rate_limit
from app.schemas.models import WorkflowChatRequest, WorkflowChatResponse
from app.services.workflows_chat import WorkflowChatService

router = APIRouter()
service = WorkflowChatService()


@router.post("/workflows/chat", response_model=WorkflowChatResponse)
def workflows_chat(
    data: WorkflowChatRequest,
    api_key_id: str = Depends(RequireWorkflowChatScopes()),
    _: None = Depends(rate_limit("chat")),
):
    """
    Chat with GitHub Actions workflows/runs.

    Scope behavior:
    - repo_id only: high-level workflow analysis
    - workflow_id only: aggregate workflow run analysis
    - run_id: deep run analysis
    """

    return service.answer_question(
        api_key_id=api_key_id,
        repo_id=data.repo_id,
        workflow_id=data.workflow_id,
        run_id=data.run_id,
        question=data.question,
        include_logs=data.include_logs,
    )
