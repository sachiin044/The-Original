import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Body
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document

from app.schemas.models import ChatRequest, IssueChatRequest, PullRequestChatRequest
from app.services.chat_store import (
    create_chat,
    append_message,
    get_chat,
    delete_chat,
)
from app.services.rag import ask_question
from app.services.question_router import route_question
from app.services.issues_chat import (
    fetch_issue_documents,
    fetch_repository_issues,
    filter_issues_by_query,
)
from app.services.pr_chat import (
    fetch_pr_documents,
    fetch_repository_prs,
    filter_prs_by_query
)
from app.services.supabase_vectorstore import SupabaseVectorStore
from app.auth.dependency import RequireChatScopes, verify_api_key
from app.auth.rate_limit import rate_limit
from app.core.db import get_supabase
from app.utils.crypto import decrypt_token

router = APIRouter()
supabase = get_supabase()

def is_greeting(question: str) -> bool:
    q = question.lower().strip()
    return q in {
        "hi", "hii", "hello", "hey", "hey there",
        "good morning", "good afternoon", "good evening"
    }

def is_last_question_query(text: str) -> bool:
    t = text.lower().strip()
    return any(p in t for p in [
        "last question",
        "previous question",
        "what did i ask",
        "what was my last"
    ])

def format_folder_structure(manifest: dict) -> str:
    lines = []
    for folder, files in manifest.get("structure", {}).items():
        if folder.startswith(".git"):
            continue
        folder_name = "repo" if folder == "." else folder
        lines.append(f"{folder_name}/")
        for f in files:
            lines.append(f"  ├─ {f}")
    return "\n".join(lines)


@router.post("/chat")
def chat(
    data: ChatRequest,
    api_key_id: str = Depends(RequireChatScopes()),
    _: None = Depends(rate_limit("chat")),
):
    # Chat ID
    chat_id = data.chat_id or str(uuid.uuid4())
    
    # Repo indexed guard FIRST
    repo_resp = (
        supabase
        .table("repos")
        .select("indexed_at")
        .eq("repo_id", data.repo_id)
        .execute()
    )

    if not repo_resp.data:
        raise HTTPException(
            status_code=404,
            detail="Repository not registered"
        )

    if not repo_resp.data[0].get("indexed_at"):
        raise HTTPException(
            status_code=400,
            detail="Repository is not indexed yet. Please index it first."
        )

    # Create chat
    create_chat(
        chat_id=chat_id,
        repo_id=data.repo_id,
    )

    # Store user message
    append_message(
        chat_id=chat_id,
        role="user",
        content=data.message
    )

    # Greeting handling
    if is_greeting(data.message):
        answer = (
            "Hi 👋 I’m here to help you understand this repository.\n\n"
            "You can ask things like:\n"
            "- What does a file do?\n"
            "- Show code of a file\n"
            "- Explain the architecture\n"
            "- How different parts work together"
        )

        append_message(
            chat_id=chat_id,
            role="assistant",
            content=answer
        )

        return {
            "chat_id": chat_id,
            "reply": answer,
            "tokens_used": None,
            "sources": [],
            "created_at": datetime.utcnow().isoformat() + "Z",
        }

    route = route_question(data.message)

    # DETERMINISTIC MEMORY QUERY
    if is_last_question_query(data.message):
        chat = get_chat(chat_id)

        if not chat:
            raise HTTPException(
                status_code=404,
                detail="Chat not found"
            )

        user_messages = [
            m for m in chat["messages"]
            if m["role"] == "user"
        ]

        if len(user_messages) < 2:
            answer = "This is your first question in this chat."
        else:
            answer = f'Your last question was: "{user_messages[-2]["content"]}"'

        append_message(
            chat_id=chat_id,
            role="assistant",
            content=answer
        )

        return {
            "chat_id": chat_id,
            "reply": answer,
            "tokens_used": 0,
            "sources": [],
            "created_at": datetime.utcnow().isoformat() + "Z",
        }

    # STRUCTURAL
    if route == "STRUCTURAL":
        repo_resp = (
            supabase
            .table("repos")
            .select("manifest")
            .eq("repo_id", data.repo_id)
            .execute()
        )

        if not repo_resp.data:
            raise HTTPException(
                status_code=404,
                detail="Repository not registered"
            )

        manifest = repo_resp.data[0].get("manifest")

        if not manifest:
            raise HTTPException(
                status_code=400,
                detail="Repository not indexed"
            )

        answer = format_folder_structure(manifest)

        append_message(
            chat_id=chat_id,
            role="assistant",
            content=answer
        )

        return {
            "chat_id": chat_id,
            "reply": answer,
            "tokens_used": None,
            "sources": [],
            "created_at": datetime.utcnow().isoformat() + "Z",
        }

    # DEFAULT → SEMANTIC (RAG)
    vector_store = SupabaseVectorStore(data.repo_id)

    response = ask_question(
        vectorstore=vector_store,
        question=data.message,
        session_id=chat_id,
        context=data.context,
    )

    answer = response["answer"]

    append_message(
        chat_id=chat_id,
        role="assistant",
        content=answer,
        sources=response.get("sources"),
        tokens_used=response.get("tokens_used"),
    )

    return {
        "chat_id": chat_id,
        "reply": answer,
        "tokens_used": response.get("tokens_used"),
        "sources": response.get("sources", []),
        "created_at": datetime.utcnow().isoformat() + "Z",
    }


