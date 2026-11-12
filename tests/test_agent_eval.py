"""Pruebas de las preguntas fijas y de la calificación automática (Bloque 3 - Oriana)."""

from __future__ import annotations

import json
import tempfile
import unittest
from collections import Counter
from pathlib import Path

from scripts.agent import run_agent_eval as ev

QUESTIONS = json.loads(Path("tests/agent_questions.json").read_text(encoding="utf-8"))


def step(tool, arguments, result, ok=True):
    return {"step": 1, "tool": tool, "arguments": arguments, "ok": ok, "result": result}


class QuestionSetTests(unittest.TestCase):
    def test_twelve_questions_with_required_distribution(self):
        self.assertEqual(len(QUESTIONS), 12)
        self.assertEqual(len({q["id"] for q in QUESTIONS}), 12)
        counts = Counter(q["category"] for q in QUESTIONS)
        self.assertEqual((counts["ruta"], counts["documental"], counts["encadenada"]), (4, 3, 2))
        self.assertEqual(counts["error"] + counts["ausente"], 3)

    def test_expected_distances_match_block2_results(self):
        import csv
        with open("results/routes.csv", encoding="utf-8") as handle:
            routes = {(r["origin"], r["destination"]): float(r["astar_distance_m"]) for r in csv.DictReader(handle)}
        import re
        for question in QUESTIONS:
            ids = re.findall(r"\d{8,}", question["question"])
            if "expected_distance_m" in question and len(ids) == 2:
                self.assertAlmostEqual(routes[tuple(ids)], question["expected_distance_m"], delta=0.01)


class NumberParsingTests(unittest.TestCase):
    def test_spanish_english_and_plain_formats(self):
        for text in ("1.069,82 m", "1,069.82 m", "1069.82 metros", "unos 1069,8 m"):
            self.assertTrue(ev.has_number(text, 1069.82), text)
        self.assertTrue(ev.has_number("$1.600", 1600, tol=0.01))
        self.assertTrue(ev.has_number("aprox. 1,07 km", 1069.82, allow_km=True))
        self.assertFalse(ev.has_number("la ruta mide 2000 m", 1069.82))
        self.assertTrue(ev.has_number("A* expandió 307 nodos", 307, tol=0.01))


class GradingTests(unittest.TestCase):
    def q(self, qid):
        return next(item for item in QUESTIONS if item["id"] == qid)

    def route_result(self, answer, distance=1069.8194):
        return {"answer": answer, "sources": [], "error": None,
                "tool_trace": [step("plan_route", {"origin": "1", "destination": "2"}, {"distance_m": distance})]}

    def test_route_success_and_wrong_number(self):
        self.assertEqual(ev.grade(self.q("q01"), self.route_result("Son 1.069,82 m."))["result"], "acierto")
        self.assertEqual(ev.grade(self.q("q01"), self.route_result("Son 1.500 m."))["result"], "fallo")

    def test_wrong_tool_distance_fails_even_if_answer_matches(self):
        graded = ev.grade(self.q("q01"), self.route_result("Son 1069,82 m.", distance=900.0))
        self.assertEqual(graded["numeric_ok"], False)

    def test_algorithm_argument_is_checked(self):
        right = {"answer": "411,94 m", "sources": [], "error": None,
                 "tool_trace": [step("plan_route", {"origin": "1", "destination": "2", "algorithm": "dijkstra"},
                                     {"distance_m": 411.9372})]}
        wrong = {**right, "tool_trace": [step("plan_route", {"origin": "1", "destination": "2"},
                                              {"distance_m": 411.9372})]}
        self.assertEqual(ev.grade(self.q("q02"), right)["result"], "acierto")
        self.assertEqual(ev.grade(self.q("q02"), wrong)["tools_ok"], False)

    def test_default_algorithm_counts_as_astar(self):
        result = {"answer": "1308,84 m; A* 171 y Dijkstra 451 nodos.", "sources": [], "error": None,
                  "tool_trace": [step("plan_route", {"origin": "1", "destination": "2"}, {"distance_m": 1308.835}),
                                 step("get_route_metrics", {"origin": "1", "destination": "2"},
                                      {"astar": {"distance_m": 1308.835}, "dijkstra": {"distance_m": 1308.835}})]}
        self.assertEqual(ev.grade(self.q("q09"), result)["result"], "acierto")

    def test_citation_must_come_from_expected_document(self):
        base = {"answer": "Bloqueo de 3 meses [S1].", "error": None,
                "tool_trace": [step("search_documents", {"query": "x"}, {"results": []})]}
        good = {**base, "sources": [{"id": "S1", "document_id": "metro_bici"}]}
        bad = {**base, "sources": [{"id": "S1", "document_id": "metro_usuarios"}]}
        self.assertEqual(ev.grade(self.q("q05"), good)["result"], "acierto")
        self.assertEqual(ev.grade(self.q("q05"), bad)["citation_ok"], False)
        self.assertEqual(ev.grade(self.q("q05"), {**base, "sources": []})["result"], "fallo")

    def test_not_applicable_criteria_do_not_count_as_hits(self):
        graded = ev.grade(self.q("q11"), {"answer": "No está en los documentos.", "sources": [],
                                          "tool_trace": [], "error": None})
        self.assertTrue(all(graded[k] == "n/a" for k in ev.CRITERIA))
        self.assertEqual(graded["result"], "pendiente")      # nunca 'acierto' sin revisión manual

    def test_tool_error_expected_and_agent_error(self):
        err = {"answer": "Ese nodo no existe.", "sources": [], "error": None,
               "tool_trace": [step("plan_route", {}, {"status": "error"}, ok=False)]}
        graded = ev.grade(self.q("q10"), err)
        self.assertEqual((graded["tool_error_ok"], graded["result"]), (True, "pendiente"))
        failing = {"answer": "x", "sources": [], "tool_trace": [], "error": "llm_error: HTTP 500"}
        self.assertEqual(ev.grade(self.q("q01"), failing)["result"], "fallo")


class SummaryTests(unittest.TestCase):
    def test_summary_has_explicit_denominators_and_writes_files(self):
        def fake_ask(text):
            return {"answer": "no sé", "sources": [], "tool_trace": [], "error": None}

        rows = ev.evaluate(QUESTIONS, fake_ask, "modelo-x", "hashing")
        with tempfile.TemporaryDirectory() as tmp:
            summary = ev.write_outputs(rows, Path(tmp) / "e.csv", Path(tmp) / "s.json")
            self.assertEqual(len((Path(tmp) / "e.csv").read_text(encoding="utf-8").splitlines()), 13)
        self.assertEqual(summary["total_questions"], 12)
        self.assertEqual(summary["auto_graded"], {"correct": 0, "of": 9})
        self.assertEqual(summary["pending_manual_review"], 3)
        self.assertEqual(summary["criteria"]["citation_ok"], {"passed": 0, "applicable": 3})
        self.assertEqual(summary["criteria"]["tool_error_ok"]["applicable"], 1)


if __name__ == "__main__":
    unittest.main()
