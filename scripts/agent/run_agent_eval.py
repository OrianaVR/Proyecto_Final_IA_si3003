"""Evalúa el agent con las 12 preguntas fijas de tests/agent_questions.json.

    python -m scripts.agent.run_agent_eval [--sleep 2]

Usa el modelo real configurado en .env. Escribe:
    results/agent_eval.csv            una fila por pregunta (herramientas esperadas/llamadas, citas, resultado)
    results/agent_eval_summary.json   tasas con denominador explícito

Criterios automáticos (solo cuando aplican; los no aplicables NO cuentan como aciertos):
    tools_ok      se llamaron todas las herramientas esperadas (y con los argumentos esperados, si se piden)
    citation_ok   la respuesta citó al menos una fuente de los documentos esperados
    numeric_ok    la respuesta contiene la distancia (y los conteos) que devolvieron las herramientas
    tool_error_ok alguna herramienta devolvió error cuando se esperaba uno
Las preguntas con manual_review (error / información ausente) quedan 'pendiente' hasta revisar la
respuesta contra manual_criterion y llenar la columna manual_ok.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import time
from pathlib import Path
from typing import Any, Callable

from src.config import PROJECT_ROOT

QUESTIONS_PATH = PROJECT_ROOT / "tests/agent_questions.json"
OUT_CSV = PROJECT_ROOT / "results/agent_eval.csv"
OUT_SUMMARY = PROJECT_ROOT / "results/agent_eval_summary.json"
COLUMNS = ["id", "category", "question", "llm_model", "embedding_backend", "tools_expected", "tools_called",
           "tools_ok", "citation_ok", "numeric_ok", "tool_error_ok", "agent_error", "sources_cited",
           "result", "manual_criterion", "manual_ok", "answer"]
CRITERIA = ("tools_ok", "citation_ok", "numeric_ok", "tool_error_ok")


def numbers_in(text: str) -> list[float]:
    """Todos los valores numéricos posibles del texto (admite 1.069,82 / 1,069.82 / 1069.82 / 1.600)."""
    values: list[float] = []
    for token in re.findall(r"\d[\d.,]*\d|\d", text or ""):
        if "." in token and "," in token:
            decimal = "." if token.rfind(".") > token.rfind(",") else ","
            thousands = "," if decimal == "." else "."
            candidates = [token.replace(thousands, "").replace(decimal, ".")]
        elif token.count(".") > 1 or token.count(",") > 1:
            candidates = [re.sub(r"[.,]", "", token)]
        elif "." in token or "," in token:
            sep = "." if "." in token else ","
            whole, frac = token.split(sep)
            candidates = [f"{whole}.{frac}"]
            if len(frac) == 3:                       # '1.600' puede ser 1600 (miles) o 1.600
                candidates.append(whole + frac)
        else:
            candidates = [token]
        for candidate in candidates:
            try:
                values.append(float(candidate))
            except ValueError:
                pass
    return values


def has_number(text: str, target: float, tol: float = 0.6, allow_km: bool = False) -> bool:
    values = numbers_in(text)
    if any(abs(v - target) <= tol for v in values):
        return True
    return allow_km and any(abs(v - target / 1000) <= 0.006 for v in values)


def _args_match(step_args: dict[str, Any], expected: dict[str, Any]) -> bool:
    for key, value in expected.items():
        actual = step_args.get(key)
        if actual is None and key == "algorithm":
            actual = "astar"                           # valor por defecto del contrato
        if str(actual).lower() != str(value).lower():
            return False
    return True


def grade(question: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
    """Califica una respuesta. Cada criterio es True/False, o 'n/a' si no aplica a la pregunta."""
    trace, answer = result.get("tool_trace", []), result.get("answer", "")
    called = [step["tool"] for step in trace]
    marks: dict[str, Any] = {key: "n/a" for key in CRITERIA}

    expected_tools = question.get("expected_tools", [])
    if expected_tools:
        ok = all(tool in called for tool in expected_tools)
        for tool, expected in question.get("expected_args", {}).items():
            ok = ok and any(_args_match(step["arguments"], expected) for step in trace if step["tool"] == tool)
        marks["tools_ok"] = ok

    if question.get("expect_citation_from"):
        wanted = set(question["expect_citation_from"])
        marks["citation_ok"] = any(source.get("document_id") in wanted for source in result.get("sources", []))

    numeric_checks = []
    if "expected_distance_m" in question:
        target = question["expected_distance_m"]
        tool_distances = [step["result"].get("distance_m") for step in trace
                          if step["tool"] == "plan_route" and step["ok"]]
        tool_distances += [step["result"][algo].get("distance_m") for step in trace
                           if step["tool"] == "get_route_metrics" and step["ok"] for algo in ("astar", "dijkstra")]
        numeric_checks.append(any(d is not None and abs(d - target) <= 0.5 for d in tool_distances)
                              and has_number(answer, target, allow_km=True))
    for target in question.get("expected_numbers", []):
        numeric_checks.append(has_number(answer, float(target), tol=0.01))
    if numeric_checks:
        marks["numeric_ok"] = all(numeric_checks)

    if question.get("expect_tool_error"):
        marks["tool_error_ok"] = any(not step["ok"] for step in trace)

    applicable = [value for value in marks.values() if value != "n/a"]
    if result.get("error"):
        verdict = "fallo"
    elif question.get("manual_review"):
        verdict = "pendiente"
    else:
        verdict = "acierto" if applicable and all(applicable) else "fallo"
    return {**marks, "result": verdict, "called": called}


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    auto = [row for row in rows if row["result"] in ("acierto", "fallo")]
    summary: dict[str, Any] = {
        "total_questions": len(rows),
        "auto_graded": {"correct": sum(r["result"] == "acierto" for r in auto), "of": len(auto)},
        "pending_manual_review": sum(r["result"] == "pendiente" for r in rows),
        "criteria": {},
    }
    for key in CRITERIA:
        applicable = [row for row in rows if row[key] != "n/a"]
        summary["criteria"][key] = {"passed": sum(row[key] is True for row in applicable),
                                    "applicable": len(applicable)}
    return summary


def evaluate(questions: list[dict[str, Any]], ask_fn: Callable[[str], dict[str, Any]],
             llm_model: str = "", backend: str = "", sleep_s: float = 0.0) -> list[dict[str, Any]]:
    rows = []
    for index, question in enumerate(questions):
        if index and sleep_s:
            time.sleep(sleep_s)
        result = ask_fn(question["question"])
        graded = grade(question, result)
        rows.append({
            "id": question["id"], "category": question["category"], "question": question["question"],
            "llm_model": llm_model, "embedding_backend": backend,
            "tools_expected": ";".join(question.get("expected_tools", [])),
            "tools_called": ";".join(graded["called"]),
            **{key: graded[key] for key in CRITERIA},
            "agent_error": result.get("error") or "",
            "sources_cited": ";".join(source["id"] for source in result.get("sources", [])),
            "result": graded["result"], "manual_criterion": question.get("manual_criterion", ""),
            "manual_ok": "", "answer": result.get("answer", "").replace("\n", " "),
        })
    return rows


def write_outputs(rows: list[dict[str, Any]], csv_path: Path = OUT_CSV, summary_path: Path = OUT_SUMMARY) -> dict:
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    summary = summarize(rows)
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary


def main() -> None:
    from src.agent import tools
    from src.agent.agent import ask
    from src.agent.llm import OpenAICompatibleClient

    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--questions", type=Path, default=QUESTIONS_PATH)
    parser.add_argument("--sleep", type=float, default=0.0, help="Segundos entre preguntas (límites de tasa).")
    args = parser.parse_args()

    questions = json.loads(args.questions.read_text(encoding="utf-8"))
    client = OpenAICompatibleClient()           # falla con mensaje claro si falta configuración
    backend = tools.get_index().meta["backend"]
    rows = evaluate(questions, lambda text: ask(text, client=client), client.config.model, backend, args.sleep)
    summary = write_outputs(rows)

    for row in rows:
        print(f"{row['id']} [{row['category']}] {row['result']:<9} tools={row['tools_called'] or '-'}")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"\nCSV: {OUT_CSV}\nRevisa a mano las filas 'pendiente' y llena manual_ok.")


if __name__ == "__main__":
    main()
