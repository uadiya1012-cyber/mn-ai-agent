import io
import unittest
from contextlib import redirect_stdout
from unittest.mock import Mock, patch

from agent.local_code import CodeBotSession
from agent.local_news import (
    QUALITY_GUIDELINES,
    TONES,
    build_prompt,
    build_safe_mongolian_content,
    generate_post,
    has_content_issues,
    has_low_quality_mongolian,
    has_script_issues,
    polish_mongolian_content,
)
from agent.local_config import POST_TYPES
from agent import local_config as config
from agent.ollama_client import chat_stream, model_is_installed


class ConfigTests(unittest.TestCase):
    def test_models_include_expected_keys(self):
        self.assertIn("news", config.MODELS)
        self.assertIn("code", config.MODELS)
        self.assertIsInstance(config.MODELS["news"], str)
        self.assertIsInstance(config.MODELS["code"], str)

    def test_post_types_include_linkedin_and_tiktok(self):
        self.assertIn("linkedin", POST_TYPES)
        self.assertIn("tiktok", POST_TYPES)

    def test_model_matching_accepts_exact_and_base_name(self):
        self.assertTrue(model_is_installed("qwen2.5:7b", ["qwen2.5:7b"]))
        self.assertTrue(model_is_installed("qwen2.5:7b", ["qwen2.5:latest"]))
        self.assertFalse(model_is_installed("qwen2.5:7b", ["llama3.2:latest"]))


class NewsBotTests(unittest.TestCase):
    @patch("agent.local_news.call_ollama", return_value="Generated post")
    def test_generate_post_defaults_invalid_language(self, call_ollama):
        with redirect_stdout(io.StringIO()):
            result = generate_post("instagram", "AI topic", lang="bad")

        self.assertEqual(result["type"], "instagram")
        self.assertEqual(result["lang"], config.DEFAULT_LANG)
        self.assertEqual(result["tone"], "balanced")
        self.assertEqual(result["content"], "Generated post")
        self.assertTrue(result["polished"])
        self.assertIsNone(result["fallback"])
        self.assertEqual(call_ollama.call_count, 2)

    @patch("agent.local_news.call_ollama", return_value="Generated post")
    def test_generate_post_adds_tone_instruction(self, call_ollama):
        with redirect_stdout(io.StringIO()):
            result = generate_post("facebook", "AI topic", lang="en", tone="friendly")

        self.assertEqual(result["tone"], "friendly")
        prompt = call_ollama.call_args.args[0]
        self.assertIn(TONES["friendly"]["en"], prompt)
        self.assertIn(QUALITY_GUIDELINES["en"], prompt)

    @patch("agent.local_news.call_ollama", return_value="Generated post")
    def test_generate_post_defaults_invalid_tone(self, call_ollama):
        with redirect_stdout(io.StringIO()):
            result = generate_post("news", "AI topic", lang="en", tone="loud")

        self.assertEqual(result["tone"], "balanced")
        prompt = call_ollama.call_args.args[0]
        self.assertIn(TONES["balanced"]["en"], prompt)

    @patch("agent.local_news.call_ollama", return_value="Зассан бичвэр")
    def test_polish_mongolian_content_uses_editor_prompt(self, call_ollama):
        result = polish_mongolian_content("Эвдэрхий бичвэр", "facebook", "friendly")

        self.assertEqual(result, "Зассан бичвэр")
        prompt = call_ollama.call_args.args[0]
        self.assertIn("Монгол хэлний редактор", prompt)
        self.assertIn("Эвдэрхий бичвэр", prompt)

    def test_generate_post_rejects_unknown_type(self):
        result = generate_post("unknown", "AI topic")
        self.assertIn("error", result)

    def test_low_quality_mongolian_detection(self):
        self.assertTrue(has_low_quality_mongolian("AI нь санал буулгах технологи юм."))
        self.assertFalse(has_low_quality_mongolian("AI нь өдөр тутмын ажлыг хөнгөвчлөх технологи юм."))

    def test_script_issues_detects_latin_transliteration(self):
        self.assertTrue(
            has_script_issues("Сайн baina uu? Энэ бол sain content.")
        )
        self.assertFalse(
            has_script_issues("Сайн байна уу? #AI #Монгол")
        )

    def test_has_content_issues_combines_heuristics(self):
        self.assertTrue(
            has_content_issues("Сайн baina uu, энэ маш sain content.")
        )
        self.assertFalse(
            has_content_issues("Хиймэл оюун нь ажлыг хөнгөвчилж чадна.")
        )

    @patch("agent.local_news.call_ollama", return_value="Generated")
    def test_build_prompt_includes_linkedin_format(self, _call):
        prompt = build_prompt("linkedin", "AI", "details", "mn", "formal")
        self.assertIn("LinkedIn", prompt)
        self.assertIn("HOOK", prompt)

    @patch("agent.local_news.call_ollama", return_value="Generated")
    def test_build_prompt_includes_tiktok_script(self, _call):
        prompt = build_prompt("tiktok", "Боловсрол", "", "mn", "friendly")
        self.assertIn("TikTok", prompt)
        self.assertIn("HOOK", prompt)

    def test_safe_fallback_for_linkedin_and_tiktok(self):
        linkedin = build_safe_mongolian_content(
            "linkedin", "AI", "", "formal"
        )
        tiktok = build_safe_mongolian_content(
            "tiktok", "AI", "", "friendly"
        )
        self.assertIn("LinkedIn", linkedin)
        self.assertIn("TikTok", tiktok)
        self.assertIn("🎬", tiktok)

    def test_safe_mongolian_fallback_is_readable(self):
        content = build_safe_mongolian_content(
            "facebook",
            "AI технологи",
            "Энгийн хүмүүст ойлгомжтой тайлбарла.",
            "friendly",
        )

        self.assertIn("хиймэл оюун", content.lower())
        self.assertIn("#AI", content)
        self.assertNotIn("[link]", content)


