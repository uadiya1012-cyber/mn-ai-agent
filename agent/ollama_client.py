"""
Small shared Ollama client helpers for mn-ai-agent.
"""

import json
from collections.abc import Callable, Iterable

import requests

from agent.local_config import OLLAMA_HOST


class OllamaError(RuntimeError):
    """Raised when Ollama cannot complete a request."""


def list_models(timeout: int = 5) -> list[str]:
    """Return installed Ollama model names."""
    try:
        response = requests.get(f"{OLLAMA_HOST}/api/tags", timeout=timeout)
        response.raise_for_status()
        tags = response.json()
        return [model["name"] for model in tags.get("models", [])]
    except requests.exceptions.ConnectionError as exc:
        raise OllamaError("Ollama ажиллахгүй байна. `ollama serve` командыг ажиллуулна уу.") from exc
    except Exception as exc:
        raise OllamaError(str(exc)) from exc


def model_is_installed(model: str, installed: Iterable[str]) -> bool:
    """Match both exact tags and same base model names."""
    base = model.split(":")[0]
    return any(name == model or name.startswith(base) for name in installed)


def generate(
    prompt: str,
    model: str,
    *,
    options: dict | None = None,
    timeout: int = 120,
) -> str:
    """Call Ollama /api/generate and return the final response text."""
    try:
        response = requests.post(
            f"{OLLAMA_HOST}/api/generate",
            json={
                "model": model,
                "prompt": prompt,
                "stream": False,
                "options": options or {},
            },
            timeout=timeout,
        )
        response.raise_for_status()
        return response.json()["response"].strip()
    except requests.exceptions.ConnectionError as exc:
        raise OllamaError("Ollama ажиллахгүй байна. `ollama serve` командыг ажиллуулна уу.") from exc
    except Exception as exc:
        raise OllamaError(str(exc)) from exc


def iter_chat_tokens(
    messages: list[dict],
    model: str,
    *,
    options: dict | None = None,
    timeout: int = 180,
):
    """Ollama /api/chat — token бүрээр yield хийнэ."""
    try:
        response = requests.post(
            f"{OLLAMA_HOST}/api/chat",
            json={
                "model": model,
                "messages": messages,
                "stream": True,
                "options": options or {},
            },
            stream=True,
            timeout=timeout,
        )
        response.raise_for_status()

        for line in response.iter_lines():
            if not line:
                continue
            try:
                chunk = json.loads(line)
            except json.JSONDecodeError:
                continue

            token = chunk.get("message", {}).get("content", "")
            if token:
                yield token
            if chunk.get("done"):
                break
    except requests.exceptions.ConnectionError as exc:
        raise OllamaError("Ollama холбогдохгүй байна. `ollama serve` ажиллуулна уу.") from exc
    except Exception as exc:
        raise OllamaError(str(exc)) from exc


def embed(
    text: str | list[str],
    model: str,
    *,
    timeout: int = 120,
) -> list[list[float]]:
    """Ollama /api/embed — нэг эсвэл олон текстийн embedding."""
    payload = text if isinstance(text, list) else [text]
    if not payload:
        return []
    try:
        response = requests.post(
            f"{OLLAMA_HOST}/api/embed",
            json={"model": model, "input": payload},
            timeout=timeout,
        )
        response.raise_for_status()
        data = response.json()
        vectors = data.get("embeddings")
        if not vectors:
            raise OllamaError("Embedding хоосон буцлаа.")
        return vectors
    except requests.exceptions.ConnectionError as exc:
        raise OllamaError("Ollama холбогдохгүй байна. `ollama serve` ажиллуулна уу.") from exc
    except OllamaError:
        raise
    except Exception as exc:
        raise OllamaError(str(exc)) from exc


def chat_stream(
    messages: list[dict],
    model: str,
    *,
    on_token: Callable[[str], None] | None = None,
    options: dict | None = None,
    timeout: int = 180,
) -> str:
    """Call Ollama /api/chat with streaming and return the full response."""
    full_response: list[str] = []
    for token in iter_chat_tokens(
        messages, model, options=options, timeout=timeout
    ):
        if on_token:
            on_token(token)
        full_response.append(token)
    return "".join(full_response)
