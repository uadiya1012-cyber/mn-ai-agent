"""
Agent-ын үндсэн loop
Хэрэглэгчийн зорилгыг хүлээн авч,
хэрэгсэл сонгон, гүйцэтгэж, үр дүн буцаана.
"""

import re
import uuid
from collections.abc import Iterator

from agent import memory, models, tools

# ─── System prompt ────────────────────────────────────────

SYSTEM = {
    "mn": """Та Монгол хэлтэй AI туслагч.

Чадварууд:
- Монгол болон Англи хэлээр харилцах
- Instagram, Facebook, мэдээний нийтлэл бичих
- Код бичих, debug хийх, тайлбарлах
- Файл хадгалах, унших, вэб URL унших, мэдлэгийн сангаас хайх — шаардлагатай үед tools дуудна
- knowledge/ мэдлэгийн сангаас ирсэн контекст байвал түүнээс хариулна

Дүрэм:
- Товч, тодорхой хариулна
- Код хэсгийг ``` блокт бичнэ
- Хэрэгтэй бол хэрэглэгчээс нэмэлт мэдээлэл асуун тодруулна
- Монгол техник нэр томьёоны ард (англиар) гэж тэмдэглэнэ""",

    "en": """You are a bilingual AI assistant (Mongolian + English).
Capable of: writing social media posts, coding help, file operations.
When the user needs files, knowledge search, listing outputs, or fetching a web page, use the provided tools (do not fake tool results).
Use knowledge base context when provided; do not invent facts beyond it.
Be concise and practical. Use markdown code blocks for code.""",
}

# ─── Tool автоматаар илрүүлэх ─────────────────────────────

def _detect_tool(text: str) -> tuple[str, dict] | None:
    """
    Хэрэглэгчийн мессежэнд хэрэгслийн түлхүүр үг байгаа эсэх шалгах.
    Олдвол (tool_name, tool_info) буцаана.
    """
    lower = text.lower()
    for name, info in tools.TOOLS.items():
        if any(kw in lower for kw in info["keywords"]):
            return name, info
    return None


def _extract_args(text: str, tool_name: str) -> list:
    """Мессежнээс хэрэгслийн аргументуудыг задлах (энгийн эвристик)"""
    if tool_name == "save_file":
        # "xxx-г хадгал" → агуулга нь өмнөх AI хариунаас ирнэ
        return ["__last_response__"]
    if tool_name == "web_fetch":
        urls = re.findall(r"https?://\S+", text)
        return [urls[0]] if urls else []
    return []


def _augment_with_rag(messages: list[dict], user_input: str, lang: str) -> list[dict]:
    """Индекс байвал мэдлэгийн сангаас контекст нэмнэ."""
    from agent.rag.config import load_rag_config
    from agent.rag.retrieve import build_context_block

    cfg = load_rag_config()
    if not cfg["enabled"] or not cfg["auto_inject"]:
        return messages

    block = build_context_block(user_input, lang=lang)
    if not block:
        return messages

    out = list(messages)
    out[-1] = {
        "role": "user",
        "content": f"{block}\n\n---\n\n{user_input}",
    }
    return out


def _load_last_response(session: str) -> str:
    """Web/CLI session-д save_file-д ашиглах сүүлийн assistant хариу."""
    for msg in reversed(memory.load(session, limit=100)):
        if msg["role"] == "assistant":
            return msg["content"]
    return ""


# ─── Agent class ──────────────────────────────────────────

