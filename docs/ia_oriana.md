# Uso de herramientas de IA - Oriana (Bloque 3)

> Borrador para completar y ajustar a lo que realmente hiciste. La declaración debe reflejar tu proceso, no el de este texto.

## Herramienta

Claude (Anthropic), en la aplicación de chat claude.ai.

## Propósito

Apoyo para diseñar y escribir el borrador del Bloque 3: agente con *tool calling*, RAG local, herramientas, pruebas, scripts de evaluación y documentación.

## Qué generó la herramienta

- Borradores de `src/agent/rag.py`, `src/agent/tools.py`, `src/agent/llm.py`, `src/agent/agent.py`.
- Borradores de `scripts/agent/build_index.py`, `scripts/agent/demo_tools.py`, `scripts/agent/ask_cli.py`, `scripts/agent/run_agent_eval.py`.
- Borradores de `tests/test_rag.py`, `tests/test_tools.py`, `tests/test_agent.py`, `tests/test_agent_eval.py` y `tests/agent_questions.json`.
- Borradores de `docs/03_agente.md` y de esta declaración, y los cambios a `README.md`, `requirements.txt`, `pyproject.toml` y `.env.example`.

## Qué hice yo

[COMPLETAR: qué revisaste, qué ejecutaste, qué cambiaste, qué decidiste (proveedor LLM, modelo, backend de embeddings), cómo verificaste que las herramientas y las citas funcionan, y cómo calificaste a mano las 3 preguntas pendientes.]

## Qué verifiqué

[COMPLETAR: pruebas ejecutadas (`python -m unittest discover -s tests -v`), evaluación con el modelo real (`python -m scripts.agent.run_agent_eval`) y revisión de los resultados.]

## Límites

La herramienta no tuvo acceso al proveedor LLM real ni a los modelos de embeddings durante la redacción: las pruebas automáticas usan un modelo simulado y el índice de prueba usa el respaldo léxico. Los resultados de la evaluación con el modelo real los produje y revisé yo.
