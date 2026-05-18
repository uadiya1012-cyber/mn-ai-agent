# 🤖 mn-ai-agent

Монгол + English · Mac M-chip · Local (Ollama) + Cloud (Claude API)

`local_bot`-ын мэдээ/пост үүсгэгч, код туслагч, FastAPI web UI-г энэ repo-д нэгтгэсэн. Цаашид хөгжүүлэх үндсэн төсөл: `mn-ai-agent`.

## Суулгах

```bash
# 1. Package суулгах
uv sync

# 2. API key тохируулах
cp .env.example .env
# .env файлыг нээгээд ANTHROPIC_API_KEY-г бөглөнө

# 3. Ollama (local news/code горимд)
brew install ollama
ollama serve
ollama pull qwen2.5:7b
ollama pull deepseek-coder:6.7b

# 4. Ажиллуулах
uv run python main.py
```

## CLI командууд

```bash
uv run python main.py                 # agent loop (Claude + Ollama router)
uv run python main.py news            # local мэдээ/пост үүсгэгч interactive
uv run python main.py code            # local код туслагч interactive
uv run python main.py check           # Ollama health/model шалгах
uv run python main.py web             # FastAPI web UI: http://127.0.0.1:8000
```

Шууд ашиглах жишээ:

```bash
uv run python main.py news --type instagram --topic "AI технологи" --lang mn --tone friendly
uv run python main.py news --type news --topic "Tesla шинэ загвар" --lang en --details "EV зах зээл"
uv run python main.py code "Python decorator гэж юу вэ?" --lang mn
```

## Хэрэглэх жишээ

```
❓ Instagram пост бичиж өг: Монголын уур амьсгал өөрчлөлтийн тухай
❓ Python-д async/await гэж юу вэ?
❓ Сүүлийн хариуг файлд хадгал
```

## Бүтэц

```
mn-ai-agent/
├── agent/
│   ├── core.py      ← agent loop
│   ├── local_code.py ← local Ollama код туслагч
│   ├── local_news.py ← local Ollama мэдээ/пост үүсгэгч
│   ├── ollama_client.py ← Ollama API helper
│   ├── models.py    ← Claude / Ollama
│   ├── memory.py    ← SQLite түүх
│   └── tools.py     ← хэрэгслүүд
├── web_app/          ← FastAPI web UI
├── tests/            ← unit + web tests
├── config.toml      ← тохиргоо
├── main.py          ← CLI
└── data/            ← DB + outputs (gitignore)
```

## Тест

```bash
uv run python -m unittest discover -s tests
```
