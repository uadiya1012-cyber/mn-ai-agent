"""
Agent-ын хэрэгслүүд (Tools)
Шинэ хэрэгсэл нэмэхэд энд функц бичиж TOOLS dict-д бүртгэнэ.
"""

import datetime
import tomllib
from pathlib import Path


def _out_dir() -> Path:
    cfg = Path(__file__).parent.parent / "config.toml"
    with open(cfg, "rb") as f:
        p = tomllib.load(f)["paths"]["outputs"]
    full = Path(__file__).parent.parent / p
    full.mkdir(parents=True, exist_ok=True)
    return full


# ─── Tool функцүүд ────────────────────────────────────────

def save_file(content: str, filename: str | None = None) -> str:
    """Текстийг файлд хадгалах"""
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    fname = filename or f"output_{ts}.txt"
    path = _out_dir() / fname
    path.write_text(content, encoding="utf-8")
    return f"✅ Хадгалагдлаа: {path}"


def read_file(filepath: str) -> str:
    """Зөвхөн outputs хавтас доторх файлыг нэрээр нь уншина (бусад замыг зөвшөөрөхгүй)."""
    root = _out_dir().resolve()
    name = Path(filepath).expanduser().name
    if not name or name in (".", ".."):
        return "❌ Буруу файлын нэр."
    path = (root / name).resolve()
    if not path.is_relative_to(root) or not path.is_file():
        return f"❌ Файл олдсонгүй (зөвхөн /files жагсаалтад байгаа нэр): {filepath}"
    return path.read_text(encoding="utf-8")


def list_outputs() -> str:
    """Outputs хавтасны файлуудыг жагсаах"""
    files = sorted(_out_dir().glob("*"))
    if not files:
        return "  (outputs хоосон байна)"
    return "\n".join(f"  · {f.name}" for f in files)


def web_fetch(url: str) -> str:
    """Вэб хуудасны текст агуулгыг татах"""
    try:
        import urllib.request
        req = urllib.request.Request(
            url, headers={"User-Agent": "Mozilla/5.0"}
        )
        with urllib.request.urlopen(req, timeout=10) as r:
            raw = r.read().decode("utf-8", errors="ignore")
        # HTML таг хасах
        import re
        text = re.sub(r"<[^>]+>", " ", raw)
        text = re.sub(r"\s+", " ", text).strip()
        return text[:3000]
    except Exception as e:
        return f"❌ Вэб татах алдаа: {e}"


def search_knowledge(query: str, top_k: int = 4) -> str:
    """RAG мэдлэгийн сангаас semantic хайлт."""
    from agent.rag import is_enabled, search
    from agent.rag.retrieve import format_hits

    if not is_enabled():
        return "❌ RAG идэвхгүй байна (config.toml [rag] enabled)."
    if not query.strip():
        return "❌ Хайлтын асуулт хоосон байна."

    hits = search(query.strip(), top_k=top_k)
    return format_hits(hits, lang="mn")


def make_post(topic: str, platform: str = "instagram", lang: str = "mn") -> str:
    """
    Нийгмийн сүлжээний пост үүсгэх prompt буцаах.
    Энэ нь agent-д system context болж ордог.
    """
    templates = {
        "mn": f"""Та {platform} пост бичих мэргэжилтэн.
Сэдэв: {topic}
Монгол хэлээр бич. Emoji ашигла. Hashtag нэм.""",
        "en": f"""You are a {platform} content specialist.
Topic: {topic}
Write in English. Use emojis. Add hashtags.""",
    }
    return templates.get(lang, templates["mn"])


# ─── Claude / Anthropic tool definitions ─────────────────

def anthropic_tool_defs() -> list[dict]:
    """Claude Messages API-ийн tools= дамжуулах JSON schema."""
    return [
        {
            "name": "save_file",
            "description": (
                "Текстийг төслийн outputs хавтасад .txt файл болгон хадгална. "
                "Хадгалах бүтэн агуулгыг content-д оруулна."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "content": {
                        "type": "string",
                        "description": "Файлд бичих бүтэн текст",
                    },
                    "filename": {
                        "type": "string",
                        "description": "Сонголттой файлын нэр (жишээ нь notes.txt)",
                    },
                },
                "required": ["content"],
            },
        },
        {
            "name": "read_file",
            "description": (
                "Зөвхөн outputs хавтас доторх файлыг уншина. "
                "Файлын нэр эсвэл зөвхөн basename (жишээ output_20250101_120000.txt)."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "filepath": {
                        "type": "string",
                        "description": "Унших файлын нэр (outputs доторх)",
                    },
                },
                "required": ["filepath"],
            },
        },
        {
            "name": "list_outputs",
            "description": "Хадгалсан бүх output файлуудын жагсаалт.",
            "input_schema": {"type": "object", "properties": {}},
        },
        {
            "name": "web_fetch",
            "description": "Өгөгдсөн URL-аас вэб хуудсын текст агуулгыг татаж, товчлох.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "https эхэлсэн бүрэн URL",
                    },
                },
                "required": ["url"],
            },
        },
        {
            "name": "search_knowledge",
            "description": (
                "Локал мэдлэгийн сан (knowledge/ хавтас) дотроос semantic хайлт хийнэ. "
                "Компанийн бүтээгдэхүүн, баримт бичиг, дотоод мэдээллийн асуултад ашиглана."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Хайх асуулт эсвэл түлхүүр үг",
                    },
                    "top_k": {
                        "type": "integer",
                        "description": "Хэдэн хэсэг буцаах (default 4)",
                    },
                },
                "required": ["query"],
            },
        },
    ]


