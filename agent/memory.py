"""
Яриын санах ой — SQLite дээр суурилсан
"""

import sqlite3
import datetime
from pathlib import Path


def _db_path() -> Path:
    import tomllib
    cfg = Path(__file__).parent.parent / "config.toml"
    with open(cfg, "rb") as f:
        p = tomllib.load(f)["paths"]["db"]
    full = Path(__file__).parent.parent / p
    full.parent.mkdir(parents=True, exist_ok=True)
    return full


def _conn() -> sqlite3.Connection:
    con = sqlite3.connect(_db_path())
    con.row_factory = sqlite3.Row
    con.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            session   TEXT    NOT NULL,
            role      TEXT    NOT NULL,
            content   TEXT    NOT NULL,
            ts        TEXT    NOT NULL
        )
    """)
    con.commit()
    return con


# ─── Public API ───────────────────────────────────────────

def save(session: str, role: str, content: str):
    """Нэг мессеж хадгалах"""
    with _conn() as con:
        con.execute(
            "INSERT INTO messages (session, role, content, ts) VALUES (?,?,?,?)",
            (session, role, content, datetime.datetime.now().isoformat()),
        )


def load(session: str, limit: int = 20) -> list[dict]:
    """Сүүлийн N мессежийг буцаах (загварт явуулах формат)"""
    with _conn() as con:
        rows = con.execute(
            "SELECT role, content FROM messages WHERE session=? ORDER BY id DESC LIMIT ?",
            (session, limit),
        ).fetchall()
    return [{"role": r["role"], "content": r["content"]} for r in reversed(rows)]


def sessions() -> list[str]:
    """Бүх session нэрсийг буцаах"""
    with _conn() as con:
        rows = con.execute(
            "SELECT DISTINCT session FROM messages ORDER BY MIN(id)"
        ).fetchall()
    return [r["session"] for r in rows]


def clear(session: str):
    """Session-ны бүх мессежийг устгах"""
    with _conn() as con:
        con.execute("DELETE FROM messages WHERE session=?", (session,))
