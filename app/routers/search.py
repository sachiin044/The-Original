from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from app.services.repo_discovery import handle_search_turn

router = APIRouter()

# Lightweight in-memory conversation store for search sessions.
SEARCH_CONVERSATIONS: dict[str, list[str]] = {}


class SearchRequest(BaseModel):
    message: str
    conversation_id: str | None = None


@router.post("/search")
def search_repositories(payload: SearchRequest):
    conversation_id = payload.conversation_id or "default"
    history = SEARCH_CONVERSATIONS.get(conversation_id, [])

    result = handle_search_turn(payload.message, history)

    history.append(payload.message)
    SEARCH_CONVERSATIONS[conversation_id] = history

    return {
        "conversation_id": conversation_id,
        **result,
    }