def execute_tool(name: str, inp: dict) -> str:
    """Claude-ийн tool_use input-оор хэрэгсэл ажиллуулах."""
    spec = TOOLS.get(name)
    if not spec:
        return f"❌ Тодорхойгүй хэрэгсэл: {name}"
    fn = spec["fn"]
    try:
        if name == "list_outputs":
            return fn()
        if name == "save_file":
            content = inp.get("content")
            if content is None:
                return "❌ save_file: content хоосон байна."
            return fn(content, inp.get("filename"))
        if name == "read_file":
            path = inp.get("filepath")
            if not path:
                return "❌ read_file: filepath заавал."
            return fn(path)
        if name == "web_fetch":
            url = inp.get("url")
            if not url:
                return "❌ web_fetch: url заавал."
            return fn(url)
        if name == "search_knowledge":
            query = inp.get("query")
            if not query:
                return "❌ search_knowledge: query заавал."
            top_k = inp.get("top_k") or 4
            return fn(query, top_k=int(top_k))
    except Exception as e:
        return f"❌ Хэрэгсэл алдаа ({name}): {e}"
    return f"❌ Хэрэгсэл: {name}"

def export_session(session: str, fmt: str = "md") -> str:
    from . import memory

    fmt = (fmt or "md").lower().strip()
    if fmt not in ("md", "json"):
        return "❌ Формат: md эсвэл json л зөвшөөрнө."

    msgs = memory.load(session, limit=10000)
    if not msgs:
        return "❌ Session хоосон эсвэл олдсонгүй."

    if fmt == "json":
        import json

        path = _out_dir() / f"session_{session}.json"
        path.write_text(
            json.dumps(msgs, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        return f"✅ Exported: {path}"

    parts = []
    for m in msgs:
        role = "User" if m["role"] == "user" else "Assistant"
        parts.append(f"### {role}\n\n{m['content']}\n")
    path = _out_dir() / f"session_{session}.md"
    path.write_text("\n---\n".join(parts), encoding="utf-8")
    return f"✅ Exported: {path}"


def summarize_session(session: str, lang: str = "mn") -> str:
    from . import memory, models

    msgs = memory.load(session, limit=200)
    if not msgs:
        return "❌ Session хоосон байна."

    transcript = "\n".join(f"{m['role']}: {m['content']}" for m in msgs)
    if lang == "mn":
        prompt = (
            "Дараах яриаг 3 товч цэгээр монголоор товчлоно уу:\n\n" + transcript
        )
        system = "Товч, ойлгомжтой монгол хэлээр хариул."
    else:
        prompt = (
            "Summarize this conversation in 3 short bullets:\n\n" + transcript
        )
        system = "Summarize briefly in English."

    return models.ask(
        [{"role": "user", "content": prompt}],
        system=system,
        force="claude",
    )


# ─── Tool бүртгэл ─────────────────────────────────────────
# Agent энэ dict-ээс хэрэгсэл хайна (Ollama түлхүүр үгийн зам)

TOOLS: dict[str, dict] = {
    "save_file": {
        "fn": save_file,
        "desc": "Текстийг файлд хадгалах",
        "keywords": ["хадгал", "save", "файлд бич"],
    },
    "read_file": {
        "fn": read_file,
        "desc": "Файл унших",
        "keywords": ["уншиж өг", "read", "файл харуул"],
    },
    "list_outputs": {
        "fn": list_outputs,
        "desc": "Хадгалсан файлуудыг жагсаах",
        "keywords": ["файлууд", "outputs", "жагсаа"],
    },
    "web_fetch": {
        "fn": web_fetch,
        "desc": "Вэб хуудас унших",
        "keywords": ["вэб", "url", "сайт", "fetch"],
    },
    "search_knowledge": {
        "fn": search_knowledge,
        "desc": "Мэдлэгийн сангаас хайх",
        "keywords": [
            "мэдлэгийн сан",
            "баримт",
            "knowledge",
            "компанийн",
            "бүтээгдэхүүн",
            "rag",
        ],
    },
}
