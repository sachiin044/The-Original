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
import hashlib
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

    print(f"[VectorStore] Total chunks to embed: {len(all_chunks)}")

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
        print(f"[VectorStore] No rows generated — skipping upsert (documents={len(documents)}, chunks={len(all_chunks)})")
        return

    print(f"[VectorStore] Generated {len(rows)} embedding rows")

    # Attempt Pinecone Upsert
    index = get_pinecone_index()
    if index is not None:
        print("[VectorStore] Using Pinecone")
        try:
            vectors_to_upsert = []
            for idx, row in enumerate(rows):
                # Deterministic ID: same repo + same position → same ID on every re-index
                # This ensures upsert OVERWRITES existing vectors instead of duplicating
                chunk_hash = hashlib.sha256(row["content"].encode()).hexdigest()[:16]
                vectors_to_upsert.append({
                    "id": f"{repo_id}-{chunk_hash}",
                    "values": row["embedding"],
                    "metadata": {
                        "repo_id": row["repo_id"],
                        "content": row["content"]
                    }
                })

            print(f"[VectorStore] Upserting {len(vectors_to_upsert)} vectors to Pinecone namespace='{repo_id}'")

            # Upsert in batches of 100
            total_upserted = 0
            for i in range(0, len(vectors_to_upsert), 100):
                batch = vectors_to_upsert[i : i + 100]
                resp = index.upsert(vectors=batch, namespace=repo_id)
                batch_count = getattr(resp, "upserted_count", len(batch))
                total_upserted += batch_count
                print(f"[VectorStore] Batch {i//100 + 1}: upserted_count={batch_count}")

            print(f"[VectorStore] ✅ Pinecone total upserted={total_upserted} for repo_id={repo_id}")
            
            return  # Success, skip Supabase
        except Exception as exc:
            print(f"[VectorStore] Pinecone upsert failed: {exc}")
            print("[VectorStore] Falling back to Supabase")
    else:
        print("[VectorStore] Pinecone not configured, using Supabase")

    # Fallback to Supabase — delete existing rows first to prevent duplication
    print(f"[VectorStore] Clearing existing Supabase embeddings for repo_id={repo_id}")
    supabase.table("repo_embeddings").delete().eq("repo_id", repo_id).execute()
    supabase.table("repo_embeddings").insert(rows).execute()
