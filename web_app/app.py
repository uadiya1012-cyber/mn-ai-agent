"""FastAPI web app — agent чат, мэдээ, код."""

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from agent.local_code import CodeBotSession
from agent.local_config import POST_TYPES
from agent.local_news import TONES, generate_post
from agent.ollama_client import OllamaError, list_models
from web_app.chat_routes import router as chat_router
from web_app.rag_routes import router as rag_router
from web_app.ui import HTML

load_dotenv()

app = FastAPI(title="mn-ai-agent", version="0.4.0")
app.include_router(chat_router, prefix="/api/chat", tags=["chat"])
app.include_router(rag_router, prefix="/api/rag", tags=["rag"])


class NewsRequest(BaseModel):
    post_type: str = Field(pattern=f"^({'|'.join(POST_TYPES)})$")
    topic: str = Field(min_length=1, max_length=300)
    details: str = Field(default="", max_length=2000)
    lang: str = Field(default="mn", pattern="^(mn|en)$")
    tone: str = Field(default="balanced")


class CodeRequest(BaseModel):
    question: str = Field(min_length=1, max_length=4000)
    lang: str = Field(default="mn", pattern="^(mn|en)$")


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return HTML


@app.get("/api/health")
def health() -> dict:
    try:
        return {"ok": True, "models": list_models()}
    except OllamaError as exc:
        return {"ok": False, "error": str(exc), "models": []}


@app.post("/api/news")
def create_news(payload: NewsRequest) -> dict:
    if payload.tone not in TONES:
        raise HTTPException(status_code=422, detail="Invalid tone")

    result = generate_post(
        payload.post_type,
        payload.topic,
        payload.details,
        payload.lang,
        payload.tone,
    )
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@app.post("/api/code")
def ask_code(payload: CodeRequest) -> dict:
    session = CodeBotSession(lang=payload.lang)
    answer = session.ask(payload.question)
    return {"answer": answer, "lang": payload.lang}
