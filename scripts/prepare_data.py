import argparse
import json
from pathlib import Path
from src.application.datasets import make_test_pairs, validate_test_pairs
from src.config import DEFAULT_BBOX, PROJECT_ROOT, RAW_GRAPH
from src.infrastructure.http_client import download
from src.infrastructure.json_store import JsonGraphRepository, write_json
from src.infrastructure.osm import build_graph, validate_bbox
from src.infrastructure.provenance import file_hash, record_download


def prepare(raw_path: Path, bbox: tuple, output: Path, pairs_path: Path):
    sidecar = raw_path.with_suffix(raw_path.suffix + ".source.json")
    if not sidecar.exists():
        raise ValueError("Falta procedencia. Descargue con --download o registre la URL del archivo importado.")
    source = json.loads(sidecar.read_text(encoding="utf-8"))
    if source["sha256"] != file_hash(raw_path):
        raise ValueError("El hash del OSM no coincide con su registro de procedencia.")
    if list(bbox) != source.get("bbox_wsen", list(DEFAULT_BBOX)):
        raise ValueError("La bbox no coincide con la registrada en el archivo original.")
    source.update({"name": "OpenStreetMap contributors", "license": "ODbL 1.0",
                   "attribution_url": "https://www.openstreetmap.org/copyright"})
    graph = build_graph(raw_path, bbox, source)
    pairs = make_test_pairs(graph)
    validate_test_pairs(graph, pairs)
    JsonGraphRepository().save(graph, output)
    write_json(pairs_path, pairs)
    return graph


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--download", action="store_true", help="Actualizar extracto por HTTP; por defecto usa copia local.")
    parser.add_argument("--bbox", nargs=4, type=float, default=None,
                        metavar=("WEST", "SOUTH", "EAST", "NORTH"))
    args = parser.parse_args()
    previous_source = RAW_GRAPH.with_suffix(".osm.source.json")
    saved_bbox = DEFAULT_BBOX
    if previous_source.exists():
        saved_bbox = json.loads(previous_source.read_text(encoding="utf-8")).get("bbox_wsen", DEFAULT_BBOX)
    bbox = tuple(args.bbox or (DEFAULT_BBOX if args.download else saved_bbox))
    validate_bbox(bbox)
    if args.bbox and bbox != tuple(saved_bbox) and not args.download:
        parser.error("Cambiar bbox requiere --download para mantener procedencia coherente.")
    if args.download:
        url = "https://api.openstreetmap.org/api/0.6/map?bbox=" + ",".join(map(str, bbox))
        download(url, RAW_GRAPH)
        record = record_download(RAW_GRAPH, url)
        record["bbox_wsen"] = list(bbox)
        write_json(previous_source, record)
    graph = prepare(RAW_GRAPH, bbox, PROJECT_ROOT / "data/processed", PROJECT_ROOT / "data/test_pairs.json")
    print(f"Grafo preparado: {len(graph.nodes)} nodos, {len(graph.edges)} aristas dirigidas y 10 pares válidos.")


if __name__ == "__main__":
    main()
