"""RAG — локал мэдлэгийн сан (Ollama embedding + SQLite)."""

from agent.rag.ingest import index_knowledge
from agent.rag.retrieve import format_hits, search
from agent.rag.config import load_rag_config, is_enabled, knowledge_dir, status

__all__ = [
    "index_knowledge",
    "search",
    "format_hits",
    "load_rag_config",
    "is_enabled",
    "knowledge_dir",
    "status",
]