@router.get("/chat/{chat_id}")
def get_chat_history(
    chat_id: str,
    api_key_id: str = Depends(verify_api_key),
):
    chat = get_chat(chat_id)

    if not chat:
        return {"error": "Chat not found"}

    return {
        "repo_id": chat.get("repo_id"),
        "messages": [
            {
                "role": m["role"],
                "content": m["content"]
            }
            for m in chat["messages"]
        ]
    }

@router.delete("/chat/{chat_id}")
def delete_chat_session(
    chat_id: str,
    api_key_id: str = Depends(verify_api_key),
):
    deleted = delete_chat(chat_id)

    if not deleted:
        return {"error": "Chat not found"}

    return {"status": "deleted"}


@router.post(
    "/issues/chat",
    summary="Chat about a specific GitHub issue",
    description="Chat about a GitHub issue: problem understanding, history, and resolution paths."
)
def issues_chat(
    data: IssueChatRequest = Body(
        ...,
        embed=False,
        example={
            "repo_id": "b44bd5ed97fb1c25",
            "issue_number": 128,
            "chat_id": "chat_202",
            "message": "Summarize this issue and possible fixes",
            "context": {
                "include_comments": True,
                "depth": "medium"
            }
        }
    ),
    api_key_id: str = Depends(verify_api_key),
):
    """
    Chat about a specific GitHub issue.
    PDF compliant. Does NOT affect repo chat.
    """

    # 1️⃣ Resolve chat_id
    chat_id = data.chat_id or str(uuid.uuid4())

    # 2️⃣ Ensure repo exists
    repo_resp = (
        supabase
        .table("repos")
        .select("repo_url, credential_id")
        .eq("repo_id", data.repo_id)
        .execute()
    )

    if not repo_resp.data:
        return {"error": "Repository not registered"}

    repo_url = repo_resp.data[0]["repo_url"]
    credential_id = repo_resp.data[0].get("credential_id")

    repo_full_name = (
        repo_url
        .replace("https://github.com/", "")
        .replace(".git", "")
    )

    # 3️⃣ Fetch and decrypt credentials if available (reused from PR chat)
    github_token = None
    if credential_id:
        cred_resp = (
            supabase
            .table("credentials")
            .select("encrypted_token, status")
            .eq("id", credential_id)
            .execute()
        )
        if cred_resp.data:
            cred = cred_resp.data[0]
            if cred["status"] in ["validated", "active"]:
                github_token = decrypt_token(cred["encrypted_token"])


    # 3️⃣ Create chat (isolated from repo chat)
    create_chat(
        chat_id=chat_id,
        repo_id=data.repo_id,
    )

    # 4️⃣ Store user message
    append_message(
        chat_id=chat_id,
        role="user",
        content=data.message,
    )

    # 5️⃣ Context handling (PDF aligned)
    include_comments = True
    # depth = "medium" # Unused

    if data.context:
        include_comments = data.context.get("include_comments", True)
        # depth = data.context.get("depth", "medium")

    # 6️⃣ Branch: Repo-level vs Single Issue
    if not data.issue_number:
        # === REPO LEVEL FLOW ===
        try:
            issues = fetch_repository_issues(
                repo_full_name=repo_full_name,
                github_token=github_token,
                limit=100
            )
            answer = filter_issues_by_query(
                issues=issues,
                query=data.message,
                repo_full_name=repo_full_name,
                github_token=github_token
            )
            sources = []
            tokens_used = 0
            
            append_message(
                chat_id=chat_id,
                role="assistant",
                content=answer,
                sources=sources,
                tokens_used=tokens_used,
            )
            
            return {
                "chat_id": chat_id,
                "reply": answer,
                "sources": sources,
                "tokens_used": tokens_used,
                "created_at": datetime.utcnow().isoformat() + "Z",
            }
            
        except ValueError as e:
            raise HTTPException(status_code=502, detail=str(e))

    # === SINGLE ISSUE FLOW ===
    # 7️⃣ Fetch issue documents
    documents = fetch_issue_documents(
        repo_full_name=repo_full_name,
        issue_number=data.issue_number,
        include_comments=include_comments,
        github_token=github_token,
    )

    # 7️⃣ Build TEMP vector store (issue-only)
    splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=150)
    texts = []

    for doc in documents:
        text = doc.get("text") or doc.get("content") or doc.get("body")
        if text:
            texts.extend(splitter.split_text(text))

    if not texts:
         # Handle case with no text (e.g. empty issue)
         # Fallback to empty store or error? 
         # For now, just create empty to avoid crash if possible, or precise error.
         # FAISS.from_texts requires non-empty text.
         # Let's add a dummy text if empty to avoid crash, but ideally should return that no info found.
         texts = ["No content found for this issue."]


    embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
    vector_store = FAISS.from_texts(texts, embedding=embeddings)

    # 8️⃣ Ask question (reuse existing RAG)
    response = ask_question(
        vectorstore=vector_store,
        question=data.message,
        session_id=chat_id,
        context=data.context,
    )

    # 9️⃣ Store assistant reply
    append_message(
        chat_id=chat_id,
        role="assistant",
        content=response["answer"],
        sources=response.get("sources"),
        tokens_used=response.get("tokens_used"),
    )

    return {
        "chat_id": chat_id,
        "reply": response["answer"],
        "sources": response.get("sources", []),
        "tokens_used": response.get("tokens_used"),
        "created_at": datetime.utcnow().isoformat() + "Z",
    }


