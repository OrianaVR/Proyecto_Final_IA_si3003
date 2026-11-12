"""Módulo de planificación de rutas y algoritmos de búsqueda para el Bloque 2 (Wendy).

Implementa los algoritmos clásicos de camino más corto:
- Dijkstra (búsqueda de costo uniforme con cola de prioridad)
- A* (búsqueda informada usando la heurística admisible de Haversine)

Reglas y definiciones del algoritmo:
- No se utilizan librerías externas de grafos (como NetworkX o OSMnx).
- Se utiliza `heapq` de la biblioteca estándar para la cola de prioridad.
- Definición de "nodo expandido":
  Se contabiliza un nodo como "expandido" estrictamente en el instante en que es
  extraído (popped) de la cola de prioridad (`heapq.heappop`) y se procesan sus
  aristas salientes para explorar a sus vecinos. No se cuenta cuando es
  descartado por obsolescencia (si ya se conocía una distancia menor) ni al ser
  simplemente encolado/generado.
"""

from __future__ import annotations

import heapq
import time
from typing import Any, Mapping

from src.data import load_graph
from src.domain.geo import haversine_m
from src.domain.models import Edge, Graph, Node


def plan_route(
    origin: str,
    destination: str,
    algorithm: str = "astar",
    graph: Graph | None = None,
) -> dict[str, Any]:
    """Calcula la ruta óptima entre origin y destination usando el algoritmo especificado.

    Parámetros
    ----------
    origin : str
        Identificador del nodo de origen.
    destination : str
        Identificador del nodo de destino.
    algorithm : str, optional
        Algoritmo a utilizar: "astar" o "dijkstra". Por defecto "astar".
    graph : Graph, optional
        Instancia del grafo vial. Si es None, se carga usando load_graph().

    Retorna
    -------
    dict[str, Any]
        Diccionario con las llaves exactas:
        - status: "ok" o "error"
        - path: lista de ids de nodos de la ruta óptima (ej: ["A", "B", "C"]) o []
        - distance_m: distancia total en metros (float) o None
        - expanded_nodes: número entero de nodos expandidos
        - elapsed_ms: tiempo de ejecución en milisegundos
        - error: mensaje de error descriptivo o None
    """
    start_time = time.perf_counter()

    algo = algorithm.lower().strip()
    if algo not in ("astar", "dijkstra"):
        elapsed_ms = (time.perf_counter() - start_time) * 1000.0
        return {
            "status": "error",
            "path": [],
            "distance_m": None,
            "expanded_nodes": 0,
            "elapsed_ms": round(elapsed_ms, 4),
            "error": f"Algoritmo no soportado: '{algorithm}'. Debe ser 'astar' o 'dijkstra'.",
        }

    if graph is None:
        graph = load_graph()

    nodes: Mapping[str, Node] = graph.nodes
    adjacency: dict[str, tuple[Edge, ...]] = graph.adjacency

    if origin not in nodes:
        elapsed_ms = (time.perf_counter() - start_time) * 1000.0
        return {
            "status": "error",
            "path": [],
            "distance_m": None,
            "expanded_nodes": 0,
            "elapsed_ms": round(elapsed_ms, 4),
            "error": f"Nodo de origen no existe en el grafo: '{origin}'.",
        }

    if destination not in nodes:
        elapsed_ms = (time.perf_counter() - start_time) * 1000.0
        return {
            "status": "error",
            "path": [],
            "distance_m": None,
            "expanded_nodes": 0,
            "elapsed_ms": round(elapsed_ms, 4),
            "error": f"Nodo de destino no existe en el grafo: '{destination}'.",
        }

    # Caso especial: origen == destino
    if origin == destination:
        elapsed_ms = (time.perf_counter() - start_time) * 1000.0
        return {
            "status": "ok",
            "path": [origin],
            "distance_m": 0.0,
            "expanded_nodes": 0,
            "elapsed_ms": round(elapsed_ms, 4),
            "error": None,
        }

    dest_node = nodes[destination]
    is_astar = algo == "astar"

    # Estructuras de búsqueda
    # g_score almacena el menor costo g(n) conocido hasta el nodo n desde el origen
    g_score: dict[str, float] = {origin: 0.0}
    # predecessor para reconstruir el camino
    predecessor: dict[str, str] = {}

    # Cola de prioridad: almacena tuplas (f_score, counter, current_node_id)
    # El counter garantiza orden FIFO en caso de empates en f_score y evita comparaciones de nodos.
    entry_counter = 0
    initial_h = haversine_m(nodes[origin], dest_node) if is_astar else 0.0
    priority_queue: list[tuple[float, int, str]] = [(initial_h, entry_counter, origin)]

    expanded_nodes = 0
    visited: set[str] = set()

    found = False

    while priority_queue:
        current_f, _, current = heapq.heappop(priority_queue)

        # Si ya fue expandido con una ruta más corta, ignorar esta entrada obsoleta
        if current in visited:
            continue

        # Al extraer el nodo de destino con menor f_score, la ruta es óptima
        if current == destination:
            found = True
            break

        # Marcar como expandido
        visited.add(current)
        expanded_nodes += 1

        current_g = g_score[current]

        # Explorar vecinos
        neighbors = adjacency.get(current, ())
        for edge in neighbors:
            neighbor = edge.destination
            if neighbor in visited:
                continue

            tentative_g = current_g + edge.distance_m

            if tentative_g < g_score.get(neighbor, float("inf")):
                g_score[neighbor] = tentative_g
                predecessor[neighbor] = current
                entry_counter += 1

                h_val = haversine_m(nodes[neighbor], dest_node) if is_astar else 0.0
                f_val = tentative_g + h_val
                heapq.heappush(priority_queue, (f_val, entry_counter, neighbor))

    elapsed_ms = (time.perf_counter() - start_time) * 1000.0

    if not found:
        return {
            "status": "error",
            "path": [],
            "distance_m": None,
            "expanded_nodes": expanded_nodes,
            "elapsed_ms": round(elapsed_ms, 4),
            "error": f"No existe ruta dirigida entre '{origin}' y '{destination}'.",
        }

    # Reconstrucción del camino
    path = []
    curr: str | None = destination
    while curr is not None:
        path.append(curr)
        curr = predecessor.get(curr)
    path.reverse()

    return {
        "status": "ok",
        "path": path,
        "distance_m": round(g_score[destination], 4),
        "expanded_nodes": expanded_nodes,
        "elapsed_ms": round(elapsed_ms, 4),
        "error": None,
    }


