"""RAG local para el Bloque 3 (Oriana): fragmentación, embeddings, índice y búsqueda.

Flujo:
    corpus/documents.jsonl --chunk--> fragmentos --embed--> data/index/ (embeddings.npy + index.json)
    pregunta --embed--> similitud coseno contra el índice --> top-k fragmentos con su fuente

Backends de embeddings (se guarda cuál se usó dentro del índice):
- ``sentence-transformers``: modelo neuronal multilingüe, local (recomendado para la entrega).
- ``hashing``: TF-IDF con hashing, solo numpy y stdlib. Sirve como respaldo sin descargas y para
  las pruebas automáticas. Es léxico, no semántico: debe declararse así en el informe si se usa.
- ``auto``: intenta sentence-transformers y, si no está instalado, usa hashing avisando por stderr.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import sys
import unicodedata
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Sequence

import numpy as np

from src.config import PROJECT_ROOT

DOCUMENTS_PATH = PROJECT_ROOT / "corpus/documents.jsonl"
INDEX_DIR = PROJECT_ROOT / "data/index"

DEFAULT_ST_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"
CHUNK_WORDS = 140
CHUNK_STEP = 100  # solapamiento de 40 palabras entre fragmentos consecutivos
MIN_TAIL_WORDS = 25
HASH_DIM = 4096

# Umbral mínimo de similitud coseno para considerar relevante un fragmento.
# Depende del backend; se guarda en el índice para que consulta y construcción coincidan.
DEFAULT_MIN_SCORE = {"hashing": 0.07, "sentence-transformers": 0.30}


class RagError(RuntimeError):
    """Problema con el índice o el corpus (falta el índice, backend no disponible, etc.)."""


# --------------------------------------------------------------------------- texto

def _strip_accents(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch))


_STOPWORDS = frozenset(_strip_accents(w) for w in """
de la el en y a los las del se que por un una con para al lo como mas o su sus es son ser si no ni
este esta estos estas ese esa pero tambien entre sobre sin muy ya le les mi tu te me que cual cuales
cuanto cuanta cuantos hay puede pueden debe deben tiene tienen""".split())


def tokenize(text: str) -> list[str]:
    """Minúsculas, sin tildes, sin stopwords y con singularización básica ('horarios' -> 'horario')."""
    words = re.findall(r"[a-z0-9]+", _strip_accents(text.lower()))
    tokens = []
    for word in words:
        if word in _STOPWORDS or (len(word) < 2 and not word.isdigit()):
            continue
        if len(word) > 4 and word.endswith("s"):
            word = word[:-1]
        tokens.append(word)
    return tokens


def split_into_chunks(records: Iterable[dict[str, Any]], words: int = CHUNK_WORDS,
                      step: int = CHUNK_STEP) -> list[dict[str, Any]]:
    """Divide cada registro (página de un documento) en ventanas de palabras con solapamiento."""
    chunks: list[dict[str, Any]] = []
    for record in records:
        tokens = record["text"].split()
        if not tokens:
            continue
        starts = list(range(0, len(tokens), step)) or [0]
        for index, start in enumerate(starts):
            window = tokens[start:start + words]
            if index > 0 and len(window) < MIN_TAIL_WORDS:
                break  # cola demasiado corta: ya quedó cubierta por el solapamiento anterior
            page = record.get("page_number")
            chunks.append({
                "chunk_id": f"{record['document_id']}:p{page or 0}:c{index}",
                "document_id": record["document_id"],
                "title": record["title"],
                "url": record["url"],
                "page_number": page,
                "text": " ".join(window),
                "retrieved_at_utc": record.get("retrieved_at_utc"),
                "version_note": record.get("version_note", ""),
            })
            if start + words >= len(tokens):
                break
    return chunks


# --------------------------------------------------------------------------- embedders

class HashingTfidfEmbedder:
    """TF-IDF con hashing de unigramas y bigramas. Determinista y sin dependencias externas."""

    backend = "hashing"

    def __init__(self, dim: int = HASH_DIM, idf: Sequence[float] | None = None):
        self.dim = dim
        self.model = f"hashing-tfidf-{dim}"
        self.idf = np.asarray(idf, dtype=np.float32) if idf is not None else np.ones(dim, np.float32)

    @staticmethod
    def _bucket(feature: str, dim: int) -> int:
        digest = hashlib.blake2b(feature.encode("utf-8"), digest_size=8).digest()
        return int.from_bytes(digest, "big") % dim

    def _counts(self, text: str) -> dict[int, int]:
        tokens = tokenize(text)
        features = tokens + [f"{a}_{b}" for a, b in zip(tokens, tokens[1:])]
        counts: dict[int, int] = {}
        for feature in features:
            bucket = self._bucket(feature, self.dim)
            counts[bucket] = counts.get(bucket, 0) + 1
        return counts

    def fit(self, texts: Sequence[str]) -> "HashingTfidfEmbedder":
        df = np.zeros(self.dim, dtype=np.float32)
        for text in texts:
            for bucket in self._counts(text):
                df[bucket] += 1
        n = len(texts)
        self.idf = (np.log((1 + n) / (1 + df)) + 1).astype(np.float32)
        return self

    def encode(self, texts: Sequence[str]) -> np.ndarray:
        matrix = np.zeros((len(texts), self.dim), dtype=np.float32)
        for row, text in enumerate(texts):
            for bucket, count in self._counts(text).items():
                matrix[row, bucket] = (1 + math.log(count)) * self.idf[bucket]
        norms = np.linalg.norm(matrix, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        return matrix / norms

    def state(self) -> dict[str, Any]:
        return {"dim": self.dim, "idf": [round(float(x), 6) for x in self.idf]}


class SentenceTransformerEmbedder:
    """Embeddings neuronales locales con sentence-transformers (modelo multilingüe)."""

    backend = "sentence-transformers"

    def __init__(self, model_name: str = DEFAULT_ST_MODEL):
        self.model = model_name
        self._encoder = None

    def _load(self):
        if self._encoder is None:
            try:
                from sentence_transformers import SentenceTransformer
            except ImportError as exc:
                raise RagError(
                    "Falta sentence-transformers. Instálalo con 'pip install sentence-transformers' "
                    "o reconstruye el índice con --backend hashing.") from exc
            self._encoder = SentenceTransformer(self.model)
        return self._encoder

    def fit(self, texts: Sequence[str]) -> "SentenceTransformerEmbedder":
        return self  # no necesita ajuste

    def encode(self, texts: Sequence[str]) -> np.ndarray:
        vectors = self._load().encode(list(texts), normalize_embeddings=True, show_progress_bar=False)
        return np.asarray(vectors, dtype=np.float32)

    def state(self) -> dict[str, Any]:
        return {}


def make_embedder(backend: str = "auto", model: str | None = None):
    """Crea un embedder. 'auto' prefiere sentence-transformers y cae a hashing si no está."""
    if backend == "hashing":
        return HashingTfidfEmbedder()
    if backend == "sentence-transformers":
        embedder = SentenceTransformerEmbedder(model or DEFAULT_ST_MODEL)
        embedder._load()  # falla pronto si la dependencia o el modelo no están disponibles
        return embedder
    if backend == "auto":
        try:
            return make_embedder("sentence-transformers", model)
        except Exception as exc:  # ImportError, sin red para descargar el modelo, etc.
            print(f"[rag] sentence-transformers no disponible ({type(exc).__name__}); "
                  "usando respaldo 'hashing' (léxico, no semántico).", file=sys.stderr)
            return HashingTfidfEmbedder()
    raise RagError(f"Backend de embeddings desconocido: '{backend}'.")


def _embedder_from_meta(meta: dict[str, Any]):
    if meta["backend"] == "hashing":
        state = meta.get("embedder_state", {})
        return HashingTfidfEmbedder(dim=state.get("dim", HASH_DIM), idf=state.get("idf"))
    if meta["backend"] == "sentence-transformers":
        return SentenceTransformerEmbedder(meta["model"])
    raise RagError(f"El índice usa un backend desconocido: {meta['backend']}")


# --------------------------------------------------------------------------- índice

def _sha256(path: Path) -> str:
    """Hash del corpus insensible a saltos de línea (Windows CRLF vs Linux/macOS LF)."""
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def load_records(path: Path = DOCUMENTS_PATH) -> list[dict[str, Any]]:
    if not path.exists():
        raise RagError(f"No existe el corpus: {path}. Ejecuta primero scripts.prepare_corpus.")
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def build_index(documents_path: Path = DOCUMENTS_PATH, index_dir: Path = INDEX_DIR,
                backend: str = "auto", model: str | None = None) -> dict[str, Any]:
    """Construye el índice local y lo guarda en ``index_dir``. Devuelve los metadatos."""
    chunks = split_into_chunks(load_records(documents_path))
    if not chunks:
        raise RagError("El corpus no produjo fragmentos.")
    embedder = make_embedder(backend, model)
    texts = [chunk["text"] for chunk in chunks]
    embedder.fit(texts)
    embeddings = embedder.encode(texts)

    meta = {
        "schema_version": 1,
        "backend": embedder.backend,
        "model": embedder.model,
        "dim": int(embeddings.shape[1]),
        "chunk_count": len(chunks),
        "chunk_words": CHUNK_WORDS,
        "chunk_overlap_words": CHUNK_WORDS - CHUNK_STEP,
        "min_score": DEFAULT_MIN_SCORE[embedder.backend],
        "corpus_sha256": _sha256(documents_path),
        "built_at_utc": datetime.now(timezone.utc).isoformat(),
        "embedder_state": embedder.state(),
    }
    index_dir.mkdir(parents=True, exist_ok=True)
    np.save(index_dir / "embeddings.npy", embeddings)
    (index_dir / "index.json").write_text(
        json.dumps({"meta": meta, "chunks": chunks}, ensure_ascii=False, indent=1), encoding="utf-8")
    return meta


@dataclass
class RagIndex:
    chunks: list[dict[str, Any]]
    embeddings: np.ndarray
    embedder: Any
    meta: dict[str, Any]

    def search(self, query: str, k: int = 4, min_score: float | None = None) -> dict[str, Any]:
        """Top-k por similitud coseno. Descarta fragmentos por debajo del umbral."""
        query = (query or "").strip()
        if not query:
            return {"status": "error", "results": [], "max_score": None, "error": "Consulta vacía."}
        threshold = self.meta.get("min_score", 0.0) if min_score is None else min_score
        scores = self.embeddings @ self.embedder.encode([query])[0]
        order = np.argsort(-scores)[:max(1, k)]
        results = []
        for position in order:
            score = float(scores[position])
            if score < threshold:
                continue
            chunk = self.chunks[int(position)]
            results.append({**chunk, "score": round(score, 4)})
        return {
            "status": "ok" if results else "no_relevant_results",
            "results": results,
            "max_score": round(float(scores[order[0]]), 4),
            "backend": self.meta["backend"],
            "error": None,
        }


def load_index(index_dir: Path = INDEX_DIR, documents_path: Path = DOCUMENTS_PATH) -> RagIndex:
    """Carga el índice local. Falla con un mensaje claro si falta o quedó desactualizado."""
    index_file, vectors_file = index_dir / "index.json", index_dir / "embeddings.npy"
    if not index_file.exists() or not vectors_file.exists():
        raise RagError("No existe el índice local. Ejecuta: python -m scripts.agent.build_index")
    payload = json.loads(index_file.read_text(encoding="utf-8"))
    meta = payload["meta"]
    if documents_path.exists() and meta.get("corpus_sha256") != _sha256(documents_path):
        raise RagError("El índice no corresponde al corpus actual. Ejecuta: python -m scripts.agent.build_index")
    embeddings = np.load(vectors_file)
    if embeddings.shape[0] != len(payload["chunks"]):
        raise RagError("El índice está corrupto (filas distintas a fragmentos). Reconstrúyelo.")
    return RagIndex(payload["chunks"], embeddings, _embedder_from_meta(meta), meta)
