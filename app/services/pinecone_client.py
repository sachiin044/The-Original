from pinecone import Pinecone
from app.core.config import settings
from typing import Optional

def get_pinecone_index() -> Optional[object]:
    """
    Initializes and returns the Pinecone index if configuration is available.
    """
    if not settings.pinecone_api_key or not settings.pinecone_index_name:
        return None

    try:
        pc = Pinecone(api_key=settings.pinecone_api_key)
        index = pc.Index(settings.pinecone_index_name)
        return index
    except Exception as exc:
        print(f"[Pinecone] Initialization failed: {exc}")
        return None


def namespace_has_vectors(repo_id: str) -> bool:
    """
    Returns True if the Pinecone namespace for this repo_id
    actually contains vectors. Returns False if Pinecone is not
    configured or the namespace is empty/missing.
    """
    index = get_pinecone_index()
    if index is None:
        return False

    try:
        stats = index.describe_index_stats()
        ns_map = stats.get("namespaces", {})
        ns_info = ns_map.get(repo_id)
        return ns_info is not None and ns_info.get("vector_count", 0) > 0
    except Exception as exc:
        print(f"[Pinecone] namespace_has_vectors check failed: {exc}")
        return False
