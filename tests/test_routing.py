"""Pruebas unitarias para el módulo de enrutamiento (Bloque 2 - Wendy).

Verifica:
1. Equivalencia de costo óptimo entre A* y Dijkstra en los 10 pares reales alcanzables.
2. Comportamiento en caso de origen igual a destino (costo 0, camino trivial [origen]).
3. Control de errores con nodos de origen o destino inexistentes o inválidos.
4. Control de errores en caso de ruta inexistente (entre componentes no conectadas).
5. Control de algoritmo inválido.
6. Validación de llaves exactas del contrato en las respuestas de plan_route.
7. Comportamiento del conteo de nodos expandidos (A* expande <= Dijkstra).
"""

from __future__ import annotations

import unittest

from src.data import load_graph
from src.domain.models import Edge, Graph, Node
from src.routing import get_route_metrics, plan_route


class RoutingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.graph = load_graph()

    def test_astar_and_dijkstra_yield_identical_optimal_cost_on_test_pairs(self):
        """A* y Dijkstra deben hallar exactamente la misma distancia óptima en los 10 pares."""
        import json
        from pathlib import Path
        pairs_file = Path("data/test_pairs.json")
        with open(pairs_file, "r", encoding="utf-8") as f:
            pairs = json.load(f)

        for pair in pairs:
            origin = pair["origin"]
            destination = pair["destination"]
            metrics = get_route_metrics(origin, destination, graph=self.graph)

            dijkstra = metrics["dijkstra"]
            astar = metrics["astar"]

            self.assertEqual(dijkstra["status"], "ok")
            self.assertEqual(astar["status"], "ok")
            self.assertIsNone(dijkstra["error"])
            self.assertIsNone(astar["error"])

            # Comprobar costo óptimo idéntico
            self.assertIsNotNone(dijkstra["distance_m"])
            self.assertIsNotNone(astar["distance_m"])
            self.assertAlmostEqual(
                dijkstra["distance_m"],
                astar["distance_m"],
                places=3,
                msg=f"Discrepancia de costo en par {origin}->{destination}",
            )

            # Comprobar que A* expande menor o igual número de nodos que Dijkstra
            self.assertLessEqual(
                astar["expanded_nodes"],
                dijkstra["expanded_nodes"],
                msg=f"A* expandió más nodos que Dijkstra en par {origin}->{destination}",
            )

    def test_same_origin_and_destination_returns_zero_cost(self):
        """Si origin == destination, retorna status ok, costo cero y camino [origin]."""
        sample_node_id = next(iter(self.graph.nodes.keys()))

        for algo in ("astar", "dijkstra"):
            result = plan_route(sample_node_id, sample_node_id, algorithm=algo, graph=self.graph)
            self.assertEqual(result["status"], "ok")
            self.assertEqual(result["path"], [sample_node_id])
            self.assertEqual(result["distance_m"], 0.0)
            self.assertEqual(result["expanded_nodes"], 0)
            self.assertIsNone(result["error"])
            self.assertGreaterEqual(result["elapsed_ms"], 0.0)

    def test_nonexistent_origin_node_returns_error(self):
        """Nodo de origen inexistente debe retornar error controlado y llaves exactas."""
        sample_node_id = next(iter(self.graph.nodes.keys()))
        result = plan_route("nodo_fantasma_xyz", sample_node_id, algorithm="astar", graph=self.graph)

        self.assertEqual(result["status"], "error")
        self.assertEqual(result["path"], [])
        self.assertIsNone(result["distance_m"])
        self.assertEqual(result["expanded_nodes"], 0)
        self.assertIn("Nodo de origen no existe", result["error"])

    def test_nonexistent_destination_node_returns_error(self):
        """Nodo de destino inexistente debe retornar error controlado y llaves exactas."""
        sample_node_id = next(iter(self.graph.nodes.keys()))
        result = plan_route(sample_node_id, "nodo_fantasma_xyz", algorithm="dijkstra", graph=self.graph)

        self.assertEqual(result["status"], "error")
        self.assertEqual(result["path"], [])
        self.assertIsNone(result["distance_m"])
        self.assertEqual(result["expanded_nodes"], 0)
        self.assertIn("Nodo de destino no existe", result["error"])

    def test_invalid_algorithm_returns_error(self):
        """Algoritmo no soportado debe retornar error controlado."""
        sample_node_id = next(iter(self.graph.nodes.keys()))
        result = plan_route(sample_node_id, sample_node_id, algorithm="bfs_invalido", graph=self.graph)

        self.assertEqual(result["status"], "error")
        self.assertEqual(result["path"], [])
        self.assertIsNone(result["distance_m"])
        self.assertEqual(result["expanded_nodes"], 0)
        self.assertIn("Algoritmo no soportado", result["error"])

    def test_unreachable_route_returns_error_and_empty_path(self):
        """En un grafo con nodos desconectados, una ruta inexistente debe retornar error."""
        # Creamos un grafo sintético con dos nodos sin arista dirigida entre ellos
        node_a = Node("node_a", 6.25, -75.57)
        node_b = Node("node_b", 6.26, -75.56)
        node_c = Node("node_c", 6.27, -75.55)
        # Solo arista A -> B; C queda aislado como destino inalcanzable
        edge_ab = Edge("edge_ab", "node_a", "node_b", 100.0, "way_1")

        synthetic_graph = Graph(
            nodes={"node_a": node_a, "node_b": node_b, "node_c": node_c},
            edges=(edge_ab,),
        )

        for algo in ("astar", "dijkstra"):
            result = plan_route("node_a", "node_c", algorithm=algo, graph=synthetic_graph)
            self.assertEqual(result["status"], "error")
            self.assertEqual(result["path"], [])
            self.assertIsNone(result["distance_m"])
            self.assertIn("No existe ruta dirigida", result["error"])

    def test_exact_keys_in_result_dictionary(self):
        """Verificar que el diccionario retornado cumpla exactamente con el contrato."""
        expected_keys = {"status", "path", "distance_m", "expanded_nodes", "elapsed_ms", "error"}
        sample_node_id = next(iter(self.graph.nodes.keys()))

        res_ok = plan_route(sample_node_id, sample_node_id, algorithm="astar", graph=self.graph)
        self.assertEqual(set(res_ok.keys()), expected_keys)

        res_err = plan_route("no_existe_1", "no_existe_2", algorithm="astar", graph=self.graph)
        self.assertEqual(set(res_err.keys()), expected_keys)


if __name__ == "__main__":
    unittest.main()

