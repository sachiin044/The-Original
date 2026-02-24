from langchain_text_splitters import RecursiveCharacterTextSplitter
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


from uuid import uuid4
from app.services.pinecone_client import get_pinecone_index

def create_vector_store(repo_id: str, documents):
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=800,
        chunk_overlap=150
    )

    all_chunks = []

    for doc in documents:
        text = (
            doc.get("text")
            or doc.get("content")
            or doc.get("body")
        )

        if not text:
            continue

        chunks = splitter.split_text(text)
        all_chunks.extend(chunks)

    rows = []

    if all_chunks:
        total_batches = (len(all_chunks) + 99) // 100
        
        for i in range(0, len(all_chunks), 100):
            batch_num = (i // 100) + 1
            print(f"[VectorStore] Embedding batch {batch_num}/{total_batches}")
            
            batch_chunks = all_chunks[i : i + 100]
            batch_vectors = embeddings.embed_documents(batch_chunks)
            
            for chunk, vector in zip(batch_chunks, batch_vectors):
                rows.append({
                    "repo_id": repo_id,
                    "content": chunk,
                    "embedding": vector,
                })

    if not rows:
        return

    # Attempt Pinecone Upsert
    index = get_pinecone_index()
    if index is not None:
        print("[VectorStore] Using Pinecone")
        try:
            vectors_to_upsert = []
            for row in rows:
                vectors_to_upsert.append({
                    "id": f"{repo_id}-{uuid4()}",
                    "values": row["embedding"],
                    "metadata": {
                        "repo_id": row["repo_id"],
                        "content": row["content"]
                    }
                })

            # Upsert in batches of 100
            for i in range(0, len(vectors_to_upsert), 100):
                batch = vectors_to_upsert[i : i + 100]
                index.upsert(vectors=batch, namespace=repo_id)
            
            return  # Success, skip Supabase
        except Exception:
            print("[VectorStore] Pinecone failed, falling back to Supabase")
    else:
        print("[VectorStore] Pinecone not configured, using Supabase")

    # Fallback to Supabase
    supabase.table("repo_embeddings").insert(rows).execute()
