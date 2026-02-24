from pydantic import BaseModel
from typing import Optional, List, Dict

class RepoRequest(BaseModel):
    repo_url: str


class ChatRequest(BaseModel):
    message: str
    repo_id: str
    chat_id: str | None = None
    context: dict | None = None
    files: list[str] | None = None


class GenerateKeyRequest(BaseModel):
    email: str
    name: str | None = "API Key"

class RevokeKeyRequest(BaseModel):
    api_key_id: str

class PrivateRepoRequest(BaseModel):
    repo_url: str
    github_token: str

class CreateApiKeyRequest(BaseModel):
    email: str
    name: str
    environment: str | None = None
    scopes: list[str] | None = None
    expires_at: str | None = None
    ip_allowlist: list[str] | None = None


class UpdateApiKeyRequest(BaseModel):
    name: str | None = None
    scopes: list[str] | None = None
    environment: str | None = None

class GithubPATRequest(BaseModel):
    token: str
    label: str
    scopes_expected: list[str]
    expires_at: str

class RegisterRepoRequest(BaseModel):
    provider: str
    repo_url: str
    branch: str | None = "main"
    visibility: str | None = "private"
    credential_id: str | None = None

class IssueChatRequest(BaseModel):
    repo_id: str
    issue_number: int | None = None
    message: str
    chat_id: str | None = None
    context: dict | None = {
        "include_comments": True,
        "depth": "medium"
    }


class PullRequestChatRequest(BaseModel):
    repo_id: str
    pr_number: int | None = None
    message: str
    chat_id: str | None = None
    context: dict | None = None


class WorkflowChatRequest(BaseModel):
    repo_id: str
    workflow_id: str | None = None
    run_id: str | None = None
    question: str
    chat_id: str | None = None
    include_logs: bool = False


class WorkflowChatResponse(BaseModel):
    answer: str
    sources: list[str]
    metadata: dict
