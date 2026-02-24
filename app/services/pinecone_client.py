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
    except Exception:
        print("[Pinecone] Initialization failed, falling back to Supabase.")
        return None
