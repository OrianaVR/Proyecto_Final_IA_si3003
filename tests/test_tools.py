"""Pruebas de las herramientas del agent (Bloque 3 - Oriana): resultados reales, sin LLM."""

from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from src.agent import rag, tools


class ToolsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        tools.reset_cache()
        cls._tmp = tempfile.TemporaryDirectory()
        rag.build_index(index_dir=Path(cls._tmp.name), backend="hashing")
        tools._INDEX = rag.load_index(index_dir=Path(cls._tmp.name))
        with open("results/routes.csv", encoding="utf-8") as handle:
            cls.expected = {row["pair_id"]: row for row in csv.DictReader(handle)}

    @classmethod
    def tearDownClass(cls):
        tools.reset_cache()
        cls._tmp.cleanup()

    def test_schemas_expose_required_tools(self):
        self.assertTrue({"plan_route", "get_route_metrics"} <= set(tools.TOOL_NAMES))
        for schema in tools.TOOL_SCHEMAS:
            self.assertEqual(schema["type"], "function")
            json.dumps(schema)

    def test_plan_route_matches_block2_results(self):
        row = self.expected["pair_01"]
        out = tools.run_tool("plan_route", {"origin": row["origin"], "destination": row["destination"]})
        self.assertTrue(out.ok)
        self.assertAlmostEqual(out.full["distance_m"], float(row["astar_distance_m"]), places=3)
        self.assertEqual(out.full["expanded_nodes"], int(row["astar_expanded_nodes"]))
        self.assertGreater(len(out.full["path"]), 2)
        self.assertNotIn("path", out.view)                     # el modelo no recibe la lista de nodos
        self.assertIn("streets", out.view)

    def test_plan_route_accepts_dijkstra_and_json_string_args(self):
        row = self.expected["pair_07"]
        raw = json.dumps({"origin": row["origin"], "destination": row["destination"], "algorithm": "dijkstra"})
        out = tools.run_tool("plan_route", raw)
        self.assertTrue(out.ok)
        self.assertEqual(out.full["algorithm"], "dijkstra")
        self.assertEqual(out.full["expanded_nodes"], int(row["dijkstra_expanded_nodes"]))

    def test_numeric_ids_are_coerced_to_text(self):
        row = self.expected["pair_07"]
        out = tools.run_tool("plan_route", {"origin": int(row["origin"]), "destination": int(row["destination"])})
        self.assertTrue(out.ok)

    def test_unknown_node_is_structured_error(self):
        out = tools.run_tool("plan_route", {"origin": "99999999999", "destination": "330610901"})
        self.assertFalse(out.ok)
        self.assertEqual(out.full["status"], "error")
        self.assertIn("origen", out.full["error"])

    def test_route_metrics_compares_both_algorithms(self):
        row = self.expected["pair_04"]
        out = tools.run_tool("get_route_metrics", {"origin": row["origin"], "destination": row["destination"]})
        self.assertTrue(out.ok)
        self.assertEqual(out.view["astar"]["expanded_nodes"], int(row["astar_expanded_nodes"]))
        self.assertEqual(out.view["dijkstra"]["expanded_nodes"], int(row["dijkstra_expanded_nodes"]))
        self.assertTrue(out.view["metrics"]["same_optimal_distance"])
        self.assertIn("path", out.full["astar"])                # el trace conserva el camino completo
        self.assertNotIn("path", out.view["astar"])

    def test_find_nodes_intersection(self):
        out = tools.run_tool("find_nodes", {"street": "calle 50", "cross_street": "CARRERA 51"})
        self.assertTrue(out.ok)
        self.assertEqual([m["node_id"] for m in out.full["matches"]], ["330611865"])

    def test_find_nodes_single_street_is_sampled(self):
        out = tools.run_tool("find_nodes", {"street": "Avenida de Greiff"})
        self.assertTrue(out.ok)
        self.assertLessEqual(len(out.full["matches"]), 8)
        self.assertGreater(out.full["total_nodes"], 8)

    def test_find_nodes_errors_list_available_streets(self):
        out = tools.run_tool("find_nodes", {"street": "Calle Inexistente 999"})
        self.assertFalse(out.ok)
        self.assertIn("Calle 50", out.full["available_streets"])
        crossing = tools.run_tool("find_nodes", {"street": "Avenida de Greiff", "cross_street": "Calle 49"})
        self.assertFalse(crossing.ok)

    def test_intersection_ids_feed_plan_route(self):
        a = tools.run_tool("find_nodes", {"street": "Calle 50", "cross_street": "Carrera 51"}).full["matches"][0]
        b = tools.run_tool("find_nodes", {"street": "Calle 49", "cross_street": "Carrera 53"}).full["matches"][0]
        out = tools.run_tool("plan_route", {"origin": a["node_id"], "destination": b["node_id"]})
        self.assertIn(out.full["status"], ("ok", "error"))     # puede no haber ruta dirigida; nunca lanza

    def test_search_documents_returns_cited_fields(self):
        out = tools.run_tool("search_documents", {"query": "tarifa estudiantil Metro", "k": 3})
        self.assertTrue(out.ok)
        self.assertLessEqual(len(out.full["results"]), 3)
        self.assertTrue({"title", "url", "text", "chunk_id"} <= set(out.full["results"][0]))

    def test_search_documents_without_index_is_error(self):
        with mock.patch.object(tools, "_INDEX", None), \
                mock.patch.object(rag, "load_index", side_effect=rag.RagError("No existe el índice")):
            out = tools.run_tool("search_documents", {"query": "tarifa"})
        self.assertFalse(out.ok)
        self.assertIn("índice", out.full["error"])

    def test_bad_calls_never_raise(self):
        self.assertFalse(tools.run_tool("nope", {}).ok)
        self.assertFalse(tools.run_tool("plan_route", "{no es json").ok)
        self.assertFalse(tools.run_tool("plan_route", {"origin": "1"}).ok)
        self.assertFalse(tools.run_tool("plan_route", ["lista"]).ok)
        self.assertFalse(tools.run_tool("search_documents", {"query": "  "}).ok)
        bad_algo = tools.run_tool("plan_route", {"origin": "330610901", "destination": "358028386",
                                                 "algorithm": "bfs"})
        self.assertFalse(bad_algo.ok)


if __name__ == "__main__":
    unittest.main()
