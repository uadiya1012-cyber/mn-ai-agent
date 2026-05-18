import unittest
from unittest.mock import patch

from agent import memory
from agent.models import route_for, route_label
from fastapi.testclient import TestClient

from web_app.app import app


class RouterTests(unittest.TestCase):
    def _route(self, text: str) -> str:
        return route_for([{"role": "user", "content": text}])

    def test_code_routes_to_ollama(self):
        self.assertEqual(self._route("Python decorator гэж юу вэ?"), "ollama")
        self.assertEqual(self._route("debug this javascript error"), "ollama")

    def test_content_routes_to_claude(self):
        self.assertEqual(
            self._route("Instagram пост бичиж өг: AI технологи"),
            "claude",
        )
        self.assertEqual(self._route("Facebook мэдээний нийтлэл"), "claude")

    def test_mixed_prefers_claude_without_strong_code(self):
        self.assertEqual(
            self._route("Instagram пост python сургалтын тухай"),
            "claude",
        )

    def test_mixed_with_strong_code_goes_ollama(self):
        self.assertEqual(
            self._route("python debug мэдээний пост script"),
            "ollama",
        )

    def test_force_overrides_keywords(self):
        msgs = [{"role": "user", "content": "python код"}]
        self.assertEqual(route_for(msgs, force="claude"), "claude")
        self.assertEqual(route_for(msgs, force="ollama"), "ollama")

    def test_route_label(self):
        self.assertIn("Claude", route_label("claude"))
        self.assertIn("Ollama", route_label("ollama"))


class ExportSummaryApiTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.sid = "export_api_test"
        memory.clear(self.sid)
        memory.save(self.sid, "user", "Сайн уу")
        memory.save(self.sid, "assistant", "Сайн байна уу")

    def tearDown(self):
        memory.clear(self.sid)

    def test_export_endpoint(self):
        res = self.client.post(
            "/api/chat/export",
            json={"session_id": self.sid, "fmt": "md"},
        )
        self.assertEqual(res.status_code, 200)
        self.assertIn("Exported", res.json()["message"])

    def test_export_rejects_empty_session(self):
        memory.clear("empty_sess")
        res = self.client.post(
            "/api/chat/export",
            json={"session_id": "empty_sess", "fmt": "md"},
        )
        self.assertEqual(res.status_code, 400)

    @patch("agent.models.ask", return_value="• bullet one")
    def test_summary_endpoint(self, _ask):
        res = self.client.post(
            "/api/chat/summary",
            json={"session_id": self.sid, "lang": "mn"},
        )
        self.assertEqual(res.status_code, 200)
        self.assertIn("bullet", res.json()["summary"])


if __name__ == "__main__":
    unittest.main()
