"""
Загвар удирдлага — Claude API (tool use) болон Ollama хооронд шилжих
"""

import os
from collections.abc import Iterator
from typing import Any, Literal

import anthropic
import requests
import tomllib
from pathlib import Path

from agent import tools as agent_tools

# ─── Config уншлах ────────────────────────────────────────


def load_config() -> dict:
    cfg_path = Path(__file__).parent.parent / "config.toml"
    with open(cfg_path, "rb") as f:
        return tomllib.load(f)


CFG = load_config()

# ─── Claude (Anthropic API) + tool loop ───────────────────

_MAX_TOOL_ROUNDS = 12


def ask_claude(
    messages: list[dict],
    system: str = "",
    max_tokens: int = 4096,
) -> str:
    """
    Claude API — tool use агуулсан эргэлтүүд.
    ANTHROPIC_API_KEY environment variable шаардлагатай.
    """
    key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not key:
        return "❌ ANTHROPIC_API_KEY тохируулаагүй байна. .env файл шалгана уу."

    client = anthropic.Anthropic(api_key=key)
    model = CFG["models"]["claude"]
    tool_defs = agent_tools.anthropic_tool_defs()

    api_messages: list[dict[str, Any]] = [dict(m) for m in messages]

    for _ in range(_MAX_TOOL_ROUNDS):
        kwargs: dict[str, Any] = dict(
            model=model,
            max_tokens=max_tokens,
            messages=api_messages,
            tools=tool_defs,
        )
        if system:
            kwargs["system"] = system

        resp = client.messages.create(**kwargs)

        if resp.stop_reason == "end_turn":
            parts: list[str] = []
            for block in resp.content:
                if block.type == "text":
                    parts.append(block.text)
            return "\n\n".join(parts).strip()

        if resp.stop_reason == "max_tokens":
            parts = [b.text for b in resp.content if b.type == "text"]
            tail = "\n\n".join(parts).strip()
            if tail:
                return tail + "\n\n⚠️ (max_tokens — хариу тасарсан байж магадгүй)"
            return "❌ max_tokens — хариу хоосон."

        if resp.stop_reason != "tool_use":
            parts = [b.text for b in resp.content if b.type == "text"]
            tail = "\n\n".join(parts).strip()
            if tail:
                return tail
            return f"❌ Claude stop_reason={resp.stop_reason!r}"

        assistant_blocks: list[dict[str, Any]] = []
        tool_uses: list[Any] = []
        for block in resp.content:
            if block.type == "text":
                assistant_blocks.append({"type": "text", "text": block.text})
            elif block.type == "tool_use":
                assistant_blocks.append(
                    {
                        "type": "tool_use",
                        "id": block.id,
                        "name": block.name,
                        "input": block.input,
                    }
                )
                tool_uses.append(block)

        api_messages.append({"role": "assistant", "content": assistant_blocks})

        result_blocks: list[dict[str, Any]] = []
        for tu in tool_uses:
            out = agent_tools.execute_tool(tu.name, dict(tu.input))
            result_blocks.append(
                {
                    "type": "tool_result",
                    "tool_use_id": tu.id,
                    "content": out,
                }
            )
        api_messages.append({"role": "user", "content": result_blocks})

    return "❌ Tool эргэлтийн дээд хязгаарт хүрлээ. Дахин оролдоно уу."


def _text_from_message(message) -> str:
    parts: list[str] = []
    for block in message.content:
        if block.type == "text":
            parts.append(block.text)
    return "\n\n".join(parts).strip()


def stream_claude(
    messages: list[dict],
    system: str = "",
    max_tokens: int = 4096,
) -> Iterator[dict[str, str]]:
    """
    Claude API — SSE-д зориулсан event yield.
    {"type": "token"|"status"|"error", ...}
    """
    key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not key:
        yield {
            "type": "error",
            "message": "❌ ANTHROPIC_API_KEY тохируулаагүй байна. .env файл шалгана уу.",
        }
        return

    client = anthropic.Anthropic(api_key=key)
    model = CFG["models"]["claude"]
    tool_defs = agent_tools.anthropic_tool_defs()
    api_messages: list[dict[str, Any]] = [dict(m) for m in messages]

    for _ in range(_MAX_TOOL_ROUNDS):
        kwargs: dict[str, Any] = dict(
            model=model,
            max_tokens=max_tokens,
            messages=api_messages,
            tools=tool_defs,
        )
        if system:
            kwargs["system"] = system

        with client.messages.stream(**kwargs) as stream:
            for text in stream.text_stream:
                yield {"type": "token", "text": text}
            final = stream.get_final_message()

        if final.stop_reason == "end_turn":
            return

        if final.stop_reason == "max_tokens":
            tail = _text_from_message(final)
            if tail:
                yield {
                    "type": "error",
                    "message": tail + "\n\n⚠️ (max_tokens — хариу тасарсан байж магадгүй)",
                }
            else:
                yield {"type": "error", "message": "❌ max_tokens — хариу хоосон."}
            return

        if final.stop_reason != "tool_use":
            tail = _text_from_message(final)
            if tail:
                yield {"type": "error", "message": tail}
            else:
                yield {
                    "type": "error",
                    "message": f"❌ Claude stop_reason={final.stop_reason!r}",
                }
            return

        assistant_blocks: list[dict[str, Any]] = []
        tool_uses: list[Any] = []
        for block in final.content:
            if block.type == "text":
                assistant_blocks.append({"type": "text", "text": block.text})
            elif block.type == "tool_use":
                assistant_blocks.append(
                    {
                        "type": "tool_use",
                        "id": block.id,
                        "name": block.name,
                        "input": block.input,
                    }
                )
                tool_uses.append(block)

        api_messages.append({"role": "assistant", "content": assistant_blocks})

        result_blocks: list[dict[str, Any]] = []
        for tu in tool_uses:
            yield {"type": "status", "message": f"Хэрэгсэл: {tu.name}"}
            out = agent_tools.execute_tool(tu.name, dict(tu.input))
            result_blocks.append(
                {
                    "type": "tool_result",
                    "tool_use_id": tu.id,
                    "content": out,
                }
            )
        api_messages.append({"role": "user", "content": result_blocks})

    yield {
        "type": "error",
        "message": "❌ Tool эргэлтийн дээд хязгаарт хүрлээ. Дахин оролдоно уу.",
    }