@router.post(
    "/pull-requests/chat",
    summary="Chat about a specific Pull Request",
    description="Chat about PR diff, reviews, CI status, intent, and risk."
)
def pull_request_chat(
    data: PullRequestChatRequest,
    api_key_id: str = Depends(verify_api_key),
):
    chat_id = data.chat_id or str(uuid.uuid4())

    repo_resp = (
        supabase
        .table("repos")
        .select("repo_url, credential_id")
        .eq("repo_id", data.repo_id)
        .execute()
    )

    if not repo_resp.data:
        raise HTTPException(
            status_code=404,
            detail="Repository not registered"
        )

    repo_url = repo_resp.data[0]["repo_url"]
    credential_id = repo_resp.data[0].get("credential_id")

    repo_full_name = (
        repo_url
        .rstrip("/")
        .replace("https://github.com/", "")
        .replace(".git", "")
    )

    github_token = None

    if credential_id:
        cred_resp = (
            supabase
            .table("credentials")
            .select("encrypted_token, status")
            .eq("id", credential_id)
            .execute()
        )

        if not cred_resp.data:
            # Log inconsistency but continue safely (treat as public repo)
            print(f"[WARN] Credential ID {credential_id} not found for repo {data.repo_id}")

        else:
            cred = cred_resp.data[0]
            if cred["status"] not in ["validated", "active"]:
                raise HTTPException(
                    status_code=403,
                    detail="GitHub credential not verified"
                )
            
            github_token = decrypt_token(cred["encrypted_token"])

    create_chat(chat_id=chat_id, repo_id=data.repo_id)

    append_message(chat_id=chat_id, role="user", content=data.message)

    include_diff = True
    include_checks = True

    if data.context:
        include_diff = data.context.get("include_diff", True)
        include_checks = data.context.get("include_checks", True)

    if data.pr_number:
        # === EXISTING SINGLE PR FLOW ===
        documents = fetch_pr_documents(
            repo_full_name=repo_full_name,
            pr_number=data.pr_number,
            github_token=github_token,
            include_diff=include_diff,
            include_checks=include_checks,
        )

        splitter = RecursiveCharacterTextSplitter(
            chunk_size=800,
            chunk_overlap=150
        )

        texts = []
        for doc in documents:
            content = doc.get("content")
            if content:
                for chunk in splitter.split_text(content):
                    texts.append({
                        "page_content": chunk,
                        "metadata": {"source": doc.get("source")}
                    })

        if not texts:
            texts = [{"page_content": "No PR content available.", "metadata": {"source": "system"}}]

        embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
        
        docs = [
            Document(page_content=t["page_content"], metadata=t["metadata"])
            for t in texts
        ]

        vector_store = FAISS.from_documents(docs, embedding=embeddings)

        response = ask_question(
            vectorstore=vector_store,
            question=data.message,
            session_id=chat_id,
            context=data.context,
        )

        answer = response["answer"]
        sources = response.get("sources", [])
        tokens_used = response.get("tokens_used")

    else:
        # === NEW REPO-LEVEL QUERY FLOW ===
        try:
            # 1. Fetch metadata (capped at 100)
            repo_prs = fetch_repository_prs(
                repo_full_name=repo_full_name,
                github_token=github_token,
                limit=100
            )
            
            # 2. Filter & format (smart, UTC-safe, deep fetch capped at 10)
            answer = filter_prs_by_query(
                prs=repo_prs,
                query=data.message,
                repo_full_name=repo_full_name,
                github_token=github_token
            )
            
            sources = []
            tokens_used = 0
            
        except ValueError as e:
            # Clean error for user
            raise HTTPException(status_code=502, detail=str(e))

    # === UNIFIED RESPONSE ===
    append_message(
        chat_id=chat_id,
        role="assistant",
        content=answer,
        sources=sources,
        tokens_used=tokens_used,
    )

    return {
        "chat_id": chat_id,
        "reply": answer,
        "sources": sources,
        "tokens_used": tokens_used,
        "created_at": datetime.utcnow().isoformat() + "Z",
    }
