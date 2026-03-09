import os
import requests
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from app.schemas.models import RepoRequest, RegisterRepoRequest, PrivateRepoRequest
from app.services.ingest import clone_repo, read_repo_files, clone_private_repo
from app.services.embed import create_vector_store
from app.services.memory import clear_all_conversations
from app.services.pinecone_client import namespace_has_vectors
from app.auth.dependency import verify_api_key
from app.auth.rate_limit import rate_limit
from app.core.db import get_supabase
from app.utils.repo_id import get_repo_id
from app.utils.crypto import decrypt_token

# Local helper - moved from main.py but modified slightly
def _resolve_repo_path(repo_path: str, rel_path: str) -> str | None:
    if not rel_path:
        return None
    if os.path.isabs(rel_path):
        return None

    full = os.path.normpath(os.path.join(repo_path, rel_path))
    real_full = os.path.realpath(full)
    real_repo = os.path.realpath(repo_path)

    if real_full == real_repo or not real_full.startswith(real_repo + os.sep):
        return None

    return real_full

def read_file_content(repo_path: str, rel_path: str) -> tuple[str | None, str | None]:
    resolved = _resolve_repo_path(repo_path, rel_path)
    if resolved is None:
        return None, "invalid_path"

    if not os.path.isfile(resolved):
        return None, "not_found"

    try:
        with open(resolved, "r", encoding="utf-8", errors="ignore") as f:
            return f.read(), None
    except Exception:
        return None, "unreadable"


router = APIRouter()
supabase = get_supabase()


def _has_new_commits_since(repo_url: str, since_iso: str, github_token: str | None) -> bool:
    """
    Returns True if the GitHub repo has any commits newer than `since_iso`.
    Safe-defaults to True (allow re-index) on any error so indexing is never
    silently blocked by a network or auth problem.
    """
    try:
        path = (
            repo_url.rstrip("/")
            .replace("https://github.com/", "")
            .replace(".git", "")
        )
        parts = path.split("/")
        if len(parts) < 2:
            return True  # Can't parse URL — allow indexing

        owner, repo = parts[0], parts[1]
        headers = {"Accept": "application/vnd.github+json"}
        if github_token:
            headers["Authorization"] = f"Bearer {github_token}"

        resp = requests.get(
            f"https://api.github.com/repos/{owner}/{repo}/commits",
            headers=headers,
            params={"per_page": 1, "since": since_iso},
            timeout=10,
        )

        if resp.status_code == 200:
            return len(resp.json()) > 0  # True → new commits exist → re-index

        # 401/403/404 — token missing or no access; allow indexing as safe default
        return True

    except Exception:
        return True  # Network error — safe default: allow indexing

def _index_repo_background(repo_id: str, repo_url: str):
    import traceback
    print(f"[Indexing] Starting background indexing for repo_id={repo_id}")
    try:
        repo_path = clone_repo(repo_url)
        print(f"[Indexing] Cloned repo to {repo_path}")

        documents, manifest = read_repo_files(repo_path)
        print(f"[Indexing] Read {len(documents)} documents")

        create_vector_store(repo_id, documents)
        print(f"[Indexing] Embeddings stored for repo_id={repo_id}")

        supabase.table("repos").update({
            "indexed_at": datetime.utcnow().isoformat() + "Z",
            "manifest": manifest,
        }).eq("repo_id", repo_id).execute()

        print(f"[Indexing] ✅ Completed for repo_id={repo_id}")

    except Exception as exc:
        print(f"[Indexing] ❌ FAILED for repo_id={repo_id}: {exc}")
        print(traceback.format_exc())


