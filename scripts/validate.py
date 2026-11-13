import json
from collections import Counter
from src.application.datasets import validate_test_pairs
from src.config import PROJECT_ROOT
from src.data import load_graph
from src.domain.geo import haversine_m
from src.infrastructure.provenance import file_hash
from src.infrastructure.json_store import write_json


def validate() -> dict:
    graph = load_graph()
    pairs = json.loads((PROJECT_ROOT / "data/test_pairs.json").read_text(encoding="utf-8"))
    validate_test_pairs(graph, pairs)
    source = graph.metadata["source"]
    raw = PROJECT_ROOT / "data/raw/medellin_centro.osm"
    if file_hash(raw) != source["sha256"]:
        raise ValueError("La copia OSM no coincide con los metadatos del grafo.")
    for edge in graph.edges:
        expected = haversine_m(graph.nodes[edge.origin], graph.nodes[edge.destination])
        if abs(expected - edge.distance_m) > 1e-7:
            raise ValueError(f"Distancia incoherente: {edge.id}")
    manifest = json.loads((PROJECT_ROOT / "corpus/manifest.json").read_text(encoding="utf-8"))
    if len(manifest) < 3:
        raise ValueError("El corpus debe contener al menos tres documentos.")
    for doc in manifest:
        if file_hash(PROJECT_ROOT/doc["raw_path"]) != doc["sha256"]:
            raise ValueError(f"Corpus original alterado: {doc['id']}")
        if file_hash(PROJECT_ROOT/doc["text_path"]) != doc["text_sha256"]:
            raise ValueError(f"Texto extraído alterado: {doc['id']}")
    records = [json.loads(line) for line in (PROJECT_ROOT / "corpus/documents.jsonl").read_text(encoding="utf-8").splitlines()]
    if not records or any(not row["text"].strip() or not row["url"].startswith("https://") for row in records):
        raise ValueError("Registros del corpus incompletos.")
    # Comparar los registros consumibles por Oriana con la extracción individual.
    for doc in manifest:
        selected = [row for row in records if row["document_id"] == doc["id"]]
        if len(selected) != doc["nonempty_pages"] or any(row["url"] != doc["url"] for row in selected):
            raise ValueError(f"Registros incoherentes: {doc['id']}")
        reconstructed = "\n\n".join(f"[Página {row['page_number']}]\n{row['text']}" if row['page_number'] else row['text'] for row in selected)+"\n"
        if reconstructed != (PROJECT_ROOT/doc["text_path"]).read_text(encoding="utf-8"):
            raise ValueError(f"documents.jsonl difiere del texto: {doc['id']}")
    lengths = [edge.distance_m for edge in graph.edges]
    return {"status": "ok", "nodes": len(graph.nodes), "directed_edges": len(graph.edges),
            "test_pairs": len(pairs), "corpus_documents": len(manifest), "corpus_records": len(records),
            "distance_min_m": min(lengths), "distance_max_m": max(lengths),
            "distance_mean_m": sum(lengths)/len(lengths),
            "directed_edges_by_highway": dict(sorted(Counter(edge.highway for edge in graph.edges).items())),
            "note": "Validación de datos del bloque 1. No evalúa A*, Dijkstra, LLM ni dashboard."}


def main():
    report = validate()
    write_json(PROJECT_ROOT / "results/data_validation.json", report)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
