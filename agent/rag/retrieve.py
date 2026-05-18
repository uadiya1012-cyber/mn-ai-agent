"""Semantic search + контекст форматлах."""

from agent.ollama_client import OllamaError, embed
from agent.rag.config import is_enabled, load_rag_config
from agent.rag.store import ChunkHit, chunk_count, search_vectors


def search(query: str, top_k: int | None = None) -> list[ChunkHit]:
    if not is_enabled() or not query.strip():
        return []
    if chunk_count() == 0:
        return []

    cfg = load_rag_config()
    k = top_k or cfg["top_k"]
    try:
        vectors = embed(query.strip(), cfg["embed_model"])
    except OllamaError:
        return []
    if not vectors:
        return []

    return search_vectors(
        vectors[0],
        top_k=k,
        min_score=cfg["min_score"],
    )


def format_hits(hits: list[ChunkHit], lang: str = "mn") -> str:
    if not hits:
        if lang == "mn":
            return "❌ Мэдлэгийн санд тохирох хэсэг олдсонгүй."
        return "❌ No matching knowledge found."

    header = (
        "📚 Мэдлэгийн сангаас олдсон хэсгүүд:"
        if lang == "mn"
        else "📚 Knowledge base excerpts:"
    )
    parts = [header]
    for i, hit in enumerate(hits, 1):
        parts.append(
            f"\n[{i}] {hit.source} (score {hit.score:.2f})\n{hit.content}"
        )
    return "\n".join(parts)


def build_context_block(query: str, lang: str = "mn") -> str:
    """Agent system/user-д нэмэх контекст — олдохгүй бол хоосон."""
    hits = search(query)
    if not hits:
        return ""

    if lang == "mn":
        intro = (
            "Доорх мэдлэгийн сангийн хэсгүүдийг ашигла. "
            "Эх сурвалжид байхгүй зүйлийг зохиож бүү бич.\n"
        )
    else:
        intro = (
            "Use the knowledge base excerpts below. "
            "Do not invent facts not supported by the sources.\n"
        )
    return intro + format_hits(hits, lang=lang)