@router.post("/upload-repo")
def upload_repo(
    data: RepoRequest,
    api_key_id: str = Depends(verify_api_key),
    _: None = Depends(rate_limit("upload")),
):
    # Reset all conversations
    clear_all_conversations()

    # 1️⃣ Generate repo_id
    repo_id = get_repo_id(data.repo_url)

    # 2️⃣ Clone repo
    repo_path = clone_repo(data.repo_url)

    # 3️⃣ Read files + build manifest
    documents, manifest = read_repo_files(repo_path)

    # 4️⃣ Store embeddings (persistent)
    create_vector_store(repo_id, documents)

    # 5️⃣ Upsert repo metadata
    supabase.table("repos").upsert({
        "repo_id": repo_id,
        "repo_url": data.repo_url,
        "manifest": manifest,
        "indexed_at": datetime.utcnow().isoformat() + "Z"
    }).execute()

    return {
        "status": "Repository indexed successfully",
        "repo_id": repo_id
    }


@router.post("/repos/register")
def register_repo(data: RegisterRepoRequest):
    """
    Register a repository and return repo_id.
    Does NOT index the repo.
    No authentication required.
    """

    # 🔐 PDF-required guard (ADD THIS)
    if data.visibility == "private" and not data.credential_id:
        return {"error": "credential_id required for private repositories"}

    # 1️⃣ Generate deterministic repo_id (already used in /chat)
    repo_id = get_repo_id(data.repo_url)

    # 2️⃣ Check if repo already registered
    existing = (
        supabase
        .table("repos")
        .select("repo_id")
        .eq("repo_id", repo_id)
        .execute()
    )

    if existing.data:
        return {
            "repo_id": repo_id,
            "status": "already_registered",
        }

    # 3️⃣ Insert repo metadata
    supabase.table("repos").insert({
        "repo_id": repo_id,
        "repo_url": data.repo_url,
        "credential_id": data.credential_id, 
    }).execute()

    return {
        "repo_id": repo_id,
        "status": "registered",
    }


@router.post("/repos/{repo_id}/index")
def index_repo(
    repo_id: str,
    background_tasks: BackgroundTasks,
    force: bool = False,
    _: None = Depends(rate_limit("index"))):
    """
    Starts async repository indexing.
    Pass ?force=true to re-index an already-indexed repository.
    No authentication required.
    """

    # 1️⃣ Fetch repo metadata including indexed_at and credential_id
    repo_resp = (
        supabase
        .table("repos")
        .select("repo_url, indexed_at, credential_id")
        .eq("repo_id", repo_id)
        .execute()
    )

    if not repo_resp.data:
        raise HTTPException(
            status_code=404,
            detail="Repository not registered"
        )

    repo_row = repo_resp.data[0]
    repo_url = repo_row["repo_url"]
    indexed_at = repo_row.get("indexed_at")

    # 2️⃣ If already indexed and not force: check for new commits since indexing
    if indexed_at and not force:
        # Try to resolve a GitHub token for the API call (optional — public repos work without)
        github_token: str | None = None
        credential_id = repo_row.get("credential_id")
        if credential_id:
            try:
                cred_resp = (
                    supabase.table("credentials")
                    .select("encrypted_token, status")
                    .eq("id", credential_id)
                    .execute()
                )
                if cred_resp.data and cred_resp.data[0]["status"] in ("validated", "active"):
                    github_token = decrypt_token(cred_resp.data[0]["encrypted_token"])
            except Exception:
                pass  # Proceed without token — safe default

        if not _has_new_commits_since(repo_url, indexed_at, github_token):
            # Verify vectors actually exist in Pinecone before trusting indexed_at
            if namespace_has_vectors(repo_id):
                return {
                    "index_id": f"idx_{repo_id}",
                    "status": "already_indexed",
                    "indexed_at": indexed_at,
                }
            # Vectors missing — fall through to re-index
            print(f"[Indexing] indexed_at is set but no vectors found in Pinecone for repo_id={repo_id} — re-indexing")

        print(f"[Indexing] New commits detected since {indexed_at} — re-indexing repo_id={repo_id}")

    # 2️⃣ Start background indexing
    background_tasks.add_task(
        _index_repo_background,
        repo_id,
        repo_url,
    )

    # 3️⃣ Return immediately (PDF compliant)
    return {
        "index_id": f"idx_{repo_id}",
        "status": "started"
    }


