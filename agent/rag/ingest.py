"""knowledge/ хавтасны файлуудыг индекслэх."""

import hashlib
from pathlib import Path

from agent.ollama_client import OllamaError, embed
from agent.rag.chunking import chunk_text
from agent.rag.config import knowledge_dir, load_rag_config
from agent.rag.store import clear_all, get_file_hash, upsert_file_chunks

SUPPORTED_SUFFIXES = {".md", ".txt", ".markdown", ".rst"}


def _file_hash(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def read_document(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore").strip()


def discover_files(root: Path | None = None) -> list[Path]:
    root = root or knowledge_dir()
    return sorted(
        p
        for p in root.rglob("*")
        if p.is_file()
        and p.suffix.lower() in SUPPORTED_SUFFIXES
        and not p.name.startswith(".")
    )


def index_knowledge(*, force: bool = False, root: Path | None = None) -> dict:
    """
    knowledge/ доторх баримтуудыг индекслэнэ.
    force=True бол hash үл харгалзан бүгдийг дахин индекслэнэ.
    """
    cfg = load_rag_config()
    files = discover_files(root)
    if not files:
        return {
            "ok": True,
            "indexed": 0,
            "skipped": 0,
            "chunks": 0,
            "message": "Индекслэх файл олдсонгүй. knowledge/ хавтас руу .md/.txt нэмнэ үү.",
        }

    indexed = 0
    skipped = 0
    total_chunks = 0
    errors: list[str] = []

    for path in files:
        rel = str(path.relative_to(knowledge_dir()))
        try:
            text = read_document(path)
            if not text:
                skipped += 1
                continue

            digest = _file_hash(text)
            if not force and get_file_hash(rel) == digest:
                skipped += 1
                continue

            pieces = chunk_text(
                text,
                size=cfg["chunk_size"],
                overlap=cfg["chunk_overlap"],
            )
            if not pieces:
                skipped += 1
                continue

            vectors = embed(pieces, cfg["embed_model"])
            if len(vectors) != len(pieces):
                raise OllamaError("Embedding тоо chunk-той таарахгүй байна.")

            rows = [(i, pieces[i], vectors[i]) for i in range(len(pieces))]
            total_chunks += upsert_file_chunks(rel, digest, rows)
            indexed += 1
        except OllamaError as exc:
            errors.append(f"{rel}: {exc}")
        except Exception as exc:
            errors.append(f"{rel}: {exc}")

    result = {
        "ok": not errors,
        "indexed": indexed,
        "skipped": skipped,
        "chunks": total_chunks,
        "files": len(files),
        "errors": errors,
    }
    if errors:
        result["message"] = "; ".join(errors[:3])
    else:
        result["message"] = (
            f"✅ {indexed} файл, {total_chunks} chunk индекслэгдлээ "
            f"({skipped} алгассан)."
        )
    return result


def reindex_all() -> dict:
    clear_all()
    return index_knowledge(force=True)
