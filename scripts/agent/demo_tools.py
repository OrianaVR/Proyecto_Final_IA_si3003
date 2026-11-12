"""Ejemplo ejecutable SIN modelo de lenguaje: prueba herramientas y recuperación documental.

    python -m scripts.agent.demo_tools

Requiere el índice (python -m scripts.agent.build_index). No usa red ni claves.
"""

from __future__ import annotations

import json

from src.agent.tools import run_tool


def show(title: str, name: str, arguments: dict) -> None:
    outcome = run_tool(name, arguments)
    print(f"\n=== {title}\n{name}({json.dumps(arguments, ensure_ascii=False)})  ok={outcome.ok}")
    print(json.dumps(outcome.view, ensure_ascii=False, indent=2)[:1800])


def main() -> None:
    show("Ruta con A*", "plan_route", {"origin": "10311382890", "destination": "10735878410"})
    show("Ruta con Dijkstra", "plan_route",
         {"origin": "10311382890", "destination": "10735878410", "algorithm": "dijkstra"})
    show("Métricas A* vs Dijkstra", "get_route_metrics", {"origin": "13957920179", "destination": "330610901"})
    show("Intersección por nombres de calle", "find_nodes", {"street": "Calle 50", "cross_street": "Carrera 51"})
    show("Error controlado (nodo inexistente)", "plan_route", {"origin": "99999999999", "destination": "330610901"})
    show("Recuperación documental", "search_documents", {"query": "uso indebido funcionalidad Bici bloqueo", "k": 2})


if __name__ == "__main__":
    main()
