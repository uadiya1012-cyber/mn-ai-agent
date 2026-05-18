"""RAG API — индекс, хайлт, статус."""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from agent.rag import index_knowledge, search, status
from agent.rag.ingest import reindex_all
from agent.rag.retrieve import format_hits

router = APIRouter()


class RagSearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=500)
    top_k: int = Field(default=4, ge=1, le=12)


@router.get("/status")
def rag_status() -> dict:
    return status()


@router.post("/index")
def rag_index(force: bool = Query(default=False)) -> dict:
    result = reindex_all() if force else index_knowledge()
    if not result.get("ok", True) and result.get("errors"):
        raise HTTPException(status_code=400, detail=result["message"])
    return result


@router.post("/search")
def rag_search(payload: RagSearchRequest) -> dict:
    hits = search(payload.query, top_k=payload.top_k)
    return {
        "query": payload.query,
        "count": len(hits),
        "hits": [
            {
                "source": h.source,
                "score": round(h.score, 4),
                "chunk_index": h.chunk_index,
                "content": h.content,
            }
            for h in hits
        ],
        "formatted": format_hits(hits, lang="mn"),
    }
