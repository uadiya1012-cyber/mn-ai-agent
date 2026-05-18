#!/usr/bin/env python3
"""
💻 Код бичих туслагч бот
Supports: Python, JavaScript, SQL, bash болон бусад
Language: Монгол 🇲🇳 / English 🇬🇧
Streaming output — хариуг бодож байхад нь харуулна
"""

import sys
import os
import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from agent.local_config import MODELS, CODE_OUTPUT, DEFAULT_LANG, MAX_HISTORY_MESSAGES
from agent.ollama_client import OllamaError, chat_stream

# ─── System prompts ───────────────────────────────────────────────────────────

SYSTEM_PROMPTS = {
    "mn": """Та туршлагатай програм хангамжийн инженер.
Хэрэглэгчийн асуултад Монгол хэлээр хариулна.
Код хэсгүүдийг markdown ```хэл``` блокт оруулна.
Тайлбарыг товч, тодорхой бич.
Монгол техник нэр томьёог ашиглахдаа хаалтад Англи эквивалентыг нэм: жишээ нь "функц (function)".
Монгол хэлний зөв бичих дүрэм, өгүүлбэрийн найруулгыг баримтал.
Хэт урт өгүүлбэрээс зайлсхийж, энгийн ойлгомжтой өгүүлбэр ашигла.
Latin үсгээр Монгол үг бүү бич.""",

    "en": """You are an experienced software engineer.
Answer the user's questions in clear English.
Place all code in markdown ```language``` blocks.
Keep explanations concise and practical.
When explaining concepts, give real examples.""",
}

# ─── Core streaming call ──────────────────────────────────────────────────────

def stream_ollama(messages: list, model: str = MODELS["code"]) -> str:
    """
    Ollama-д streaming горимоор хандах.
    Хариу гарч байхад нь нэг нэгээр хэвлэнэ.
    """
    try:
        print("\n🤖 ", end="", flush=True)
        answer = chat_stream(
            messages,
            model,
            on_token=lambda token: print(token, end="", flush=True),
            options={
                "temperature": 0.3,   # Код бичихэд бага temperature
                "top_p": 0.9,
                "num_predict": 2000,
            },
        )
        print()
        return answer
    except OllamaError as e:
        msg = f"\n❌ Алдаа: {e}"
        print(msg)
        return msg


# ─── Session management ───────────────────────────────────────────────────────

class CodeBotSession:
    """
    Харилцааны түүхтэй код туслагч.
    Олон асуулт — бот контекстыг санана.
    """

    def __init__(self, lang: str = DEFAULT_LANG):
        self.lang = lang if lang in ("mn", "en") else "mn"
        self.history: list[dict] = []
        self.started_at = datetime.datetime.now()
        self._init_system()

    def _init_system(self):
        """System prompt тохируулах"""
        self.system_msg = {
            "role": "system",
            "content": SYSTEM_PROMPTS[self.lang],
        }

    def switch_language(self, lang: str):
        """Яриа дундаас хэл солих"""
        if lang in ("mn", "en"):
            self.lang = lang
            self._init_system()
            label = "Монгол" if lang == "mn" else "English"
            print(f"\n🔄 Хэл солигдлоо: {label}")

    def ask(self, question: str) -> str:
        """Асуулт тавих — хариу streaming-ээр ирнэ"""
        self.history.append({"role": "user", "content": question})

        messages = [self.system_msg] + self.history[-MAX_HISTORY_MESSAGES:]

        answer = stream_ollama(messages)

        self.history.append({"role": "assistant", "content": answer})
        return answer

    def save_session(self) -> str:
        """Бүх яриаг файлд хадгалах"""
        ts = self.started_at.strftime("%Y%m%d_%H%M%S")
        filename = f"code_session_{self.lang}_{ts}.md"
        filepath = os.path.join(str(CODE_OUTPUT), filename)

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(f"# Код туслагч — {self.started_at.strftime('%Y-%m-%d %H:%M')}\n")
            f.write(f"Language: {self.lang}\n\n")
            f.write("---\n\n")
            for msg in self.history:
                role = "👤 Асуулт" if msg["role"] == "user" else "🤖 Хариу"
                f.write(f"## {role}\n\n{msg['content']}\n\n---\n\n")

        return filepath

    def clear(self):
        """Яриын түүхийг цэвэрлэх (шинэ сэдэв)"""
        self.history.clear()
        print("🗑️  Түүх цэвэрлэгдлээ — шинэ яриа эхэллээ.")

    def show_history(self):
        """Одоогийн яриыг харуулах"""
        if not self.history:
            print("  (Яриын түүх хоосон)")
            return
        print(f"\n{'─'*40}")
        for i, msg in enumerate(self.history):
            label = "👤" if msg["role"] == "user" else "🤖"
            preview = msg["content"][:80].replace("\n", " ")
            print(f"  {label} [{i+1}] {preview}...")
        print(f"{'─'*40}")


