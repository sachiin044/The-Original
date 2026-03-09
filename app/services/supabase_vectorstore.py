from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings
from supabase import create_client
from dotenv import load_dotenv

import os

load_dotenv()

supabase = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_SERVICE_KEY"),
)

embeddings = OpenAIEmbeddings(
    model="text-embedding-3-small"
)


from app.services.pinecone_client import get_pinecone_index

class SupabaseVectorStore:
    def __init__(self, repo_id: str):
        self.repo_id = repo_id

    def similarity_search(self, query: str, k: int = 20):
        query_vector = embeddings.embed_query(query)

        index = get_pinecone_index()
        if index is not None:
            print("[VectorStore] Searching in Pinecone")
            try:
                search_results = index.query(
                    vector=query_vector,
                    top_k=k,
                    namespace=self.repo_id,
                    include_metadata=True
                )
                
                return [
                    Document(page_content=match.metadata["content"])
                    for match in search_results.matches
                ]
            except Exception:
                print("[VectorStore] Pinecone search failed, falling back to Supabase")
        else:
            print("[VectorStore] Pinecone not configured, using Supabase search")

        response = supabase.rpc(
            "match_repo_embeddings",
            {
                "query_embedding": query_vector,
                "match_repo_id": self.repo_id,
                "match_count": k,
            },
        ).execute()

        results = response.data or []

        return [
            Document(page_content=row["content"])
            for row in results
        ]
