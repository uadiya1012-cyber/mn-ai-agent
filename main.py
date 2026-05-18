#!/usr/bin/env python3
"""
🤖 mn-ai-agent — Үндсэн CLI
"""

import os
import readline  # noqa: F401 — CLI мөрний түүх (↑/↓)
import sys
import argparse
from dotenv import load_dotenv

load_dotenv()   # .env файлаас API key уншина

from agent.core import Agent
from agent.local_config import MODELS, NEWS_TONES, POST_TYPES
from agent.memory import sessions
from agent.tools import list_outputs

BANNER = """
╔══════════════════════════════════════╗
║      🤖  mn-ai-agent  v0.3          ║
║   Монгол + English · Local + API    ║
╚══════════════════════════════════════╝"""

HELP = """
📋 Командууд:
  /mn        — Монгол хэл
  /en        — English
  /clear     — Яриын түүх цэвэрлэх
  /new       — Шинэ session эхлэх
  /sessions  — Бүх session жагсаах
  /switch ID — Өмнөх session руу шилжих
  /files     — Хадгалсан output файлууд
  /export [md|json] — Яриаг файлд экспортлох
  /summary   — Яриаг 3 цэгээр товчлох (Claude)
  /claude    — Загварыг Claude-д түгжих
  /local     — Загварыг Ollama-д түгжих (код горим)
  /auto      — Автомат router (default)
  /route     — Одоогийн router горим харах
  /help      — Энэ цэс
  /exit      — Гарах

💡 Жишээ асуултууд:
  → Instagram пост бичиж өг: AI хиймэл оюун ухааны тухай
  → Python-д list comprehension гэж юу вэ?
  → Сүүлийн хариуг файлд хадгал
"""


def _route_status(agent: Agent) -> str:
    from agent.models import route_label

    if agent.force_route:
        return route_label(agent.force_route) + " (түгжсэн)"
    return "автомат (контент→Claude, код→Ollama)"


def check_ollama() -> bool:
    """Ollama ажиллаж байгаа эсэх болон шаардлагатай model-уудыг шалгах."""
    from agent.ollama_client import OllamaError, list_models, model_is_installed

    try:
        installed = list_models()
        print("✅ Ollama ажиллаж байна\n")
        print("📦 Суулгагдсан загварууд:")
        if installed:
            for model in installed:
                marker = "  ✓ " if any(
                    model_is_installed(req, [model]) for req in MODELS.values()
                ) else "  · "
                print(f"{marker}{model}")
        else:
            print("  (загвар алга — доорх командаар татаж авна уу)")

        from agent.rag.config import load_rag_config

        rag_cfg = load_rag_config()
        all_models = dict(MODELS)
        if rag_cfg.get("enabled"):
            all_models["rag_embed"] = rag_cfg["embed_model"]

        print("\n💡 Шаардлагатай загварууд:")
        for purpose, model in all_models.items():
            status = "✓" if model_is_installed(model, installed) else "✗"
            print(f"  [{status}] {model:30s} ← {purpose}")

        missing = [
            model for model in all_models.values()
            if not model_is_installed(model, installed)
        ]
        if missing:
            print("\n📥 Татаж авах командууд:")
            for model in missing:
                print(f"  ollama pull {model}")
        return True
    except OllamaError as exc:
        print("❌ Ollama ажиллахгүй байна!")
        print(f"Шалтгаан: {exc}")
        print("\nЭхлүүлэх:")
        print("  ollama serve")
        return False


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="mn-ai-agent — Монгол/Англи local + API туслагч",
    )
    subparsers = parser.add_subparsers(dest="command")

    news = subparsers.add_parser("news", help="Local Ollama мэдээ/пост үүсгэгч")
    news.add_argument("--type", choices=POST_TYPES, help="Контентын төрөл")
    news.add_argument("--topic", help="Сэдэв")
    news.add_argument("--lang", choices=("mn", "en"), default="mn", help="Гаралтын хэл")
    news.add_argument("--details", default="", help="Нэмэлт мэдээлэл")
    news.add_argument("--tone", choices=NEWS_TONES, default="balanced", help="Бичвэрийн өнгө")

    code = subparsers.add_parser("code", help="Local Ollama код туслагч")
    code.add_argument("question", nargs="?", help="Нэг асуулт шууд асуух")
    code.add_argument("--lang", choices=("mn", "en"), default="mn", help="Хариулах хэл")

    subparsers.add_parser("check", help="Ollama холболт болон model-ууд шалгах")
    subparsers.add_parser("web", help="FastAPI web UI ажиллуулах")

    rag = subparsers.add_parser("rag", help="RAG мэдлэгийн сан (knowledge/)")
    rag_sub = rag.add_subparsers(dest="rag_action", required=True)
    rag_sub.add_parser("status", help="Индекс статус")
    rag_index = rag_sub.add_parser("index", help="Файлуудыг индекслэх")
    rag_index.add_argument(
        "--force",
        action="store_true",
        help="Бүх индексийг устгаад дахин үүсгэх",
    )
    rag_search = rag_sub.add_parser("search", help="Semantic хайлт")
    rag_search.add_argument("query", help="Хайх асуулт")
    rag_search.add_argument("--top-k", type=int, default=4, dest="top_k")

    return parser


