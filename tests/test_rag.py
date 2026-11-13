"""Pruebas del RAG local (Bloque 3 - Oriana). Usan el backend hashing: sin red ni descargas."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from src.agent import rag


class ChunkingTests(unittest.TestCase):
    def test_windows_overlap_and_keep_source_fields(self):
        text = " ".join(f"w{i}" for i in range(300))
        record = {"document_id": "d1", "title": "T", "url": "http://x", "page_number": 3, "text": text,
                  "retrieved_at_utc": "2026-01-01", "version_note": "nota"}
        chunks = rag.split_into_chunks([record])
        self.assertGreaterEqual(len(chunks), 3)
        self.assertTrue(all(len(c["text"].split()) <= rag.CHUNK_WORDS for c in chunks))
        first, second = chunks[0]["text"].split(), chunks[1]["text"].split()
        self.assertEqual(first[rag.CHUNK_STEP:], second[:rag.CHUNK_WORDS - rag.CHUNK_STEP])
        self.assertEqual(chunks[0]["page_number"], 3)
        self.assertEqual(len({c["chunk_id"] for c in chunks}), len(chunks))
        covered = set(" ".join(c["text"] for c in chunks).split())
        self.assertEqual(covered, set(text.split()))

    def test_empty_text_produces_no_chunks_and_short_text_one(self):
        base = {"document_id": "d", "title": "T", "url": "u", "page_number": None}
        self.assertEqual(rag.split_into_chunks([{**base, "text": "   "}]), [])
        short = rag.split_into_chunks([{**base, "text": "una frase corta"}])
        self.assertEqual(len(short), 1)
        self.assertIsNone(short[0]["page_number"])


class IndexTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory()
        cls.dir = Path(cls._tmp.name)
        cls.meta = rag.build_index(index_dir=cls.dir, backend="hashing")
        cls.index = rag.load_index(index_dir=cls.dir)

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()

    def test_meta_records_backend_and_counts(self):
        self.assertEqual(self.meta["backend"], "hashing")
        self.assertEqual(self.index.embeddings.shape[0], len(self.index.chunks))
        self.assertEqual(self.index.meta["chunk_count"], len(self.index.chunks))

    def test_every_chunk_has_citable_source(self):
        for chunk in self.index.chunks:
            self.assertTrue(chunk["title"] and chunk["url"].startswith("http"))
            self.assertTrue(chunk["text"].strip())

    def test_bike_question_retrieves_bike_documents(self):
        found = self.index.search("horarios para entrar con bicicleta rígida al Metro", k=4)
        self.assertEqual(found["status"], "ok")
        docs = {r["document_id"] for r in found["results"]}
        self.assertTrue(docs & {"metro_bici", "metro_convivencia", "metro_usuarios"})
        scores = [r["score"] for r in found["results"]]
        self.assertEqual(scores, sorted(scores, reverse=True))

    def test_fare_question_retrieves_user_page(self):
        found = self.index.search("tarifa estudiantil integraciones 1 a 4 Cívica", k=3)
        self.assertEqual(found["results"][0]["document_id"], "metro_usuarios")

    def test_gibberish_has_no_relevant_results(self):
        found = self.index.search("xyzzy qwertyuiop zzzz", k=3)
        self.assertEqual(found["status"], "no_relevant_results")
        self.assertEqual(found["results"], [])

    def test_empty_query_is_error(self):
        self.assertEqual(self.index.search("   ")["status"], "error")

    def test_stale_index_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            other = Path(tmp) / "docs.jsonl"
            other.write_text(rag.DOCUMENTS_PATH.read_text(encoding="utf-8") + json.dumps(
                {"document_id": "x", "title": "x", "url": "http://x", "page_number": 1,
                 "text": "texto adicional " * 40}) + "\n", encoding="utf-8")
            with self.assertRaises(rag.RagError):
                rag.load_index(index_dir=self.dir, documents_path=other)

    def test_missing_index_has_helpful_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(rag.RagError) as ctx:
                rag.load_index(index_dir=Path(tmp))
            self.assertIn("build_index", str(ctx.exception))


class TokenizeTests(unittest.TestCase):
    def test_accents_stopwords_and_plurals(self):
        self.assertEqual(rag.tokenize("Los Horarios de la Bicicleta"), ["horario", "bicicleta"])


if __name__ == "__main__":
    unittest.main()