@router.get("/repos/{repo_id}/status")
def repo_status(repo_id: str):
    """
    Get repository indexing status.
    No authentication required.
    """

    repo_resp = (
        supabase
        .table("repos")
        .select("indexed_at, manifest,  created_at")
        .eq("repo_id", repo_id)
        .execute()
    )

    if not repo_resp.data:
        raise HTTPException(
            status_code=404,
            detail="Repository not registered"
        )

    repo = repo_resp.data[0]

    # Use Pinecone as source of truth
    if namespace_has_vectors(repo_id):
        status = "indexed"
    else:
        status = "not_indexed"

    return {
        "repo_id": repo_id,
        "status": status,
        "last_indexed_at": repo.get("indexed_at"),
    }


@router.get("/repos/{repo_id}/tree")
def repo_tree(repo_id: str):

    repo_resp = (
        supabase
        .table("repos")
        .select("manifest")
        .eq("repo_id", repo_id)
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

    tree = []

    for folder, files in manifest.get("structure", {}).items():

        if folder.startswith(".git"):
            continue

        folder_path = "" if folder == "." else f"{folder}/"

        if folder_path:
            tree.append({
                "path": folder_path,
                "type": "dir"
            })

        for f in files:
            if f.startswith(".git"):
                continue

            tree.append({
                "path": f"{folder_path}{f}",
                "type": "file"
            })

    return {
        "repo_id": repo_id,
        "tree": tree
    }


@router.get("/repos/{repo_id}/files")
def repo_file(repo_id: str, path: str):
    """
    Get file content from repository.
    Requires repo to be indexed.
    No authentication required.
    """

    # 1️⃣ Fetch repo metadata
    repo_resp = (
        supabase
        .table("repos")
        .select("repo_url, indexed_at")
        .eq("repo_id", repo_id)
        .execute()
    )

    if not repo_resp.data:
        raise HTTPException(
            status_code=404,
            detail="Repository not registered"
        )

    repo = repo_resp.data[0]

    if not repo.get("indexed_at"):
        raise HTTPException(
            status_code=400,
            detail="Repository not indexed"
        )

    repo_url = repo["repo_url"]

    # 2️⃣ Clone repo deterministically
    repo_path = clone_repo(repo_url)

    # 3️⃣ Read file safely (your existing secure logic)
    content, err = read_file_content(repo_path, path)

    if err == "invalid_path":
        raise HTTPException(status_code=400, detail="Invalid file path")
    if err == "not_found":
        raise HTTPException(status_code=404, detail="File not found")
    if err == "unreadable":
        raise HTTPException(status_code=500, detail="Unable to read file")

    return {
        "repo_id": repo_id,
        "path": path,
        "content": content
    }


@router.post("/private-repo-access")
def private_repo_access(
    data: PrivateRepoRequest,
    api_key_id: str = Depends(verify_api_key),
):
    """
    Access and index a private GitHub repository using a per-request token.
    Replaces the currently indexed repository.
    """

    # global VECTOR_STORE, REPO_MANIFEST, REPO_PATH

    if not data.repo_url or not data.github_token:
        return {"error": "repo_url and github_token are required"}

    clear_all_conversations()

    try:
        repo_path = clone_private_repo(
            data.repo_url,
            data.github_token
        )
    except Exception:
        # logger.exception("Private repo clone failed") # logger needs to be imported or removed/replaced
        raise HTTPException(
            status_code=500,
            detail="Failed to access private repository"
        )


    documents, manifest = read_repo_files(repo_path)

    repo_id = get_repo_id(data.repo_url)

    # Store embeddings persistently
    create_vector_store(repo_id, documents)

    # Persist manifest + indexed_at
    supabase.table("repos").upsert({
        "repo_id": repo_id,
        "repo_url": data.repo_url,
        "manifest": manifest,
        "indexed_at": datetime.utcnow().isoformat() + "Z"
    }).execute()

    return {
        "status": "Private repository indexed successfully",
        "repo_id": repo_id
    }
