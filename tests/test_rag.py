import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from agent.rag.chunking import chunk_text
from agent.rag.store import ChunkHit, clear_all, search_vectors, upsert_file_chunks
from fastapi.testclient import TestClient

from web_app.app import app


class ChunkingTests(unittest.TestCase):
    def test_chunk_text_overlap(self):
        text = "а" * 600
        chunks = chunk_text(text, size=200, overlap=40)
        self.assertGreater(len(chunks), 1)
        self.assertLessEqual(len(chunks[0]), 200)


class StoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.db_patch = patch(
            "agent.rag.store.index_db_path",
            return_value=Path(self.tmp.name) / "rag.db",
        )
        self.db_patch.start()
        clear_all()

    def tearDown(self):
        self.db_patch.stop()

    def test_search_vectors_ranking(self):
        upsert_file_chunks(
            "a.md",
            "hash1",
            [
                (0, "CloudDesk pricing starts at 29000", [1.0, 0.0, 0.0]),
                (1, "Unrelated cooking recipe", [0.0, 1.0, 0.0]),
            ],
        )
        hits = search_vectors([0.95, 0.05, 0.0], top_k=2, min_score=0.1)
        self.assertEqual(hits[0].source, "a.md")
        self.assertIn("CloudDesk", hits[0].content)


class IngestTests(unittest.TestCase):
    def test_discover_md_files(self):
        from agent.rag.ingest import discover_files

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "doc.md").write_text("# Hello", encoding="utf-8")
            (root / "skip.pdf").write_bytes(b"%PDF")
            files = discover_files(root)
            self.assertEqual(len(files), 1)
            self.assertEqual(files[0].name, "doc.md")


class RagApiTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_status_endpoint(self):
        with patch("web_app.rag_routes.status", return_value={"chunks_indexed": 3}):
            res = self.client.get("/api/rag/status")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["chunks_indexed"], 3)

    @patch("web_app.rag_routes.search")
    def test_search_endpoint(self, search_mock):
        search_mock.return_value = [
            ChunkHit(source="example.md", content="CloudDesk", score=0.9, chunk_index=0)
        ]
        res = self.client.post(
            "/api/rag/search",
            json={"query": "үнэ", "top_k": 2},
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["count"], 1)
        self.assertIn("CloudDesk", res.json()["formatted"])


class ToolsRagTests(unittest.TestCase):
    @patch("agent.rag.search")
    @patch("agent.rag.is_enabled", return_value=True)
    def test_search_knowledge_tool(self, _enabled, search_mock):
        from agent import tools

        search_mock.return_value = [
            ChunkHit(source="x.md", content="answer", score=0.8, chunk_index=0)
        ]
        out = tools.search_knowledge("үнэ")
        self.assertIn("answer", out)


if __name__ == "__main__":
    unittest.main()