def get_route_metrics(
    origin: str,
    destination: str,
    graph: Graph | None = None,
) -> dict[str, Any]:
    """Ejecuta tanto A* como Dijkstra sobre el mismo par y retorna sus métricas comparativas.

    Parámetros
    ----------
    origin : str
        Identificador del nodo de origen.
    destination : str
        Identificador del nodo de destino.
    graph : Graph, optional
        Instancia del grafo vial. Si es None, se carga usando load_graph().

    Retorna
    -------
    dict[str, Any]
        Diccionario con las ejecuciones de 'astar' y 'dijkstra', más un resumen comparativo.
    """
    if graph is None:
        graph = load_graph()

    dijkstra_res = plan_route(origin, destination, algorithm="dijkstra", graph=graph)
    astar_res = plan_route(origin, destination, algorithm="astar", graph=graph)

    same_distance = None
    if dijkstra_res["distance_m"] is not None and astar_res["distance_m"] is not None:
        same_distance = abs(dijkstra_res["distance_m"] - astar_res["distance_m"]) < 1e-4

    return {
        "origin": origin,
        "destination": destination,
        "dijkstra": dijkstra_res,
        "astar": astar_res,
        "metrics": {
            "same_optimal_distance": same_distance,
            "expanded_difference": dijkstra_res["expanded_nodes"] - astar_res["expanded_nodes"],
            "dijkstra_expanded": dijkstra_res["expanded_nodes"],
            "astar_expanded": astar_res["expanded_nodes"],
            "dijkstra_time_ms": dijkstra_res["elapsed_ms"],
            "astar_time_ms": astar_res["elapsed_ms"],
        },
    }

