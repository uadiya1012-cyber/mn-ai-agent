"""SQLite дээр embedding хадгалах, cosine search."""

import json
import math
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone

from agent.rag.config import index_db_path


@dataclass
class ChunkHit:
    source: str
    content: str
    score: float
    chunk_index: int


def _conn() -> sqlite3.Connection:
    con = sqlite3.connect(index_db_path())
    con.row_factory = sqlite3.Row
    con.execute("""
        CREATE TABLE IF NOT EXISTS chunks (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            source      TEXT NOT NULL,
            chunk_index INTEGER NOT NULL,
            content     TEXT NOT NULL,
            embedding   TEXT NOT NULL,
            file_hash   TEXT NOT NULL,
            updated_at  TEXT NOT NULL,
            UNIQUE(source, chunk_index)
        )
    """)
    con.execute("""
        CREATE TABLE IF NOT EXISTS file_meta (
            source     TEXT PRIMARY KEY,
            file_hash  TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)
    con.commit()
    return con


def clear_all() -> None:
    with _conn() as con:
        con.execute("DELETE FROM chunks")
        con.execute("DELETE FROM file_meta")


def clear_source(source: str) -> None:
    with _conn() as con:
        con.execute("DELETE FROM chunks WHERE source = ?", (source,))
        con.execute("DELETE FROM file_meta WHERE source = ?", (source,))


def get_file_hash(source: str) -> str | None:
    with _conn() as con:
        row = con.execute(
            "SELECT file_hash FROM file_meta WHERE source = ?", (source,)
        ).fetchone()
    return row["file_hash"] if row else None


def upsert_file_chunks(
    source: str,
    file_hash: str,
    chunks: list[tuple[int, str, list[float]]],
) -> int:
    """(chunk_index, content, embedding) жагсаалтыг хадгална."""
    now = datetime.now(timezone.utc).isoformat()
    with _conn() as con:
        con.execute("DELETE FROM chunks WHERE source = ?", (source,))
        for idx, content, vector in chunks:
            con.execute(
                """
                INSERT INTO chunks
                    (source, chunk_index, content, embedding, file_hash, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (source, idx, content, json.dumps(vector), file_hash, now),
            )
        con.execute(
            """
            INSERT INTO file_meta (source, file_hash, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(source) DO UPDATE SET
                file_hash = excluded.file_hash,
                updated_at = excluded.updated_at
            """,
            (source, file_hash, now),
        )
    return len(chunks)


def chunk_count() -> int:
    with _conn() as con:
        row = con.execute("SELECT COUNT(*) AS c FROM chunks").fetchone()
    return int(row["c"])


def list_sources() -> list[str]:
    with _conn() as con:
        rows = con.execute(
            "SELECT DISTINCT source FROM chunks ORDER BY source"
        ).fetchall()
    return [r["source"] for r in rows]


def _cosine(a: list[float], b: list[float]) -> float:
    if len(a) != len(b) or not a:
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def search_vectors(
    query_vector: list[float],
    top_k: int = 4,
    min_score: float = 0.0,
) -> list[ChunkHit]:
    hits: list[ChunkHit] = []
    with _conn() as con:
        rows = con.execute(
            "SELECT source, chunk_index, content, embedding FROM chunks"
        ).fetchall()

    for row in rows:
        vector = json.loads(row["embedding"])
        score = _cosine(query_vector, vector)
        if score >= min_score:
            hits.append(
                ChunkHit(
                    source=row["source"],
                    content=row["content"],
                    score=score,
                    chunk_index=row["chunk_index"],
                )
            )

    hits.sort(key=lambda h: h.score, reverse=True)
    return hits[:top_k]
