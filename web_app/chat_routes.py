"""Agent чат API — SSE streaming, session, түүх."""

import json
import os
from collections.abc import Iterator

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from agent import memory, tools
from agent.core import Agent

router = APIRouter()


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=8000)
    lang: str = Field(default="mn", pattern="^(mn|en)$")
    session_id: str | None = Field(default=None, max_length=32)
    force: str | None = Field(default=None, pattern="^(claude|ollama)$")


class ClearRequest(BaseModel):
    session_id: str = Field(min_length=1, max_length=32)


class ExportRequest(BaseModel):
    session_id: str = Field(min_length=1, max_length=32)
    fmt: str = Field(default="md", pattern="^(md|json)$")


class SummaryRequest(BaseModel):
    session_id: str = Field(min_length=1, max_length=32)
    lang: str = Field(default="mn", pattern="^(mn|en)$")


def _format_sse(event: dict) -> str:
    typ = event.get("type", "message")
    return f"event: {typ}\ndata: {json.dumps(event, ensure_ascii=False)}\n\n"


@router.get("/status")
def chat_status() -> dict:
    return {"claude_configured": bool(os.environ.get("ANTHROPIC_API_KEY"))}


@router.get("/sessions")
def list_sessions() -> dict:
    return {"sessions": memory.sessions()}


@router.get("/history")
def chat_history(
    session_id: str = Query(..., min_length=1, max_length=32),
    limit: int = Query(default=50, ge=1, le=200),
) -> dict:
    return {
        "session_id": session_id,
        "messages": memory.load(session_id, limit=limit),
    }


@router.post("/clear")
def clear_session(payload: ClearRequest) -> dict:
    memory.clear(payload.session_id)
    return {"ok": True, "session_id": payload.session_id}


@router.post("/export")
def export_session(payload: ExportRequest) -> dict:
    result = tools.export_session(payload.session_id, payload.fmt)
    if result.startswith("❌"):
        raise HTTPException(status_code=400, detail=result)
    return {"ok": True, "message": result}


@router.post("/summary")
def summarize_session(payload: SummaryRequest) -> dict:
    summary = tools.summarize_session(payload.session_id, lang=payload.lang)
    if summary.startswith("❌"):
        raise HTTPException(status_code=400, detail=summary)
    return {"ok": True, "summary": summary, "lang": payload.lang}


@router.post("/stream")
def stream_chat(payload: ChatRequest) -> StreamingResponse:
    agent = Agent(lang=payload.lang, session=payload.session_id)

    def generate() -> Iterator[str]:
        for event in agent.run_stream(payload.message, force=payload.force):
            yield _format_sse(event)

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
