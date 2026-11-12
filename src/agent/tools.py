"""Herramientas que el agent LLM puede invocar (Bloque 3 - Oriana).

Todas calculan resultados reales sobre el código de los bloques anteriores:
- plan_route         -> src.routing.plan_route (A* / Dijkstra propios, Bloque 2)
- get_route_metrics  -> src.routing.get_route_metrics (compara ambos algoritmos, Bloque 2)
- find_nodes         -> consulta el grafo cargado por src.data.load_graph (Bloque 1)
- search_documents   -> RAG local sobre el corpus del Metro (src.rag)

``run_tool`` devuelve dos vistas del resultado:
- ``full``: resultado completo (incluye el camino de nodos) para el ``tool_trace`` y el dashboard.
- ``view``: versión compacta que se le entrega al modelo (sin listas largas de nodos).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from src.agent import rag
from src.data import load_graph
from src.domain.models import Graph
from src.routing import get_route_metrics as _get_route_metrics
from src.routing import plan_route as _plan_route

MAX_DOC_RESULTS = 6

TOOL_SCHEMAS: list[dict[str, Any]] = [
    {"type": "function", "function": {
        "name": "plan_route",
        "description": (
            "Calcula la ruta de menor distancia entre dos nodos de la red vial del centro de Medellín "
            "con A* o Dijkstra. Devuelve estado, distancia en metros, nodos expandidos, tiempo y las "
            "calles recorridas. Los nodos se identifican por su id de OpenStreetMap (texto numérico)."),
        "parameters": {"type": "object", "properties": {
            "origin": {"type": "string", "description": "Id del nodo de origen."},
            "destination": {"type": "string", "description": "Id del nodo de destino."},
            "algorithm": {"type": "string", "enum": ["astar", "dijkstra"],
                          "description": "Algoritmo; por defecto astar."}},
            "required": ["origin", "destination"]}}},
    {"type": "function", "function": {
        "name": "get_route_metrics",
        "description": (
            "Ejecuta A* y Dijkstra sobre el mismo par de nodos y compara distancia óptima, nodos "
            "expandidos y tiempo de ejecución de ambos."),
        "parameters": {"type": "object", "properties": {
            "origin": {"type": "string", "description": "Id del nodo de origen."},
            "destination": {"type": "string", "description": "Id del nodo de destino."}},
            "required": ["origin", "destination"]}}},
    {"type": "function", "function": {
        "name": "find_nodes",
        "description": (
            "Busca ids de nodos por nombre de calle. Con 'street' y 'cross_street' devuelve los nodos "
            "donde ambas calles se cruzan (intersección). Con solo 'street' devuelve una muestra de "
            "nodos de esa calle. Úsala cuando la persona nombre calles en vez de ids."),
        "parameters": {"type": "object", "properties": {
            "street": {"type": "string", "description": "Nombre de la calle, p. ej. 'Calle 50'."},
            "cross_street": {"type": "string", "description": "Calle que cruza (opcional)."}},
            "required": ["street"]}}},
    {"type": "function", "function": {
        "name": "search_documents",
        "description": (
            "Busca fragmentos relevantes en los documentos del Metro de Medellín (reglamento del "
            "usuario, tarifas, horarios y condiciones para bicicletas). Devuelve pasajes con un "
            "source_id para citar. Úsala para toda pregunta sobre el Metro."),
        "parameters": {"type": "object", "properties": {
            "query": {"type": "string", "description": "Consulta en español con las palabras clave."},
            "k": {"type": "integer", "minimum": 1, "maximum": MAX_DOC_RESULTS,
                  "description": "Cantidad de fragmentos (por defecto 4)."}},
            "required": ["query"]}}},
]

TOOL_NAMES = tuple(schema["function"]["name"] for schema in TOOL_SCHEMAS)


@dataclass
class ToolOutcome:
    full: dict[str, Any]   # resultado completo para trazas y dashboard
    view: dict[str, Any]   # resultado compacto para el modelo
    ok: bool               # False si la herramienta devolvió un error


# ------------------------------------------------------------------ estado compartido

_GRAPH: Graph | None = None
_INDEX: rag.RagIndex | None = None
_STREET_CACHE: dict[int, dict[str, tuple[str, set[str]]]] = {}


def get_graph() -> Graph:
    global _GRAPH
    if _GRAPH is None:
        _GRAPH = load_graph()
    return _GRAPH


def get_index() -> rag.RagIndex:
    global _INDEX
    if _INDEX is None:
        _INDEX = rag.load_index()
    return _INDEX


def reset_cache() -> None:
    """Olvida el grafo y el índice cargados (útil en pruebas)."""
    global _GRAPH, _INDEX
    _GRAPH = _INDEX = None
    _STREET_CACHE.clear()


# ------------------------------------------------------------------ utilidades de grafo

def _normalize(text: str) -> str:
    return " ".join(rag._strip_accents(str(text)).lower().split())


def _street_nodes(graph: Graph) -> dict[str, tuple[str, set[str]]]:
    """Calle normalizada -> (nombre original, ids de nodos tocados por sus aristas)."""
    cached = _STREET_CACHE.get(id(graph))
    if cached is None:
        cached = {}
        for edge in graph.edges:
            if not edge.name:
                continue
            _, nodes = cached.setdefault(_normalize(edge.name), (edge.name, set()))
            nodes.update((edge.origin, edge.destination))
        _STREET_CACHE[id(graph)] = cached
    return cached


def _streets_along(path: list[str], graph: Graph) -> list[str]:
    """Nombres de calle en orden de recorrido, sin repetir consecutivos ni aristas sin nombre."""
    names: list[str] = []
    for a, b in zip(path, path[1:]):
        edges = [e for e in graph.adjacency.get(a, ()) if e.destination == b]
        if not edges:
            continue
        name = min(edges, key=lambda e: e.distance_m).name
        if name and (not names or names[-1] != name):
            names.append(name)
    return names


def _as_id(value: Any) -> str:
    return str(value).strip()


# ------------------------------------------------------------------ implementaciones

def _plan_route_tool(args: dict[str, Any], graph: Graph) -> ToolOutcome:
    origin, destination = _as_id(args.get("origin", "")), _as_id(args.get("destination", ""))
    algorithm = str(args.get("algorithm") or "astar").lower().strip()
    result = _plan_route(origin, destination, algorithm=algorithm, graph=graph)
    full = {**result, "algorithm": algorithm, "origin": origin, "destination": destination}
    ok = result["status"] == "ok"
    view = {"status": result["status"], "algorithm": algorithm, "origin": origin,
            "destination": destination, "distance_m": result["distance_m"],
            "expanded_nodes": result["expanded_nodes"], "elapsed_ms": result["elapsed_ms"],
            "error": result["error"]}
    if ok:
        view["path_node_count"] = len(result["path"])
        view["streets"] = _streets_along(result["path"], graph)
    return ToolOutcome(full, view, ok)


def _get_route_metrics_tool(args: dict[str, Any], graph: Graph) -> ToolOutcome:
    origin, destination = _as_id(args.get("origin", "")), _as_id(args.get("destination", ""))
    result = _get_route_metrics(origin, destination, graph=graph)
    ok = result["astar"]["status"] == "ok" and result["dijkstra"]["status"] == "ok"

    def brief(run: dict[str, Any]) -> dict[str, Any]:
        return {key: run[key] for key in ("status", "distance_m", "expanded_nodes", "elapsed_ms", "error")}

    view = {"origin": origin, "destination": destination, "status": "ok" if ok else "error",
            "astar": brief(result["astar"]), "dijkstra": brief(result["dijkstra"]),
            "metrics": result["metrics"]}
    return ToolOutcome(result, view, ok)


def _find_nodes_tool(args: dict[str, Any], graph: Graph, limit: int = 8) -> ToolOutcome:
    streets = _street_nodes(graph)
    street, cross = str(args.get("street") or "").strip(), str(args.get("cross_street") or "").strip()
    known = sorted(name for name, _ in streets.values())

    def resolve(query: str) -> tuple[str, set[str]] | None:
        wanted = _normalize(query)
        if wanted in streets:
            return streets[wanted]
        partial = [value for key, value in streets.items() if wanted and wanted in key]
        if not partial:
            return None
        return " / ".join(name for name, _ in partial), set().union(*(nodes for _, nodes in partial))

    first = resolve(street)
    if first is None:
        error = f"No hay una calle llamada '{street}' en el extracto."
        full = {"status": "error", "error": error, "available_streets": known}
        return ToolOutcome(full, full, False)

    if cross:
        second = resolve(cross)
        if second is None:
            error = f"No hay una calle llamada '{cross}' en el extracto."
            full = {"status": "error", "error": error, "available_streets": known}
            return ToolOutcome(full, full, False)
        shared = sorted(first[1] & second[1])
        if not shared:
            full = {"status": "error", "error": f"{first[0]} y {second[0]} no se cruzan en el extracto.",
                    "available_streets": known}
            return ToolOutcome(full, full, False)
        label, node_ids = f"{first[0]} con {second[0]}", shared
    else:
        label, node_ids = first[0], sorted(first[1])

    step = max(1, len(node_ids) // limit)
    sample = node_ids[::step][:limit]
    matches = [{"node_id": nid, "latitude": graph.nodes[nid].latitude,
                "longitude": graph.nodes[nid].longitude} for nid in sample]
    full = {"status": "ok", "query": label, "total_nodes": len(node_ids), "matches": matches,
            "note": "Con intersección, cualquiera de los nodos sirve como punto." if cross else
                    "Es solo una muestra de los nodos de la calle."}
    return ToolOutcome(full, full, True)


def _search_documents_tool(args: dict[str, Any]) -> ToolOutcome:
    query = str(args.get("query") or "").strip()
    try:
        k = int(args.get("k") or 4)
    except (TypeError, ValueError):
        k = 4
    k = max(1, min(k, MAX_DOC_RESULTS))
    try:
        found = get_index().search(query, k=k)
    except rag.RagError as exc:
        full = {"status": "error", "results": [], "error": str(exc)}
        return ToolOutcome(full, full, False)
    ok = found["status"] != "error"
    return ToolOutcome(found, found, ok)


# ------------------------------------------------------------------ despacho

def run_tool(name: str, arguments: dict[str, Any] | str | None) -> ToolOutcome:
    """Ejecuta una herramienta por nombre. Nunca lanza: los fallos salen como resultado de error."""
    if isinstance(arguments, str):
        try:
            arguments = json.loads(arguments) if arguments.strip() else {}
        except json.JSONDecodeError:
            return _error(f"Los argumentos de '{name}' no son un JSON válido.")
    if arguments is None:
        arguments = {}
    if not isinstance(arguments, dict):
        return _error(f"Los argumentos de '{name}' deben ser un objeto JSON.")
    if name not in TOOL_NAMES:
        return _error(f"Herramienta desconocida: '{name}'. Disponibles: {', '.join(TOOL_NAMES)}.")

    required = {"plan_route": ("origin", "destination"), "get_route_metrics": ("origin", "destination"),
                "find_nodes": ("street",), "search_documents": ("query",)}[name]
    missing = [key for key in required if not str(arguments.get(key, "")).strip()]
    if missing:
        return _error(f"Faltan argumentos obligatorios en '{name}': {', '.join(missing)}.")

    try:
        if name == "search_documents":
            return _search_documents_tool(arguments)
        graph = get_graph()
        if name == "plan_route":
            return _plan_route_tool(arguments, graph)
        if name == "get_route_metrics":
            return _get_route_metrics_tool(arguments, graph)
        return _find_nodes_tool(arguments, graph)
    except Exception as exc:  # defensa final: el loop del agent no debe romperse por una herramienta
        return _error(f"Falla interna en '{name}': {type(exc).__name__}: {exc}")


def _error(message: str) -> ToolOutcome:
    full = {"status": "error", "error": message}
    return ToolOutcome(full, full, False)
