from collections import deque
from pathlib import Path
from .ports import GraphReader
from src.domain.models import DataValidationError, Graph


def read_graph(reader: GraphReader, directory: Path) -> Graph:
    return reader.load(directory)


def reachable_nodes(graph: Graph, origin: str) -> set[str]:
    """BFS de conectividad para escoger casos válidos, sin optimizar rutas."""
    if origin not in graph.nodes:
        raise DataValidationError(f"Origen desconocido: {origin}")
    seen = {origin}
    pending = deque([origin])
    while pending:
        for edge in graph.adjacency[pending.popleft()]:
            if edge.destination not in seen:
                seen.add(edge.destination)
                pending.append(edge.destination)
    return seen


def make_test_pairs(graph: Graph, count: int = 10) -> list[dict]:
    """Casos distintos y reproducibles, con orígenes distribuidos en el grafo."""
    if count < 1:
        raise DataValidationError("count debe ser positivo.")
    ids = sorted(graph.nodes)
    origins = ids[::max(1, len(ids) // count)] + ids
    result = []
    used = set()
    for origin in origins:
        reachable = reachable_nodes(graph, origin) - {origin}
        destinations = sorted(reachable)
        if destinations:
            offset = ((len(result) + 1) * len(destinations) // (count + 1)) % len(destinations)
            destinations = destinations[offset:] + destinations[:offset]
        for destination in destinations:
            pair = (origin, destination)
            if pair not in used:
                result.append({"id": f"pair_{len(result)+1:02d}",
                               "origin": origin, "destination": destination})
                used.add(pair)
                break
        if len(result) == count:
            return result
    raise DataValidationError(f"No hay {count} pares distintos alcanzables.")


def validate_test_pairs(graph: Graph, pairs: list[dict]) -> None:
    if len(pairs) != 10:
        raise DataValidationError("Se requieren exactamente 10 pares de prueba.")
    seen = set()
    for pair in pairs:
        origin, destination = pair["origin"], pair["destination"]
        if origin == destination or (origin, destination) in seen:
            raise DataValidationError("Par repetido o trivial.")
        if destination not in graph.nodes or destination not in reachable_nodes(graph, origin):
            raise DataValidationError(f"Par no alcanzable: {pair}")
        seen.add((origin, destination))
