"""
Local Ollama feature configuration for mn-ai-agent.
"""

import os
import tomllib
from pathlib import Path


BASE_DIR = Path(__file__).parent.parent


def _load_config() -> dict:
    with open(BASE_DIR / "config.toml", "rb") as f:
        return tomllib.load(f)


CFG = _load_config()

MODELS = {
    "news": CFG["models"].get("news", "qwen2.5:7b"),
    "code": CFG["models"].get("ollama", "deepseek-coder:6.7b"),
}

LANGUAGES = {
    "mn": "Mongolian",
    "en": "English",
}

DEFAULT_LANG = CFG.get("language", {}).get("default", "mn")
NEWS_TONES = ("balanced", "friendly", "formal", "marketing", "short")
POST_TYPES = ("instagram", "facebook", "news", "linkedin", "tiktok")
MAX_HISTORY_MESSAGES = 20

NEWS_TEMPERATURE = 0.45
ENABLE_MONGOLIAN_POLISH = True
MONGOLIAN_FALLBACK_ON_LOW_QUALITY = True

OLLAMA_HOST = CFG.get("ollama", {}).get("host", "http://localhost:11434")

OUTPUT_DIR = BASE_DIR / CFG["paths"].get("outputs", "data/outputs")
NEWS_OUTPUT = OUTPUT_DIR / "news_posts"
CODE_OUTPUT = OUTPUT_DIR / "code_sessions"

os.makedirs(NEWS_OUTPUT, exist_ok=True)
os.makedirs(CODE_OUTPUT, exist_ok=True)
