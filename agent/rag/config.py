"""RAG тохиргоо — config.toml [rag] хэсэг."""

import tomllib
from pathlib import Path

_BASE = Path(__file__).parent.parent.parent


def load_rag_config() -> dict:
    with open(_BASE / "config.toml", "rb") as f:
        cfg = tomllib.load(f)
    rag = cfg.get("rag", {})
    return {
        "enabled": bool(rag.get("enabled", True)),
        "knowledge_dir": str(rag.get("knowledge_dir", "knowledge")),
        "index_db": str(rag.get("index_db", "data/rag.db")),
        "embed_model": str(rag.get("embed_model", "nomic-embed-text")),
        "chunk_size": int(rag.get("chunk_size", 500)),
        "chunk_overlap": int(rag.get("chunk_overlap", 80)),
        "top_k": int(rag.get("top_k", 4)),
        "min_score": float(rag.get("min_score", 0.32)),
        "auto_inject": bool(rag.get("auto_inject", True)),
    }


def is_enabled() -> bool:
    return load_rag_config()["enabled"]


def knowledge_dir() -> Path:
    rel = load_rag_config()["knowledge_dir"]
    path = (_BASE / rel).resolve()
    path.mkdir(parents=True, exist_ok=True)
    return path


def index_db_path() -> Path:
    rel = load_rag_config()["index_db"]
    path = (_BASE / rel).resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def status() -> dict:
    from agent.rag.store import chunk_count, list_sources

    cfg = load_rag_config()
    kdir = knowledge_dir()
    files = sorted(
        p for p in kdir.rglob("*") if p.is_file() and not p.name.startswith(".")
    )
    return {
        "enabled": cfg["enabled"],
        "knowledge_dir": str(kdir),
        "index_db": str(index_db_path()),
        "embed_model": cfg["embed_model"],
        "files_on_disk": len(files),
        "chunks_indexed": chunk_count(),
        "sources": list_sources(),
        "chunk_size": cfg["chunk_size"],
        "top_k": cfg["top_k"],
        "min_score": cfg["min_score"],
    }
