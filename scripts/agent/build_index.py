"""Construye el índice RAG local a partir de corpus/documents.jsonl.

    python -m scripts.agent.build_index                       # auto: sentence-transformers si está, si no hashing
    python -m scripts.agent.build_index --backend sentence-transformers
    python -m scripts.agent.build_index --backend hashing     # sin descargas (léxico, no semántico)

El backend usado queda registrado en data/index/index.json; declara cuál usaste en el informe.
"""

from __future__ import annotations

import argparse
import json

from src.agent import rag


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--backend", choices=["auto", "sentence-transformers", "hashing"], default="auto")
    parser.add_argument("--model", default=None, help=f"Modelo de sentence-transformers (por defecto {rag.DEFAULT_ST_MODEL}).")
    args = parser.parse_args()
    meta = rag.build_index(backend=args.backend, model=args.model)
    summary = {key: meta[key] for key in ("backend", "model", "dim", "chunk_count", "min_score", "corpus_sha256")}
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"Índice guardado en {rag.INDEX_DIR}")


if __name__ == "__main__":
    main()
