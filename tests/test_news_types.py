import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from web_app.app import app


class NewsTypeApiTests(unittest.TestCase):
    @patch(
        "web_app.app.generate_post",
        return_value={
            "type": "linkedin",
            "lang": "mn",
            "tone": "formal",
            "topic": "AI",
            "content": "LinkedIn post",
            "polished": True,
            "fallback": None,
            "generated_at": "2026-01-01T00:00:00",
        },
    )
    def test_linkedin_endpoint(self, generate_post_mock):
        client = TestClient(app)
        response = client.post(
            "/api/news",
            json={
                "post_type": "linkedin",
                "topic": "AI",
                "lang": "mn",
                "tone": "formal",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["type"], "linkedin")
        generate_post_mock.assert_called_once()

    def test_invalid_post_type_rejected(self):
        client = TestClient(app)
        response = client.post(
            "/api/news",
            json={
                "post_type": "twitter",
                "topic": "AI",
                "lang": "mn",
            },
        )
        self.assertEqual(response.status_code, 422)


if __name__ == "__main__":
    unittest.main()
