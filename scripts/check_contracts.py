"""Valida los 4 contratos del equipo con data/test_pairs.json (sin red ni API key).

Uso: python -m scripts.check_contracts
"""
import json
import sys
from pathlib import Path

from src.agent.agent import ask
from src.data import load_graph
from src.routing import get_route_metrics, plan_route

ROOT = Path(__file__).resolve().parents[1]
ROUTE_KEYS = {"status", "path", "distance_m", "expanded_nodes", "elapsed_ms", "error"}
failures: list[str] = []


def check(ok: bool, label: str) -> None:
    print(("OK   " if ok else "FALLA"), label)
    if not ok:
        failures.append(label)


def main() -> int:
    graph = load_graph()
    pairs = json.loads((ROOT / "data" / "test_pairs.json").read_text(encoding="utf-8"))

    # 1. load_graph
    check(len(graph.nodes) > 0 and len(graph.edges) > 0, f"load_graph: {len(graph.nodes)} nodos, {len(graph.edges)} aristas")
    check(all(n.id and n.latitude is not None and n.longitude is not None for n in graph.nodes.values()),
          "load_graph: todos los nodos tienen id, lat y lon")
    check(all(e.distance_m >= 0 and e.origin in graph.nodes and e.destination in graph.nodes for e in graph.edges),
          "load_graph: aristas con distance_m >= 0 y extremos existentes")

    # 2 y 3. plan_route / get_route_metrics en los pares de prueba
    for pair in pairs:
        o, d = pair["origin"], pair["destination"]
        results = {a: plan_route(o, d, a, graph=graph) for a in ("astar", "dijkstra")}
        shape_ok = all(set(r) >= ROUTE_KEYS and r["status"] == "ok" and r["path"] for r in results.values())
        same = abs(results["astar"]["distance_m"] - results["dijkstra"]["distance_m"]) < 1e-4 if shape_ok else False
        check(shape_ok and same, f"plan_route {pair['id']}: campos, ok y mismo costo A*/Dijkstra")
        m = get_route_metrics(o, d, graph=graph)
        check({"astar", "dijkstra", "metrics"} <= set(m), f"get_route_metrics {pair['id']}: ambos algoritmos")

    bad = plan_route("no-existe", pairs[0]["destination"], "astar", graph=graph)
    check(bad["status"] == "error" and bad["error"], "plan_route: nodo inválido devuelve error estructurado")

    # 4. ask con cliente simulado (sin LLM real)
    class Fake:
        def chat(self, messages, tools=None):
            return {"content": "Respuesta de prueba.", "tool_calls": []}

    r = ask("hola", [], client=Fake())
    check({"answer", "sources", "tool_trace"} <= set(r) and isinstance(r["sources"], list)
          and isinstance(r["tool_trace"], list), "ask: devuelve answer, sources y tool_trace")

    print(f"\n{'TODO OK' if not failures else str(len(failures)) + ' contrato(s) con fallas'}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