class CodeBotTests(unittest.TestCase):
    @patch("agent.local_code.stream_ollama", return_value="answer")
    def test_ask_limits_messages_sent_to_model(self, stream_ollama):
        session = CodeBotSession(lang="mn")
        session.history = [
            {"role": "user", "content": f"old question {i}"}
            for i in range(config.MAX_HISTORY_MESSAGES + 5)
        ]

        answer = session.ask("new question")

        self.assertEqual(answer, "answer")
        messages = stream_ollama.call_args.args[0]
        self.assertEqual(messages[0]["role"], "system")
        self.assertLessEqual(len(messages) - 1, config.MAX_HISTORY_MESSAGES)
        self.assertEqual(messages[-1]["content"], "new question")


class OllamaClientTests(unittest.TestCase):
    @patch("agent.ollama_client.requests.post")
    def test_chat_stream_collects_tokens(self, post):
        response = Mock()
        response.iter_lines.return_value = [
            b'{"message":{"content":"Hello"},"done":false}',
            b'{"message":{"content":" world"},"done":true}',
        ]
        response.raise_for_status.return_value = None
        post.return_value = response

        tokens = []
        result = chat_stream(
            [{"role": "user", "content": "hi"}],
            "model",
            on_token=tokens.append,
        )

        self.assertEqual(result, "Hello world")
        self.assertEqual(tokens, ["Hello", " world"])


class WebAppTests(unittest.TestCase):
    @patch("web_app.app.generate_post", return_value={
        "type": "instagram",
        "lang": "mn",
        "tone": "friendly",
        "topic": "AI",
        "content": "Generated",
        "generated_at": "2026-01-01T00:00:00",
    })
    def test_news_endpoint_returns_generated_content(self, generate_post_mock):
        from fastapi.testclient import TestClient
        from web_app.app import app

        client = TestClient(app)
        response = client.post(
            "/api/news",
            json={
                "post_type": "instagram",
                "topic": "AI",
                "lang": "mn",
                "tone": "friendly",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["content"], "Generated")
        generate_post_mock.assert_called_once()


class ToolsTests(unittest.TestCase):
    def test_export_session_creates_file(self):
        from agent import memory
        from agent import tools

        sid = "testsess"
        memory.clear(sid)
        memory.save(sid, "user", "hello")
        memory.save(sid, "assistant", "hi there")

        res = tools.export_session(sid, fmt="md")
        self.assertIn("Exported", res)

    def test_export_rejects_invalid_format(self):
        from agent import tools

        res = tools.export_session("testsess", fmt="pdf")
        self.assertTrue(res.startswith("❌"))

    @patch("agent.models.ask", return_value="• товчлол")
    def test_summarize_session_uses_newlines(self, ask_mock):
        from agent import memory, tools

        sid = "sumtest"
        memory.clear(sid)
        memory.save(sid, "user", "hello")
        memory.save(sid, "assistant", "hi")

        result = tools.summarize_session(sid, lang="mn")
        self.assertEqual(result, "• товчлол")
        prompt = ask_mock.call_args[0][0][0]["content"]
        self.assertIn("user: hello", prompt)
        self.assertNotIn("\\n", prompt)



if __name__ == "__main__":
    unittest.main()