# ─── Ollama (local) ───────────────────────────────────────

OLLAMA_URL = "http://localhost:11434"


def ask_ollama(
    messages: list[dict],
    system: str = "",
    model: str | None = None,
) -> str:
    """
    Ollama-д хандах — код, техник, англи текст
    Streaming горимоор хэвлэнэ
    """
    from agent.ollama_client import chat_stream, OllamaError

    mdl = model or CFG["models"]["ollama"]
    if system:
        messages = [{"role": "system", "content": system}] + messages

    try:
        print("\n🤖 ", end="", flush=True)
        def on_token(t):
            print(t, end="", flush=True)
            
        full = chat_stream(
            messages,
            model=mdl,
            on_token=on_token,
            options={"temperature": 0.3, "num_predict": 2000}
        )
        print()
        return full

    except OllamaError as e:
        return f"❌ {e}"


def stream_ollama(
    messages: list[dict],
    system: str = "",
    model: str | None = None,
) -> Iterator[dict[str, str]]:
    """Ollama chat — token event yield."""
    from agent.ollama_client import OllamaError, iter_chat_tokens

    mdl = model or CFG["models"]["ollama"]
    if system:
        messages = [{"role": "system", "content": system}] + messages

    try:
        for token in iter_chat_tokens(
            messages,
            mdl,
            options={"temperature": 0.3, "num_predict": 2000},
        ):
            yield {"type": "token", "text": token}
    except OllamaError as e:
        yield {"type": "error", "message": f"❌ {e}"}


# ─── Auto router ──────────────────────────────────────────

CODE_KEYWORDS = (
    "код",
    "code",
    "функц",
    "function",
    "python",
    "javascript",
    "typescript",
    "sql",
    "debug",
    "error",
    "traceback",
    "алдаа засах",
    "script",
    "алгоритм",
    "api endpoint",
    "regex",
    "git ",
    "docker",
    "compile",
)

CONTENT_KEYWORDS = (
    "пост",
    "post",
    "instagram",
    "facebook",
    "linkedin",
    "tiktok",
    "мэдээ",
    "article",
    "нийтлэл",
    "caption",
    "hashtag",
    "контент",
    "content writer",
    "marketing",
    "slogan",
    "бичиж өг",
    "бичээд өг",
    "copywrite",
    "уншигчид",
)

STRONG_CODE_KEYWORDS = (
    "debug",
    "traceback",
    "syntax error",
    "stack trace",
    "function",
    "sql",
    "```",
    "def ",
    "class ",
    "import ",
)


def _last_user_text(messages: list[dict]) -> str:
    last = next(
        (m["content"] for m in reversed(messages) if m["role"] == "user"),
        "",
    )
    return last if isinstance(last, str) else ""


def route_for(
    messages: list[dict],
    force: str | None = None,
) -> Literal["claude", "ollama"]:
    """
    Загвар сонголт:
    - force: claude | ollama — гараар түгжих
    - код/техник → Ollama
    - пост/мэдээ/контент → Claude
  - үлдсэн → Claude (tool use)
    """
    if force == "claude":
        return "claude"
    if force == "ollama":
        return "ollama"

    lower = _last_user_text(messages).lower()
    if not lower:
        return "claude"

    code_hit = any(kw in lower for kw in CODE_KEYWORDS)
    content_hit = any(kw in lower for kw in CONTENT_KEYWORDS)

    if code_hit and content_hit:
        if any(kw in lower for kw in STRONG_CODE_KEYWORDS):
            return "ollama"
        return "claude"
    if code_hit:
        return "ollama"
    if content_hit:
        return "claude"
    return "claude"


def route_label(route: Literal["claude", "ollama"]) -> str:
    if route == "ollama":
        return "Ollama · код"
    return "Claude · tool use"


def ask(
    messages: list[dict],
    system: str = "",
    force: str | None = None,  # "claude" | "ollama" | None
) -> str:
    """
    force=None үед сүүлчийн хэрэглэгчийн мессежийг шинжлэн
    автоматаар Claude эсвэл Ollama сонгоно.
    """
    if force == "claude":
        print(f"  [{route_label('claude')}]")
        return ask_claude(messages, system)
    if force == "ollama":
        print(f"  [{route_label('ollama')}]")
        return ask_ollama(messages, system)

    route = route_for(messages)
    print(f"  [{route_label(route)}]")
    if route == "ollama":
        return ask_ollama(messages, system)
    return ask_claude(messages, system)
