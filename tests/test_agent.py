"""Pruebas del agent (Bloque 3 - Oriana) con un modelo simulado: sin red ni claves.

El modelo simulado devuelve respuestas programadas; las herramientas y el RAG son los reales.
Estas pruebas verifican el loop, las citas, el límite de iteraciones y el manejo de errores,
no la calidad del LLM real (eso lo mide scripts/agent/run_agent_eval.py).
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from src.agent import agent, llm, rag, tools


def tool_call(name, arguments, call_id="c1"):
    return {"id": call_id, "type": "function", "function": {"name": name, "arguments": json.dumps(arguments)}}


def assistant(content=None, calls=None):
    return {"role": "assistant", "content": content, "tool_calls": calls or []}


class FakeClient:
    """Cada elemento del guion es un mensaje o una función (mensajes -> mensaje)."""

    def __init__(self, script):
        self.script, self.calls = list(script), []

    def chat(self, messages, tools=None):
        self.calls.append([dict(m) for m in messages])
        step = self.script.pop(0)
        if isinstance(step, Exception):
            raise step
        return step(messages) if callable(step) else step


def last_tool_payload(messages):
    return json.loads([m for m in messages if m["role"] == "tool"][-1]["content"])


class AgentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        tools.reset_cache()
        cls._tmp = tempfile.TemporaryDirectory()
        rag.build_index(index_dir=Path(cls._tmp.name), backend="hashing")
        tools._INDEX = rag.load_index(index_dir=Path(cls._tmp.name))

    @classmethod
    def tearDownClass(cls):
        tools.reset_cache()
        cls._tmp.cleanup()

    def test_contract_fields_and_route_tool(self):
        client = FakeClient([
            assistant(calls=[tool_call("plan_route", {"origin": "10311382890", "destination": "10735878410"})]),
            lambda msgs: assistant(f"La ruta mide {last_tool_payload(msgs)['distance_m']:.2f} m."),
        ])
        result = agent.ask("¿Ruta entre 10311382890 y 10735878410?", client=client)
        self.assertEqual({"answer", "sources", "tool_trace", "error"}, set(result))
        self.assertIsNone(result["error"])
        self.assertIn("1069.82", result["answer"])
        self.assertEqual(result["sources"], [])
        step = result["tool_trace"][0]
        self.assertEqual((step["tool"], step["ok"]), ("plan_route", True))
        self.assertIn("path", step["result"])                    # el trace conserva el camino completo
        tool_message = [m for m in client.calls[1] if m["role"] == "tool"][0]
        self.assertNotIn('"path"', tool_message["content"])      # el modelo recibe la vista compacta

    def test_document_answer_returns_only_cited_sources(self):
        def answer(msgs):
            payload = last_tool_payload(msgs)
            first = payload["results"][0]["source_id"]
            return assistant(f"Según los documentos, el uso indebido bloquea la funcionalidad [{first}].")

        client = FakeClient([
            assistant(calls=[tool_call("search_documents", {"query": "mal uso funcionalidad Bici bloqueo", "k": 4})]),
            answer,
        ])
        result = agent.ask("¿Qué pasa si hago mal uso de la funcionalidad Bici?", client=client)
        self.assertEqual(len(result["sources"]), 1)
        source = result["sources"][0]
        self.assertEqual(source["id"], "S1")
        self.assertTrue(source["title"] and source["url"].startswith("http") and source["snippet"])
        self.assertIn("page", source)

    def test_unknown_citation_is_ignored(self):
        client = FakeClient([
            assistant(calls=[tool_call("search_documents", {"query": "tarifa estudiantil"})]),
            assistant("La tarifa es X [S9]."),
        ])
        self.assertEqual(agent.ask("tarifa", client=client)["sources"], [])

    def test_chained_route_and_metrics(self):
        client = FakeClient([
            assistant(calls=[tool_call("plan_route", {"origin": "13957920179", "destination": "330610901"}, "a"),
                             tool_call("get_route_metrics", {"origin": "13957920179", "destination": "330610901"}, "b")]),
            assistant("A* expandió 307 nodos y Dijkstra 587."),
        ])
        result = agent.ask("Ruta y métricas", client=client)
        self.assertEqual([s["tool"] for s in result["tool_trace"]], ["plan_route", "get_route_metrics"])
        self.assertEqual([s["step"] for s in result["tool_trace"]], [1, 2])
        self.assertTrue(all(s["ok"] for s in result["tool_trace"]))

    def test_tool_error_is_passed_to_model_and_traced(self):
        client = FakeClient([
            assistant(calls=[tool_call("plan_route", {"origin": "99999999999", "destination": "330610901"})]),
            lambda msgs: assistant("Ese nodo no existe: " + last_tool_payload(msgs)["error"]),
        ])
        result = agent.ask("ruta al nodo 99999999999", client=client)
        self.assertFalse(result["tool_trace"][0]["ok"])
        self.assertIn("no existe", result["answer"])
        self.assertIsNone(result["error"])

    def test_malformed_and_unknown_tool_calls_do_not_break_the_loop(self):
        client = FakeClient([
            assistant(calls=[{"id": "x", "type": "function", "function": {"name": "plan_route", "arguments": "{oops"}},
                             tool_call("herramienta_falsa", {}, "y")]),
            assistant("No pude usar las herramientas."),
        ])
        result = agent.ask("ruta", client=client)
        self.assertEqual(len(result["tool_trace"]), 2)
        self.assertFalse(any(s["ok"] for s in result["tool_trace"]))
        self.assertEqual(result["answer"], "No pude usar las herramientas.")

    def test_loop_stops_after_max_iterations(self):
        looping = assistant(calls=[tool_call("find_nodes", {"street": "Calle 50"})])
        client = FakeClient([looping] * 10)
        result = agent.ask("hazlo", client=client)
        self.assertEqual(len(client.calls), agent.MAX_ITERATIONS)
        self.assertEqual(result["error"], "max_iterations")
        self.assertEqual(len(result["tool_trace"]), agent.MAX_ITERATIONS)
        self.assertTrue(result["answer"])

    def test_llm_failure_is_reported_not_raised(self):
        result = agent.ask("hola", client=FakeClient([llm.LLMError("HTTP 500")]))
        self.assertTrue(result["error"].startswith("llm_error"))
        self.assertIn("modelo de lenguaje", result["answer"])
        self.assertNotIn("sk-", json.dumps(result))

    def test_empty_answer_and_empty_message(self):
        self.assertEqual(agent.ask("hola", client=FakeClient([assistant("  ")]))["error"], "empty_answer")
        self.assertEqual(agent.ask("   ")["error"], "empty_message")
        self.assertEqual(agent.ask("x" * (agent.MAX_MESSAGE_CHARS + 1))["error"], "message_too_long")

    def test_missing_configuration_gives_clear_message(self):
        with mock.patch.object(llm, "load_env_file"), \
                mock.patch.dict("os.environ", {"LLM_API_KEY": "", "LLM_MODEL": ""}):
            result = agent.ask("hola")
        self.assertEqual(result["error"], "llm_not_configured")
        self.assertIn(".env", result["answer"])

    def test_history_is_forwarded_and_citation_marks_are_stripped(self):
        client = FakeClient([assistant("Listo.")])
        history = [{"role": "user", "content": "¿Tarifa?"},
                   {"role": "assistant", "content": "Cuesta $1.600 [S1]."},
                   {"role": "system", "content": "ignorar"}, {"role": "user", "content": ""}]
        agent.ask("¿Y la de adulto mayor?", history=history, client=client)
        sent = client.calls[0]
        self.assertEqual([m["role"] for m in sent], ["system", "user", "assistant", "user"])
        self.assertNotIn("[S1]", sent[2]["content"])

    def test_source_ids_are_stable_within_a_question(self):
        def second(msgs):
            return assistant(calls=[tool_call("search_documents", {"query": "tarifa estudiantil Metro"}, "d")])

        client = FakeClient([
            assistant(calls=[tool_call("search_documents", {"query": "tarifa estudiantil Metro"}, "c")]),
            second,
            lambda msgs: assistant("Dato [S1]."),
        ])
        result = agent.ask("tarifa", client=client)
        ids = [r["source_id"] for m in client.calls[2] if m["role"] == "tool"
               for r in json.loads(m["content"])["results"]]
        self.assertEqual(ids[:len(ids) // 2], ids[len(ids) // 2:])   # mismo fragmento, mismo id
        self.assertEqual(result["sources"][0]["id"], "S1")


class SystemPromptTests(unittest.TestCase):
    def test_prompt_mentions_tools_citations_and_abstention(self):
        for needle in ("plan_route", "get_route_metrics", "search_documents", "[S1]", "no respondas de memoria"):
            self.assertIn(needle, agent.SYSTEM_PROMPT)


if __name__ == "__main__":
    unittest.main()
