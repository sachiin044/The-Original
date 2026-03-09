# # chat_store.py
# from datetime import datetime
# from typing import Dict, List

# CHAT_STORE: Dict[str, dict] = {}


# def create_chat(chat_id: str, repo_id: str):
#     if chat_id not in CHAT_STORE:
#         CHAT_STORE[chat_id] = {
#             "repo_id": repo_id,
#             "created_at": datetime.utcnow().isoformat() + "Z",
#             "messages": []
#         }


# # def append_message(
# #     chat_id: str,
# #     role: str,
# #     content: str,
# #     sources: List[str] | None = None,
# #     tokens_used: int | None = None,
# # ):
# #     CHAT_STORE[chat_id]["messages"].append({
# #         "role": role,
# #         "content": content,
# #         "sources": sources,
# #         "tokens_used": tokens_used,
# #         "created_at": datetime.utcnow().isoformat() + "Z"
# #     })


# from datetime import datetime
# from typing import List

# CHAT_STORE = {}

# def append_message(
#     chat_id: str,
#     role: str,
#     content: str,
#     sources: List[str] | None = None,
#     tokens_used: int | None = None,
# ):
#     # ✅ Initialize chat if it doesn't exist
#     if chat_id not in CHAT_STORE:
#         CHAT_STORE[chat_id] = {
#             "messages": []
#         }

#     CHAT_STORE[chat_id]["messages"].append({
#         "role": role,
#         "content": content,
#         "sources": sources,
#         "tokens_used": tokens_used,
#         "created_at": datetime.utcnow().isoformat() + "Z"
#     })


# def get_chat(chat_id: str):
#     return CHAT_STORE.get(chat_id)


# def delete_chat(chat_id: str):
#     return CHAT_STORE.pop(chat_id, None)


from typing import List, Optional
from dotenv import load_dotenv
from supabase import create_client
import os
from datetime import datetime

load_dotenv()

supabase = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_SERVICE_KEY"),
)


def create_chat(chat_id: str, repo_id: str):
    # Insert only if not exists
    existing = (
        supabase
        .table("chats")
        .select("chat_id")
        .eq("chat_id", chat_id)
        .execute()
    )

    if existing.data:
        return

    supabase.table("chats").insert({
        "chat_id": chat_id,
        "repo_id": repo_id,
    }).execute()


def append_message(
    chat_id: str,
    role: str,
    content: str,
    sources: Optional[List[str]] = None,
    tokens_used: Optional[int] = None,
):
    supabase.table("chat_messages").insert({
        "chat_id": chat_id,
        "role": role,
        "content": content,
        "sources": sources,
        "tokens_used": tokens_used,
    }).execute()


def get_chat(chat_id: str):
    chat_resp = (
        supabase
        .table("chats")
        .select("chat_id, repo_id, created_at")
        .eq("chat_id", chat_id)
        .execute()
    )

    if not chat_resp.data:
        return None

    messages_resp = (
        supabase
        .table("chat_messages")
        .select("role, content, sources, tokens_used, created_at")
        .eq("chat_id", chat_id)
        .order("created_at")
        .execute()
    )

    return {
        "repo_id": chat_resp.data[0]["repo_id"],
        "created_at": chat_resp.data[0]["created_at"],
        "messages": messages_resp.data or [],
    }


def delete_chat(chat_id: str):
    resp = (
        supabase
        .table("chats")
        .delete()
        .eq("chat_id", chat_id)
        .execute()
    )

    return resp.data
