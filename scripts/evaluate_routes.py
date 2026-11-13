"""Script para evaluar los 10 pares de prueba fijos del Bloque 2 (Wendy).

Lee data/test_pairs.json, evalúa ambos algoritmos (A* y Dijkstra) llamando a
get_route_metrics, e imprime y exporta los resultados consolidados a results/routes.csv.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
import sys

# Asegurar que el directorio raíz del proyecto esté en sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.data import load_graph
from src.routing import get_route_metrics


def evaluate_test_pairs(
    test_pairs_path: Path = PROJECT_ROOT / "data" / "test_pairs.json",
    output_csv_path: Path = PROJECT_ROOT / "results" / "routes.csv",
) -> list[dict]:
    """Carga los pares de prueba, ejecuta las métricas de ruta y genera el archivo CSV."""
    if not test_pairs_path.is_file():
        raise FileNotFoundError(f"No se encontró el archivo de pares de prueba: {test_pairs_path}")

    with open(test_pairs_path, "r", encoding="utf-8") as f:
        test_pairs = json.load(f)

    print(f"Cargando grafo vial local...")
    graph = load_graph()
    print(f"Grafo cargado: {len(graph.nodes)} nodos y {len(graph.edges)} aristas dirigidas.")
    print(f"Evaluando {len(test_pairs)} pares de prueba con Dijkstra y A*...\n")

    results = []

    for pair in test_pairs:
        pair_id = pair.get("id", "")
        origin = pair["origin"]
        destination = pair["destination"]

        metrics = get_route_metrics(origin, destination, graph=graph)
        dijkstra = metrics["dijkstra"]
        astar = metrics["astar"]

        row = {
            "pair_id": pair_id,
            "origin": origin,
            "destination": destination,
            "status": "ok" if (dijkstra["status"] == "ok" and astar["status"] == "ok") else "error",
            "dijkstra_distance_m": dijkstra["distance_m"],
            "astar_distance_m": astar["distance_m"],
            "same_optimal_distance": metrics["metrics"]["same_optimal_distance"],
            "dijkstra_expanded_nodes": dijkstra["expanded_nodes"],
            "astar_expanded_nodes": astar["expanded_nodes"],
            "expanded_nodes_diff": metrics["metrics"]["expanded_difference"],
            "astar_expansion_reduction_pct": round(
                ((dijkstra["expanded_nodes"] - astar["expanded_nodes"]) / dijkstra["expanded_nodes"] * 100.0)
                if dijkstra["expanded_nodes"] > 0
                else 0.0,
                2,
            ),
            "dijkstra_elapsed_ms": dijkstra["elapsed_ms"],
            "astar_elapsed_ms": astar["elapsed_ms"],
            "dijkstra_path_hops": len(dijkstra["path"]),
            "astar_path_hops": len(astar["path"]),
            "same_path": dijkstra["path"] == astar["path"],
        }
        results.append(row)

        print(
            f"[{pair_id}] Dist: {row['astar_distance_m']}m | "
            f"Expandidos -> Dijkstra: {row['dijkstra_expanded_nodes']}, A*: {row['astar_expanded_nodes']} "
            f"(-{row['astar_expansion_reduction_pct']}%) | "
            f"Tiempo -> D: {row['dijkstra_elapsed_ms']}ms, A*: {row['astar_elapsed_ms']}ms"
        )

    output_csv_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(results[0].keys())

    with open(output_csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)

    print(f"\nResultados exportados exitosamente a: {output_csv_path}")
    return results


if __name__ == "__main__":
    evaluate_test_pairs()