def run_rag(args) -> None:
    from agent.rag import index_knowledge, search, status
    from agent.rag.ingest import reindex_all
    from agent.rag.retrieve import format_hits

    if args.rag_action == "status":
        info = status()
        print("\n📚 RAG статус\n")
        for key, value in info.items():
            print(f"  {key}: {value}")
        print()
        return

    if args.rag_action == "index":
        print("\n⏳ Индекслэж байна...")
        result = reindex_all() if args.force else index_knowledge()
        print(result.get("message", result))
        return

    if args.rag_action == "search":
        hits = search(args.query, top_k=args.top_k)
        print(format_hits(hits, lang="mn"))
        print()


def check_env():
    """API key шалгах"""
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("⚠️  ANTHROPIC_API_KEY тохируулаагүй байна.")
        print("   .env файлд дараахийг нэм:\n")
        print("   ANTHROPIC_API_KEY=sk-ant-xxxxxx\n")
        ans = input("   Үргэлжлүүлэх үү? (Ollama-гаар л ажиллана) [y/n]: ").strip()
        if ans.lower() == "n":
            sys.exit(0)


def interactive_agent():
    print(BANNER)
    check_env()

    lang = input("\n  Хэл / Language (mn/en) [mn]: ").strip().lower()
    if lang not in ("mn", "en"):
        lang = "mn"

    agent = Agent(lang=lang)

    print(f"\n  Session: {agent.session}")
    print(f"  Router: {_route_status(agent)}")
    print("  /help гэж бичвэл командуудыг харна.\n")

    while True:
        try:
            user = input("❓ ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n👋 Баярлалаа!")
            break

        if not user:
            continue

        # ── Командууд ──
        if user.startswith("/"):
            parts = user.split(None, 1)
            cmd = parts[0].lower()
            arg = parts[1].strip() if len(parts) > 1 else ""

            if cmd == "/exit":
                print("👋 Баярлалаа!")
                break
            elif cmd == "/mn":
                agent.switch_lang("mn")
            elif cmd == "/en":
                agent.switch_lang("en")
            elif cmd == "/clear":
                agent.clear()
            elif cmd == "/new":
                import uuid
                agent = Agent(lang=agent.lang, session=str(uuid.uuid4())[:8])
                print(f"✨ Шинэ session: {agent.session}")
            elif cmd == "/sessions":
                for s in sessions():
                    marker = " ←" if s == agent.session else ""
                    print(f"  · {s}{marker}")
            elif cmd == "/switch":
                if not arg:
                    print("  Ашиглалт: /switch <session_id>  (/sessions-аас ID харна)")
                elif arg not in sessions():
                    print(f"  Session олдсонгүй: {arg!r} — /sessions жагсаалтыг шалгана уу.")
                else:
                    agent = Agent(lang=agent.lang, session=arg)
                    print(f"  🔀 Session: {agent.session}")
            elif cmd == "/files":
                print(list_outputs())
            elif cmd == "/export":
                fmt = (arg or "md").lower()
                print(agent.export(fmt))
            elif cmd == "/summary":
                print("\n📋 Товчлол:\n")
                print(agent.summarize())
                print()
            elif cmd in ("/claude", "/local", "/ollama", "/auto", "/route"):
                if cmd == "/route":
                    print(f"  Router: {_route_status(agent)}")
                elif cmd == "/auto":
                    agent.set_force_route("auto")
                    print(f"  🔀 Router: {_route_status(agent)}")
                elif cmd == "/claude":
                    agent.set_force_route("claude")
                    print(f"  🔀 Router: {_route_status(agent)}")
                else:
                    agent.set_force_route("ollama")
                    print(f"  🔀 Router: {_route_status(agent)}")
            elif cmd == "/help":
                print(HELP)
            else:
                print(f"  Тодорхойгүй команд. /help харна уу.")
            continue

        # ── Agent ──
        response = agent.run(user)
        if not response.startswith("  ["):   # route label биш бол хэвлэнэ
            print(f"\n{response}\n")


def main():
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "news":
        if args.type and args.topic:
            from agent.local_news import quick
            quick(args.type, args.topic, args.lang, args.details, args.tone)
            return
        if args.type or args.topic or args.details:
            parser.error("news shortcut-д --type болон --topic хоёулаа хэрэгтэй")
        from agent.local_news import interactive
        interactive()
        return

    if args.command == "code":
        if args.question:
            from agent.local_code import quick
            quick(args.question, args.lang)
            return
        from agent.local_code import interactive
        interactive()
        return

    if args.command == "check":
        check_ollama()
        return

    if args.command == "web":
        import uvicorn
        uvicorn.run("web_app.app:app", host="127.0.0.1", port=8000, reload=True)
        return

    if args.command == "rag":
        run_rag(args)
        return

    interactive_agent()


if __name__ == "__main__":
    main()