class Agent:
    def __init__(
        self,
        lang: str = "mn",
        session: str | None = None,
        force_route: str | None = None,
    ):
        self.lang = lang
        self.session = session or str(uuid.uuid4())[:8]
        self.system = SYSTEM.get(lang, SYSTEM["mn"])
        self._last = _load_last_response(self.session)
        self.force_route = force_route if force_route in ("claude", "ollama") else None

    def _resolve_route(
        self, messages: list[dict], call_force: str | None = None
    ) -> str:
        force = call_force or self.force_route
        return models.route_for(messages, force=force)

    def set_force_route(self, mode: str | None) -> str:
        """CLI: /claude, /local, /auto"""
        if mode is None or mode == "auto":
            self.force_route = None
            return "auto"
        if mode in ("claude", "ollama"):
            self.force_route = mode
            return mode
        raise ValueError(f"Unknown route mode: {mode}")

    # ── Нэг эргэлт ──────────────────────────────────────

    def run(self, user_input: str, force: str | None = None) -> str:
        history = memory.load(self.session)
        messages = history + [{"role": "user", "content": user_input}]
        messages = _augment_with_rag(messages, user_input, self.lang)
        route = self._resolve_route(messages, call_force=force)

        # Ollama горимд л түлхүүр үгээр хэрэгсэл (Claude = API tool use)
        if route == "ollama":
            tool_hit = _detect_tool(user_input)
            if tool_hit:
                tool_name, tool_info = tool_hit
                args = _extract_args(user_input, tool_name)

                if tool_name == "save_file":
                    if not self._last:
                        return "❌ Хадгалах агуулга алга — эхлээд ямар нэг зүйл үүсгэнэ үү."
                    result = tool_info["fn"](self._last)
                    memory.save(self.session, "user", user_input)
                    memory.save(self.session, "assistant", result)
                    return result

                if args:
                    result = tool_info["fn"](*args)
                    memory.save(self.session, "user", user_input)
                    memory.save(self.session, "assistant", result)
                    return result

        response = models.ask(messages, system=self.system, force=route)

        memory.save(self.session, "user", user_input)
        memory.save(self.session, "assistant", response)
        self._last = response

        return response

    def run_stream(
        self, user_input: str, force: str | None = None
    ) -> Iterator[dict]:
        """
        SSE-д зориулсан event generator.
        meta → token/status → done | error
        """
        yield {"type": "meta", "session": self.session, "lang": self.lang}

        history = memory.load(self.session)
        messages = history + [{"role": "user", "content": user_input}]
        messages = _augment_with_rag(messages, user_input, self.lang)
        route = self._resolve_route(messages, call_force=force)
        if messages[-1]["content"] != user_input:
            yield {"type": "meta", "rag": True}
        yield {
            "type": "meta",
            "route": route,
            "route_mode": self.force_route or "auto",
            "route_label": models.route_label(route),
        }

        if route == "ollama":
            tool_hit = _detect_tool(user_input)
            if tool_hit:
                tool_name, tool_info = tool_hit
                args = _extract_args(user_input, tool_name)

                if tool_name == "save_file":
                    if not self._last:
                        yield {
                            "type": "error",
                            "message": "❌ Хадгалах агуулга алга — эхлээд ямар нэг зүйл үүсгэнэ үү.",
                        }
                        return
                    result = tool_info["fn"](self._last)
                    memory.save(self.session, "user", user_input)
                    memory.save(self.session, "assistant", result)
                    yield {
                        "type": "done",
                        "content": result,
                        "route": route,
                        "session": self.session,
                    }
                    return

                if args:
                    result = tool_info["fn"](*args)
                    memory.save(self.session, "user", user_input)
                    memory.save(self.session, "assistant", result)
                    yield {
                        "type": "done",
                        "content": result,
                        "route": route,
                        "session": self.session,
                    }
                    return

        stream_fn = (
            models.stream_ollama if route == "ollama" else models.stream_claude
        )
        parts: list[str] = []
        had_error = False

        for event in stream_fn(messages, system=self.system):
            if event["type"] == "token":
                parts.append(event["text"])
            elif event["type"] == "error":
                had_error = True
            yield event

        if had_error:
            return

        response = "".join(parts)
        memory.save(self.session, "user", user_input)
        memory.save(self.session, "assistant", response)
        self._last = response

        yield {
            "type": "done",
            "content": response,
            "route": route,
            "session": self.session,
        }

    # ── Session ──────────────────────────────────────────

    def clear(self):
        memory.clear(self.session)
        self._last = ""
        print("🗑️  Яриын түүх цэвэрлэгдлээ.")

    def switch_lang(self, lang: str):
        if lang in ("mn", "en"):
            self.lang = lang
            self.system = SYSTEM.get(lang, SYSTEM["mn"])
            label = "Монгол" if lang == "mn" else "English"
            print(f"🔄  Хэл: {label}")

    def export(self, fmt: str = "md") -> str:
        return tools.export_session(self.session, fmt)

    def summarize(self) -> str:
        return tools.summarize_session(self.session, lang=self.lang)
