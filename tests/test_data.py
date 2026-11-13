import json
from dataclasses import asdict
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from src.application.datasets import make_test_pairs, reachable_nodes, validate_test_pairs
from src.config import DEFAULT_BBOX, PROJECT_ROOT, RAW_GRAPH
from src.data import load_graph
from src.domain.geo import haversine_m
from src.domain.models import DataValidationError, Edge, Graph, Node
from src.infrastructure.json_store import JsonGraphRepository, write_json
from src.infrastructure.osm import build_graph, directions, is_allowed
from scripts.prepare_data import prepare
from scripts.validate import validate


class DomainTests(unittest.TestCase):
    def test_invalid_coordinates_and_distances_are_rejected(self):
        for lat in (91, float("nan"), float("inf")):
            with self.assertRaises(DataValidationError):
                Node("n", lat, 0)
        for distance in (-1, float("nan"), float("inf")):
            with self.assertRaises(DataValidationError):
                Edge("e", "a", "b", distance, "way")

    def test_missing_endpoint_is_rejected(self):
        with self.assertRaises(DataValidationError):
            Graph({"a": Node("a", 0, 0)}, (Edge("e", "a", "b", 1, "w"),))

    def test_haversine_known_distance_and_symmetry(self):
        a, b = Node("a", 0, 0), Node("b", 0, 1)
        self.assertAlmostEqual(haversine_m(a, b), 111195.080, places=2)
        self.assertEqual(haversine_m(a, b), haversine_m(b, a))
        self.assertEqual(haversine_m(a, a), 0)

    def test_duplicate_edge_id_is_rejected(self):
        nodes = {key: Node(key, 0, index) for index,key in enumerate(("a","b"))}
        edge = Edge("e", "a", "b", 1, "w")
        with self.assertRaises(DataValidationError):
            Graph(nodes, (edge, edge))


class OsmTests(unittest.TestCase):
    def test_direction_rules(self):
        self.assertEqual(directions({"oneway": "-1"}), (False, True))
        self.assertEqual(directions({"oneway": "yes"}), (True, False))
        self.assertEqual(directions({"junction": "roundabout"}), (True, False))
        self.assertEqual(directions({"junction": "roundabout", "oneway": "no"}), (True, True))
        self.assertEqual(directions({"oneway": "unknown"}), (False, False))

    def test_access_specificity_and_unsupported_ways(self):
        self.assertFalse(is_allowed({"highway":"residential", "access":"private"}))
        self.assertTrue(is_allowed({"highway":"residential", "access":"private", "motorcar":"yes"}))
        self.assertFalse(is_allowed({"highway":"footway"}))
        self.assertFalse(is_allowed({"highway":"residential", "oneway":"reversible"}))
        self.assertFalse(is_allowed({"highway":"residential", "area":"yes"}))

    def test_xml_parser_preserves_direction_and_clips_bbox(self):
        xml = '<osm><node id="1" lat="0" lon="0"/><node id="2" lat="0" lon="0.01"/>'
        xml += '<node id="3" lat="0" lon="0.03"/><way id="4"><nd ref="1"/><nd ref="2"/>'
        xml += '<nd ref="3"/><tag k="highway" v="residential"/><tag k="oneway" v="-1"/></way></osm>'
        with TemporaryDirectory() as directory:
            path = Path(directory)/"graph.osm"; path.write_text(xml)
            graph = build_graph(path, (-.01,-.01,.02,.01), {})
            self.assertEqual(set(graph.nodes), {"1","2"})
            self.assertEqual([(e.origin,e.destination) for e in graph.edges], [("2","1")])
            self.assertAlmostEqual(graph.edges[0].distance_m, 1111.95, places=1)


class DatasetIntegrationTests(unittest.TestCase):
    def test_included_snapshot_loads_without_network(self):
        with patch("urllib.request.urlopen", side_effect=AssertionError("Network forbidden")), \
             patch("src.infrastructure.http_client.urlopen", side_effect=AssertionError("Network forbidden")):
            report = validate()
        self.assertEqual(report["status"], "ok")
        self.assertEqual(report["test_pairs"], 10)
        self.assertGreater(report["nodes"], 100)
        self.assertEqual(report["corpus_documents"], 4)

    def test_all_ten_pairs_are_directed_reachable_and_deterministic(self):
        graph = load_graph()
        pairs = make_test_pairs(graph)
        validate_test_pairs(graph, pairs)
        expected = json.loads((PROJECT_ROOT/"data/test_pairs.json").read_text())
        self.assertEqual(pairs, expected)
        for pair in pairs:
            self.assertIn(pair["destination"], reachable_nodes(graph, pair["origin"]))

    def test_rebuild_matches_shipped_data_with_numeric_tolerance(self):
        expected = load_graph()
        with TemporaryDirectory() as directory:
            base = Path(directory)
            rebuilt = prepare(
                RAW_GRAPH,
                tuple(expected.metadata["bbox_wsen"]),
                base / "processed",
                base / "pairs.json",
            )
            # Coordenadas, topología, ids y metadatos deben ser iguales.
            self.assertEqual(rebuilt.nodes, expected.nodes)
            self.assertEqual(rebuilt.metadata, expected.metadata)
            self.assertEqual(len(rebuilt.edges), len(expected.edges))
            for actual_edge, expected_edge in zip(rebuilt.edges, expected.edges):
                with self.subTest(edge_id=expected_edge.id):
                    actual_fields = asdict(actual_edge)
                    expected_fields = asdict(expected_edge)
                    actual_distance = actual_fields.pop("distance_m")
                    expected_distance = expected_fields.pop("distance_m")
                    self.assertEqual(actual_fields, expected_fields)
                    # math puede variar en los últimos bits entre plataformas.
                    # 1e-8 metros evita exigir identidad binaria sin ocultar
                    # cambios materiales de distancias.
                    self.assertAlmostEqual(
                        actual_distance,
                        expected_distance,
                        delta=1e-8,
                    )
            actual_pairs = json.loads((base / "pairs.json").read_text(encoding="utf-8"))
            expected_pairs = json.loads(
                (PROJECT_ROOT / "data/test_pairs.json").read_text(encoding="utf-8")
            )
            self.assertEqual(actual_pairs, expected_pairs)

    def test_repository_roundtrip_and_duplicate_node_detection(self):
        graph = load_graph()
        with TemporaryDirectory() as directory:
            target = Path(directory)
            repository = JsonGraphRepository()
            repository.save(graph, target)
            self.assertEqual(repository.load(target).edges, graph.edges)
            nodes = json.loads((target/"nodes.json").read_text())
            nodes.append(nodes[0]);write_json(target/"nodes.json", nodes)
            with self.assertRaises(DataValidationError):
                repository.load(target)

    def test_missing_dataset_produces_actionable_error(self):
        with TemporaryDirectory() as directory:
            with self.assertRaisesRegex(DataValidationError, "No se pudo cargar"):
                load_graph(directory)

    def test_tampered_raw_data_is_rejected_before_processing(self):
        with TemporaryDirectory() as directory:
            raw = Path(directory)/"bad.osm"
            raw.write_text("<osm/>")
            write_json(raw.with_suffix(".osm.source.json"), {"sha256":"wrong"})
            with self.assertRaisesRegex(ValueError, "hash"):
                prepare(raw, DEFAULT_BBOX, Path(directory)/"out", Path(directory)/"pairs.json")


if __name__ == "__main__":
    unittest.main()