# ─── Interactive CLI ──────────────────────────────────────────────────────────

HELP = {
    "mn": """\
📋 Командууд:
  /mn       — Монгол хэлрүү солих
  /en       — Англи хэлрүү солих
  /clear    — Яриын түүх цэвэрлэх
  /history  — Яриын түүх харах
  /save     — Яриыг файлд хадгалах
  /help     — Энэ цэсийг харуулах
  /exit     — Гарах
""",
    "en": """\
📋 Commands:
  /mn       — Switch to Mongolian
  /en       — Switch to English
  /clear    — Clear conversation history
  /history  — Show conversation history
  /save     — Save session to file
  /help     — Show this menu
  /exit     — Exit
""",
}


def interactive():
    """Харилцааны горим"""
    ui_lang = input("Language / Хэл (mn/en) [mn]: ").strip().lower()
    if ui_lang not in ("mn", "en"):
        ui_lang = "mn"

    session = CodeBotSession(lang=ui_lang)

    welcome = {
        "mn": "💻 Код туслагч бот бэлэн\n   Асуулт бичнэ үү. /help гэж бичвэл командуудыг харна.",
        "en": "💻 Code Assistant Bot ready\n   Ask anything. Type /help for commands.",
    }
    model_info = f"   Model: {MODELS['code']}"

    print(f"\n{'═'*50}")
    print(f"  {welcome[ui_lang]}")
    print(model_info)
    print(f"{'═'*50}\n")

    while True:
        try:
            prompt = "❓ " if session.lang == "mn" else "❓ "
            user_input = input(f"\n{prompt}").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n👋 Баярлалаа!")
            break

        if not user_input:
            continue

        # Commands
        if user_input.startswith("/"):
            cmd = user_input.lower()
            if cmd == "/exit":
                save = input("Яриыг хадгалах уу? (y/n): ").strip().lower()
                if save == "y":
                    path = session.save_session()
                    print(f"💾 Хадгалагдлаа: {path}")
                print("👋 Баярлалаа!")
                break
            elif cmd == "/mn":
                session.switch_language("mn")
            elif cmd == "/en":
                session.switch_language("en")
            elif cmd == "/clear":
                session.clear()
            elif cmd == "/history":
                session.show_history()
            elif cmd == "/save":
                path = session.save_session()
                print(f"💾 Хадгалагдлаа: {path}")
            elif cmd == "/help":
                print(HELP[session.lang])
            else:
                print(f"  Тодорхойгүй команд: {user_input}")
            continue

        session.ask(user_input)


# ─── Quick single question (non-interactive) ──────────────────────────────────

def quick(question: str, lang: str = "mn") -> str:
    """
    Нэг асуулт шуурхай хариулуулах:
    python main.py code "list comprehension гэж юу вэ" --lang mn
    """
    session = CodeBotSession(lang=lang)
    return session.ask(question)


if __name__ == "__main__":
    if len(sys.argv) >= 2 and not sys.argv[1].startswith("/"):
        _question = sys.argv[1]
        _lang     = sys.argv[2] if len(sys.argv) > 2 else "mn"
        quick(_question, _lang)
    else:
        interactive()
