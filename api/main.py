"""
Lab 2 — Production RAG API
FastAPI server with configurable chunking strategy.
"""

from fastapi import FastAPI, Query
from fastapi.responses import StreamingResponse
from pathlib import Path
import json
import numpy as np
from sentence_transformers import SentenceTransformer
import faiss
from typing import Optional
import asyncio

app = FastAPI(title="LLM Engineer Lab 2 - RAG API")

MODEL = None
INDICES = {}
CHUNKS = {}


@app.on_event("startup")
async def load_model():
    global MODEL, INDICES, CHUNKS

    print("Loading embedding model...")
    MODEL = SentenceTransformer("all-MiniLM-L6-v2")

    chunks_dir = Path("data/chunks")
    for strategy in ["character", "recursive", "semantic", "llm"]:
        print(f"Loading {strategy} chunks...")
        chunk_data = json.loads(
            (chunks_dir / f"chunks_{strategy}.json").read_text(encoding="utf-8")
        )
        CHUNKS[strategy] = chunk_data

        texts = [c["text"] for c in chunk_data]
        embeddings = MODEL.encode(texts, normalize_embeddings=True)

        dim = embeddings.shape[1]
        index = faiss.IndexFlatIP(dim)
        index.add(embeddings.astype(np.float32))
        INDICES[strategy] = index

    print("Ready!")


async def stream_response(text: str):
    for word in text.split():
        yield f"{word} "
        await asyncio.sleep(0.05)


@app.get("/")
async def root():
    return {
        "service": "LLM Engineer Lab 2 - RAG API",
        "strategies": list(INDICES.keys()),
        "endpoints": {
            "/search": "Search with configurable strategy",
            "/health": "Health check",
        },
    }


@app.get("/health")
async def health():
    return {"status": "ok", "strategies_loaded": len(INDICES)}


@app.get("/search")
async def search(
    q: str = Query(..., description="Search query"),
    strategy: str = Query("character", description="Chunking strategy"),
    k: int = Query(3, description="Number of results"),
):
    if strategy not in INDICES:
        return {"error": f"Strategy {strategy} not found. Available: {list(INDICES.keys())}"}

    query_emb = MODEL.encode([q], normalize_embeddings=True)
    scores, indices = INDICES[strategy].search(query_emb.astype(np.float32), k)

    results = []
    for idx, score in zip(indices[0], scores[0]):
        chunk = CHUNKS[strategy][idx]
        results.append({
            "score": float(score),
            "text": chunk["text"][:500],
            "source": chunk["metadata"]["source"],
            "chunk_id": chunk["chunk_id"],
            "char_count": chunk["char_count"],
        })

    return {
        "query": q,
        "strategy": strategy,
        "k": k,
        "results": results,
    }


@app.get("/search/stream")
async def search_stream(
    q: str = Query(..., description="Search query"),
    strategy: str = Query("character", description="Chunking strategy"),
    k: int = Query(3, description="Number of results"),
):
    if strategy not in INDICES:
        return {"error": f"Strategy {strategy} not found."}

    query_emb = MODEL.encode([q], normalize_embeddings=True)
    scores, indices = INDICES[strategy].search(query_emb.astype(np.float32), k)
    top_text = CHUNKS[strategy][indices[0][0]]["text"]
    return StreamingResponse(stream_response(top_text), media_type="text/plain")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)