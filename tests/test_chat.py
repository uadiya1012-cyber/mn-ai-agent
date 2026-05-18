import unittest
from unittest.mock import patch

from agent import memory
from agent.core import Agent
from fastapi.testclient import TestClient

from web_app.app import app


class AgentStreamTests(unittest.TestCase):
    @patch("agent.core.models.stream_claude")
    def test_run_stream_collects_tokens_and_saves_memory(self, stream_claude):
        sid = "stream_unit_test"
        memory.clear(sid)
        stream_claude.return_value = iter([{"type": "token", "text": "Hello"}])

        agent = Agent(lang="mn", session=sid)
        events = list(agent.run_stream("Сайн уу", force="claude"))
        types = [e["type"] for e in events]

        self.assertIn("meta", types)
        self.assertIn("token", types)
        self.assertIn("done", types)
        self.assertEqual(events[-1]["content"], "Hello")

        history = memory.load(sid)
        self.assertEqual(len(history), 2)
        self.assertEqual(history[-1]["content"], "Hello")
        memory.clear(sid)

    @patch("agent.core.models.stream_ollama")
    def test_run_stream_surfaces_ollama_errors(self, stream_ollama):
        sid = "stream_err_test"
        memory.clear(sid)
        stream_ollama.return_value = iter(
            [{"type": "error", "message": "❌ Ollama offline"}]
        )

        agent = Agent(lang="mn", session=sid)
        events = list(agent.run_stream("python код", force="ollama"))
        self.assertTrue(any(e["type"] == "error" for e in events))
        self.assertFalse(any(e["type"] == "done" for e in events))
        memory.clear(sid)


class ChatApiTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    @patch("web_app.chat_routes.Agent.run_stream")
    def test_stream_endpoint_returns_sse_events(self, run_stream):
        run_stream.return_value = iter(
            [
                {"type": "meta", "session": "abc12345", "lang": "mn"},
                {"type": "meta", "route": "claude"},
                {"type": "token", "text": "Сайн"},
                {
                    "type": "done",
                    "content": "Сайн",
                    "route": "claude",
                    "session": "abc12345",
                },
            ]
        )

        with self.client.stream(
            "POST",
            "/api/chat/stream",
            json={"message": "hello", "lang": "mn"},
        ) as response:
            self.assertEqual(response.status_code, 200)
            body = "".join(response.iter_text())

        self.assertIn("event: token", body)
        self.assertIn("Сайн", body)
        self.assertIn("event: done", body)

    def test_history_and_clear_endpoints(self):
        sid = "web_hist_test"
        memory.clear(sid)
        memory.save(sid, "user", "test question")

        history = self.client.get(f"/api/chat/history?session_id={sid}")
        self.assertEqual(history.status_code, 200)
        self.assertEqual(len(history.json()["messages"]), 1)

        cleared = self.client.post("/api/chat/clear", json={"session_id": sid})
        self.assertEqual(cleared.status_code, 200)
        self.assertEqual(memory.load(sid), [])

    def test_chat_status_reports_claude_key(self):
        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}):
            response = self.client.get("/api/chat/status")
        self.assertTrue(response.json()["claude_configured"])


if __name__ == "__main__":
    unittest.main()
