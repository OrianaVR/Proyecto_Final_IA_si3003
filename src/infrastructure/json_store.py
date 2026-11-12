import json
from dataclasses import asdict
from pathlib import Path
from src.domain.models import DataValidationError, Edge, Graph, Node


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False)+"\n",
                    encoding="utf-8")


class JsonGraphRepository:
    def load(self, directory: Path) -> Graph:
        try:
            nodes_payload = json.loads((directory / "nodes.json").read_text(encoding="utf-8"))
            edges_payload = json.loads((directory / "edges.json").read_text(encoding="utf-8"))
            metadata = json.loads((directory / "metadata.json").read_text(encoding="utf-8"))
            if metadata.get("schema_version") != 1:
                raise DataValidationError("Versión de esquema no soportada.")
            nodes_list = [Node(**row) for row in nodes_payload]
            nodes = {node.id: node for node in nodes_list}
            if len(nodes) != len(nodes_list):
                raise DataValidationError("Nodos duplicados en nodes.json.")
            return Graph(nodes, tuple(Edge(**row) for row in edges_payload), metadata)
        except (OSError, ValueError, TypeError, KeyError) as error:
            raise DataValidationError(f"No se pudo cargar el grafo en {directory}: {error}") from error

    def save(self, graph: Graph, directory: Path) -> None:
        write_json(directory / "nodes.json", [asdict(graph.nodes[key]) for key in sorted(graph.nodes)])
        write_json(directory / "edges.json", [asdict(edge) for edge in graph.edges])
        write_json(directory / "metadata.json", graph.metadata)
