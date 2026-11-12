"""Consola para probar el agent sin interfaz.

    python -m scripts.agent.ask_cli "¿Ruta entre 10311382890 y 10735878410?"   # una pregunta
    python -m scripts.agent.ask_cli                                            # conversación (línea vacía sale)

Necesita LLM_API_KEY y LLM_MODEL (ver .env.example) y el índice (python -m scripts.agent.build_index).
"""

from __future__ import annotations

import sys

from src.agent.agent import ask


def run_once(message: str, history: list[dict]) -> None:
    result = ask(message, history)
    print(f"\n{result['answer']}")
    if result["sources"]:
        print("\nFuentes:")
        for source in result["sources"]:
            page = f", pág. {source['page']}" if source["page"] else ""
            print(f"  [{source['id']}] {source['title']}{page} - {source['url']}")
    if result["tool_trace"]:
        print("\nHerramientas:")
        for step in result["tool_trace"]:
            print(f"  {step['step']}. {step['tool']}({step['arguments']}) -> {'ok' if step['ok'] else 'ERROR'}")
    if result["error"]:
        print(f"\n[error: {result['error']}]")
    history += [{"role": "user", "content": message}, {"role": "assistant", "content": result["answer"]}]


def main() -> None:
    history: list[dict] = []
    if len(sys.argv) > 1:
        run_once(" ".join(sys.argv[1:]), history)
        return
    while True:
        message = input("\nTú: ").strip()
        if not message:
            break
        run_once(message, history)


if __name__ == "__main__":
    main()
