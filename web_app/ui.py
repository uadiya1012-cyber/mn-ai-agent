"""Web UI — нэг HTML хуудас (чат + мэдээ + код)."""

HTML = r"""<!doctype html>
<html lang="mn">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>mn-ai-agent</title>
  <style>
    :root {
      color-scheme: light;
      --ink: #17201b;
      --muted: #66736c;
      --line: #d8ded8;
      --paper: #f7f5ef;
      --panel: #ffffff;
      --accent: #1c7c6b;
      --accent-2: #b84a3a;
      --focus: #f0b429;
      --user-bg: #e8f4f1;
      --bot-bg: #fffdf8;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background: var(--paper);
      color: var(--ink);
    }
    header {
      min-height: 64px;
      padding: 14px 24px;
      border-bottom: 1px solid var(--line);
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
      background: #fbfaf6;
    }
    h1 { font-size: 20px; margin: 0; font-weight: 760; }
    .status {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      min-height: 34px;
      padding: 0 12px;
      border: 1px solid var(--line);
      border-radius: 999px;
      background: var(--panel);
      color: var(--muted);
      font-size: 13px;
    }
    .dot { width: 9px; height: 9px; border-radius: 999px; background: var(--focus); }
    .dot.ok { background: var(--accent); }
    .dot.bad { background: var(--accent-2); }
    main {
      width: min(1180px, 100%);
      margin: 0 auto;
      padding: 24px;
      display: grid;
      grid-template-columns: 200px 1fr;
      gap: 20px;
      align-items: start;
    }
    nav { display: grid; gap: 10px; }
    .tab {
      min-height: 48px;
      border: 1px solid var(--line);
      background: var(--panel);
      border-radius: 8px;
      font: inherit;
      font-weight: 650;
      text-align: left;
      padding: 0 14px;
      cursor: pointer;
    }
    .tab.active {
      border-color: var(--accent);
      box-shadow: inset 4px 0 0 var(--accent);
    }
    .workspace {
      display: grid;
      grid-template-columns: minmax(280px, 420px) minmax(320px, 1fr);
      gap: 20px;
      align-items: start;
    }
  .chat-layout {
      display: flex;
      flex-direction: column;
      min-height: min(720px, calc(100vh - 140px));
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      overflow: hidden;
    }
    .chat-toolbar {
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      gap: 10px;
      padding: 12px 16px;
      border-bottom: 1px solid var(--line);
      background: #fbfaf6;
      font-size: 13px;
      color: var(--muted);
    }
    .chat-toolbar select, .chat-toolbar button {
      font: inherit;
      font-size: 13px;
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 6px 10px;
      background: #fff;
      color: var(--ink);
      cursor: pointer;
    }
    .chat-toolbar button.primary-sm {
      background: var(--accent);
      color: #fff;
      border-color: var(--accent);
    }
    .badge {
      padding: 4px 10px;
      border-radius: 999px;
      background: #eef5f2;
      color: var(--accent);
      font-weight: 650;
    }
    .badge.ollama { background: #f5f0e8; color: #8a5a12; }
    .session-id { font-family: ui-monospace, monospace; }
    .chat-messages {
      flex: 1;
      overflow-y: auto;
      padding: 20px;
      display: flex;
      flex-direction: column;
      gap: 14px;
    }
    .msg {
      max-width: 88%;
      padding: 12px 14px;
      border-radius: 10px;
      line-height: 1.55;
      font-size: 15px;
      white-space: pre-wrap;
      overflow-wrap: anywhere;
    }
    .msg.user {
      align-self: flex-end;
      background: var(--user-bg);
      border: 1px solid #c5e0d8;
    }
    .msg.assistant {
      align-self: flex-start;
      background: var(--bot-bg);
      border: 1px solid var(--line);
    }
    .msg.status {
      align-self: center;
      max-width: 100%;
      font-size: 13px;
      color: var(--muted);
      background: transparent;
      border: 0;
      padding: 4px;
    }
    .msg.error {
      align-self: stretch;
      background: #fdf0ee;
      border-color: #e8c4bc;
      color: var(--accent-2);
    }
    .chat-composer {
      display: flex;
      gap: 10px;
      padding: 14px 16px;
      border-top: 1px solid var(--line);
      background: #fbfaf6;
    }
    .chat-composer textarea {
      flex: 1;
      min-height: 48px;
      max-height: 160px;
      resize: vertical;
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 10px 12px;
      font: inherit;
    }
    .chat-composer button {
      align-self: flex-end;
      min-height: 48px;
      min-width: 100px;
      border: 0;
      border-radius: 8px;
      background: var(--accent);
      color: #fff;
      font: inherit;
      font-weight: 700;
      cursor: pointer;
    }
    .chat-composer button:disabled { opacity: 0.55; cursor: wait; }
    form, .output {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 18px;
    }
    form { display: grid; gap: 14px; }
    .field { display: grid; gap: 7px; }
    label { color: var(--muted); font-size: 13px; font-weight: 650; }
    input, select, textarea {
      width: 100%;
      border: 1px solid var(--line);
      border-radius: 7px;
      min-height: 40px;
      padding: 9px 10px;
      font: inherit;
      background: #fffdf8;
    }
    textarea { min-height: 112px; resize: vertical; }
    button.primary {
      min-height: 44px;
      border: 0;
      border-radius: 7px;
      background: var(--accent);
      color: #fff;
      font: inherit;
      font-weight: 760;
      cursor: pointer;
    }
    button.primary:disabled { opacity: 0.62; cursor: wait; }
    .output {
      min-height: 520px;
      display: grid;
      grid-template-rows: auto 1fr;
      gap: 12px;
    }
    .output-head {
      display: flex;
      justify-content: space-between;
      color: var(--muted);
      font-size: 13px;
      border-bottom: 1px solid var(--line);
      padding-bottom: 10px;
    }
    pre {
      margin: 0;
      white-space: pre-wrap;
      overflow-wrap: anywhere;
      font: 15px/1.55 ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
    }
    .hidden { display: none !important; }
    @media (max-width: 920px) {
      main, .workspace { grid-template-columns: 1fr; }
      header { flex-direction: column; align-items: flex-start; }
    }
  </style>
</head>
<body>
  <header>
    <h1>mn-ai-agent</h1>
    <div class="status"><span id="statusDot" class="dot"></span><span id="statusText">Шалгаж байна...</span></div>
  </header>
  <main>
    <nav aria-label="Tools">
      <button class="tab active" data-view="chat">💬 Agent чат</button>
      <button class="tab" data-view="news">📰 Мэдээ / Пост</button>
      <button class="tab" data-view="code">⌨️ Код туслагч</button>
      <button class="tab" data-view="rag">📚 RAG</button>
    </nav>

    <section id="chatView" class="chat-layout">
      <div class="chat-toolbar">
        <span>Session: <span id="sessionLabel" class="session-id">—</span></span>
        <span id="routeBadge" class="badge hidden"></span>
        <label>
          Router
          <select id="chatRoute">
            <option value="">Автомат</option>
            <option value="claude">Claude</option>
            <option value="ollama">Ollama</option>
          </select>
        </label>
        <label>
          Хэл
          <select id="chatLang">
            <option value="mn">Монгол</option>
            <option value="en">English</option>
          </select>
        </label>
        <button type="button" id="exportChatBtn">Экспорт</button>
        <button type="button" id="summaryChatBtn">Товчлол</button>
        <button type="button" id="newChatBtn">Шинэ чат</button>
        <button type="button" id="clearChatBtn">Цэвэрлэх</button>
      </div>
      <div id="chatMessages" class="chat-messages" aria-live="polite">
        <div class="msg status">Монгол + English туслагч. Асуултаа доор бичнэ үү.</div>
      </div>
      <form id="chatForm" class="chat-composer">
        <textarea id="chatInput" rows="2" placeholder="Жишээ: Instagram пост бичиж өг..." required></textarea>
        <button type="submit" id="chatSendBtn">Илгээх</button>
      </form>
    </section>

    <section id="newsView" class="workspace hidden">
      <form id="newsForm">
        <div class="field">
          <label for="postType">Төрөл</label>
          <select id="postType" name="post_type">
            <option value="instagram">Instagram</option>
            <option value="facebook">Facebook</option>
            <option value="linkedin">LinkedIn</option>
            <option value="tiktok">TikTok</option>
            <option value="news">News article</option>
          </select>
        </div>
        <div class="field">
          <label for="newsLang">Хэл</label>
          <select id="newsLang" name="lang">
            <option value="mn">Монгол</option>
            <option value="en">English</option>
          </select>
        </div>
        <div class="field">
          <label for="tone">Tone</label>
          <select id="tone" name="tone">
            <option value="balanced">Balanced</option>
            <option value="friendly">Friendly</option>
            <option value="formal">Formal</option>
            <option value="marketing">Marketing</option>
            <option value="short">Short</option>
          </select>
        </div>
        <div class="field">
          <label for="topic">Сэдэв</label>
          <input id="topic" name="topic" required placeholder="AI технологи" />
        </div>
        <div class="field">
          <label for="details">Нэмэлт</label>
          <textarea id="details" name="details" placeholder="Зорилтот уншигч, гол санаа..."></textarea>
        </div>
        <button class="primary" type="submit">Үүсгэх</button>
      </form>
      <section class="output">
        <div class="output-head"><span>Гаралт</span><span id="newsMeta">Ready</span></div>
        <pre id="newsOutput">Энд үүсгэсэн пост харагдана.</pre>
      </section>
    </section>

    <section id="ragView" class="workspace hidden">
      <form id="ragForm">
        <div class="field">
          <label for="ragQuery">Хайлт</label>
          <textarea id="ragQuery" name="query" required placeholder="CloudDesk үнэ хэд вэ?"></textarea>
        </div>
        <div class="field">
          <label for="ragTopK">Top K</label>
          <input id="ragTopK" name="top_k" type="number" min="1" max="12" value="4" />
        </div>
        <button class="primary" type="submit">Хайх</button>
        <button class="primary" type="button" id="ragIndexBtn" style="background:#5a6b63;">Индекслэх</button>
      </form>
      <section class="output">
        <div class="output-head"><span>RAG</span><span id="ragMeta">Ready</span></div>
        <pre id="ragOutput">Статус ачаалж байна...</pre>
      </section>
    </section>

    <section id="codeView" class="workspace hidden">
      <form id="codeForm">
        <div class="field">
          <label for="codeLang">Хэл</label>
          <select id="codeLang" name="lang">
            <option value="mn">Монгол</option>
            <option value="en">English</option>
          </select>
        </div>
        <div class="field">
          <label for="question">Асуулт</label>
          <textarea id="question" name="question" required placeholder="Python decorator гэж юу вэ?"></textarea>
        </div>
        <button class="primary" type="submit">Асуух</button>
      </form>
      <section class="output">
        <div class="output-head"><span>Хариу</span><span id="codeMeta">Ready</span></div>
        <pre id="codeOutput">Энд код туслагчийн хариу харагдана.</pre>
      </section>
    </section>
  </main>
  <script>
    const $ = (sel) => document.querySelector(sel);
    const tabs = document.querySelectorAll(".tab");
    const STORAGE_KEY = "mn-ai-agent-session";

    let sessionId = localStorage.getItem(STORAGE_KEY) || "";
    let streaming = false;
    let assistantNode = null;

    function newSessionId() {
      return Math.random().toString(36).slice(2, 10);
    }

    function ensureSession() {
      if (!sessionId) {
        sessionId = newSessionId();
        localStorage.setItem(STORAGE_KEY, sessionId);
      }
      $("#sessionLabel").textContent = sessionId;
    }

    function showView(name) {
      $("#chatView").classList.toggle("hidden", name !== "chat");
      $("#newsView").classList.toggle("hidden", name !== "news");
      $("#codeView").classList.toggle("hidden", name !== "code");
      $("#ragView").classList.toggle("hidden", name !== "rag");
      if (name === "rag") loadRagStatus();
    }

    async function loadRagStatus() {
      try {
        const res = await fetch("/api/rag/status");
        const data = await res.json();
        $("#ragMeta").textContent = `${data.chunks_indexed} chunks · ${data.files_on_disk} files`;
        $("#ragOutput").textContent = JSON.stringify(data, null, 2);
      } catch (err) {
        $("#ragMeta").textContent = "Error";
        $("#ragOutput").textContent = err.message;
      }
    }

    tabs.forEach((tab) => {
      tab.addEventListener("click", () => {
        tabs.forEach((t) => t.classList.remove("active"));
        tab.classList.add("active");
        showView(tab.dataset.view);
        if (tab.dataset.view === "chat") loadHistory();
      });
    });

    function appendMessage(role, text, extraClass = "") {
      const el = document.createElement("div");
      el.className = `msg ${role} ${extraClass}`.trim();
      el.textContent = text;
      $("#chatMessages").appendChild(el);
      $("#chatMessages").scrollTop = $("#chatMessages").scrollHeight;
      return el;
    }

    function setRouteBadge(route, label, mode) {
      const badge = $("#routeBadge");
      if (!route) {
        badge.classList.add("hidden");
        return;
      }
      badge.classList.remove("hidden", "ollama");
      const locked = mode && mode !== "auto" ? " 🔒" : "";
      badge.textContent = (label || (route === "ollama" ? "Ollama · код" : "Claude · tool use")) + locked;
      if (route === "ollama") badge.classList.add("ollama");
    }

    async function loadHistory() {
      ensureSession();
      try {
        const res = await fetch(`/api/chat/history?session_id=${encodeURIComponent(sessionId)}`);
        const data = await res.json();
        const box = $("#chatMessages");
        box.innerHTML = "";
        if (!data.messages.length) {
          appendMessage("status", "Монгол + English туслагч. Асуултаа доор бичнэ үү.");
          return;
        }
        for (const m of data.messages) {
          appendMessage(m.role === "user" ? "user" : "assistant", m.content);
        }
      } catch (err) {
        appendMessage("status", "Түүх ачаалахад алдаа: " + err.message);
      }
    }

    function parseSseBlock(block) {
      let eventType = "message";
      let dataLine = "";
      for (const line of block.split("\n")) {
        if (line.startsWith("event: ")) eventType = line.slice(7).trim();
        if (line.startsWith("data: ")) dataLine = line.slice(6);
      }
      if (!dataLine) return null;
      try {
        return { eventType, payload: JSON.parse(dataLine) };
      } catch {
        return null;
      }
    }

    async function streamChat(message) {
      const lang = $("#chatLang").value;
      const routeSel = $("#chatRoute").value;
      const body = { message, lang, session_id: sessionId };
      if (routeSel) body.force = routeSel;

      const res = await fetch("/api/chat/stream", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || res.statusText || "Request failed");
      }

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const parts = buffer.split("\n\n");
        buffer = parts.pop() || "";
        for (const part of parts) {
          const parsed = parseSseBlock(part);
          if (!parsed) continue;
          handleStreamEvent(parsed.eventType, parsed.payload);
        }
      }
      if (buffer.trim()) {
        const parsed = parseSseBlock(buffer);
        if (parsed) handleStreamEvent(parsed.eventType, parsed.payload);
      }
    }

    function handleStreamEvent(eventType, payload) {
      if (eventType === "meta") {
        if (payload.session) {
          sessionId = payload.session;
          localStorage.setItem(STORAGE_KEY, sessionId);
          $("#sessionLabel").textContent = sessionId;
        }
        if (payload.route) {
          setRouteBadge(payload.route, payload.route_label, payload.route_mode);
        }
        return;
      }
      if (eventType === "token") {
        if (!assistantNode) {
          assistantNode = appendMessage("assistant", "");
        }
        assistantNode.textContent += payload.text || "";
        $("#chatMessages").scrollTop = $("#chatMessages").scrollHeight;
        return;
      }
      if (eventType === "status") {
        appendMessage("status", payload.message || "");
        return;
      }
      if (eventType === "error") {
        appendMessage("assistant error", payload.message || "Алдаа", "error");
        assistantNode = null;
        return;
      }
      if (eventType === "done") {
        if (!assistantNode && payload.content) {
          assistantNode = appendMessage("assistant", payload.content);
        } else if (assistantNode && payload.content) {
          assistantNode.textContent = payload.content;
        }
        assistantNode = null;
        return;
      }
    }

    $("#chatForm").addEventListener("submit", async (e) => {
      e.preventDefault();
      if (streaming) return;
      const input = $("#chatInput");
      const text = input.value.trim();
      if (!text) return;

      ensureSession();
      streaming = true;
      $("#chatSendBtn").disabled = true;
      assistantNode = null;

      appendMessage("user", text);
      input.value = "";

      try {
        await streamChat(text);
      } catch (err) {
        appendMessage("assistant error", err.message, "error");
      } finally {
        streaming = false;
        $("#chatSendBtn").disabled = false;
        input.focus();
      }
    });

    $("#newChatBtn").addEventListener("click", () => {
      sessionId = newSessionId();
      localStorage.setItem(STORAGE_KEY, sessionId);
      $("#sessionLabel").textContent = sessionId;
      $("#chatMessages").innerHTML = "";
      appendMessage("status", "Шинэ чат эхэллээ.");
      setRouteBadge(null);
    });

    $("#exportChatBtn").addEventListener("click", async () => {
      ensureSession();
      try {
        const res = await fetch("/api/chat/export", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ session_id: sessionId, fmt: "md" }),
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || "Export failed");
        appendMessage("status", data.message);
      } catch (err) {
        appendMessage("status", "Экспорт алдаа: " + err.message);
      }
    });

    $("#summaryChatBtn").addEventListener("click", async () => {
      ensureSession();
      if (streaming) return;
      streaming = true;
      $("#summaryChatBtn").disabled = true;
      appendMessage("status", "Товчлол үүсгэж байна (Claude)...");
      try {
        const res = await fetch("/api/chat/summary", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            session_id: sessionId,
            lang: $("#chatLang").value,
          }),
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || "Summary failed");
        appendMessage("assistant", "📋 " + data.summary);
      } catch (err) {
        appendMessage("status", "Товчлол алдаа: " + err.message);
      } finally {
        streaming = false;
        $("#summaryChatBtn").disabled = false;
      }
    });

    $("#clearChatBtn").addEventListener("click", async () => {
      ensureSession();
      try {
        await fetch("/api/chat/clear", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ session_id: sessionId }),
        });
        $("#chatMessages").innerHTML = "";
        appendMessage("status", "Ярианы түүх цэвэрлэгдлээ.");
        setRouteBadge(null);
      } catch (err) {
        appendMessage("status", "Цэвэрлэхэд алдаа: " + err.message);
      }
    });

    async function jsonFetch(url, payload) {
      const response = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Request failed");
      return data;
    }

    async function checkHealth() {
      const dot = $("#statusDot");
      const text = $("#statusText");
      try {
        const [health, chatStatus] = await Promise.all([
          fetch("/api/health").then((r) => r.json()),
          fetch("/api/chat/status").then((r) => r.json()),
        ]);
        const ollamaOk = health.ok;
        const claudeOk = chatStatus.claude_configured;
        dot.className = `dot ${ollamaOk || claudeOk ? "ok" : "bad"}`;
        const parts = [];
        if (claudeOk) parts.push("Claude");
        if (ollamaOk) parts.push(`Ollama · ${health.models.length} models`);
        if (!claudeOk) parts.push("Claude key байхгүй");
        if (!ollamaOk) parts.push(health.error || "Ollama offline");
        text.textContent = parts.join(" · ");
      } catch (error) {
        dot.className = "dot bad";
        text.textContent = error.message;
      }
    }

    $("#newsForm").addEventListener("submit", async (event) => {
      event.preventDefault();
      const button = event.submitter;
      button.disabled = true;
      $("#newsMeta").textContent = "Generating...";
      $("#newsOutput").textContent = "";
      try {
        const data = await jsonFetch("/api/news", Object.fromEntries(new FormData(event.currentTarget)));
        $("#newsMeta").textContent = `${data.type} · ${data.lang} · ${data.tone}`;
        $("#newsOutput").textContent = data.content;
      } catch (error) {
        $("#newsMeta").textContent = "Error";
        $("#newsOutput").textContent = error.message;
      } finally {
        button.disabled = false;
      }
    });

    $("#ragForm").addEventListener("submit", async (event) => {
      event.preventDefault();
      const button = event.submitter;
      button.disabled = true;
      $("#ragMeta").textContent = "Searching...";
      $("#ragOutput").textContent = "";
      const query = $("#ragQuery").value.trim();
      const top_k = Number($("#ragTopK").value) || 4;
      try {
        const res = await fetch("/api/rag/search", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ query, top_k }),
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || "Search failed");
        $("#ragMeta").textContent = `${data.count} hit(s)`;
        $("#ragOutput").textContent = data.formatted;
      } catch (err) {
        $("#ragMeta").textContent = "Error";
        $("#ragOutput").textContent = err.message;
      } finally {
        button.disabled = false;
      }
    });

    $("#ragIndexBtn").addEventListener("click", async () => {
      const btn = $("#ragIndexBtn");
      btn.disabled = true;
      $("#ragMeta").textContent = "Indexing...";
      try {
        const res = await fetch("/api/rag/index?force=false", { method: "POST" });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || "Index failed");
        $("#ragOutput").textContent = data.message || JSON.stringify(data, null, 2);
        await loadRagStatus();
      } catch (err) {
        $("#ragMeta").textContent = "Error";
        $("#ragOutput").textContent = err.message;
      } finally {
        btn.disabled = false;
      }
    });

    $("#codeForm").addEventListener("submit", async (event) => {
      event.preventDefault();
      const button = event.submitter;
      button.disabled = true;
      $("#codeMeta").textContent = "Thinking...";
      $("#codeOutput").textContent = "";
      try {
        const data = await jsonFetch("/api/code", Object.fromEntries(new FormData(event.currentTarget)));
        $("#codeMeta").textContent = data.lang;
        $("#codeOutput").textContent = data.answer;
      } catch (error) {
        $("#codeMeta").textContent = "Error";
        $("#codeOutput").textContent = error.message;
      } finally {
        button.disabled = false;
      }
    });

    ensureSession();
    checkHealth();
    loadHistory();
  </script>
</body>
</html>"""
