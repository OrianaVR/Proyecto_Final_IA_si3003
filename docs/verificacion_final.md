# Verificación final (Bloque 4)

Registro de lo comprobado al integrar. Solo se anotan resultados de ejecuciones reales.

## Hallazgos de integración

- El agente vive en `src/agent/` (no `src/agent.py`) y `build_index` en `scripts/agent/`; `app.py` importa `src.agent.agent.ask`.
- El índice incluido en `data/index/` fue construido con el backend `hashing` (`hashing-tfidf-4096`, 97 fragmentos),
  no con sentence-transformers. Para consultarlo basta numpy; torch no es necesario para correr la app.
  Reconstruir con sentence-transformers instalado produciría un índice distinto (decisión de Oriana).
- Instalar `requirements.txt` completo descarga torch (`sentence-transformers`) y tardó más de 15 minutos sin terminar;
  se canceló y se instalaron solo las dependencias necesarias.

## Contratos (scripts/check_contracts.py)

`python -m scripts.check_contracts` (venv limpio, sin API key): **todos los chequeos OK**.
- `load_graph()`: 696 nodos y 858 aristas, con id, lat/lon y `distance_m >= 0`.
- `plan_route()` y `get_route_metrics()`: campos correctos y mismo costo óptimo A*/Dijkstra en los 10 pares de `data/test_pairs.json`; nodo inválido devuelve error estructurado.
- `ask()`: devuelve `answer`, `sources` y `tool_trace` (verificado con un cliente simulado; el LLM real requiere API key y no se ha probado).
- No fue necesario ningún adaptador: los contratos coinciden con lo acordado.

## Agente con LLM real (Groq, `openai/gpt-oss-120b`)

- `plan_route`, `get_route_metrics` y `search_documents` se llaman correctamente. Las cifras de `get_route_metrics`
  (A* 115 nodos, Dijkstra 277, 1069.8 m para `pair_01`) coinciden con `results/routes.csv`.
- **Hallazgo 1 (corregido con adaptador en `app.py`)**: Groq responde HTTP 403 (código 1010, Cloudflare) porque
  `src/agent/llm.py` no define `User-Agent` y urllib envía `Python-urllib`. `app.py` instala un opener con
  `User-Agent` propio. Los scripts de `scripts/agent/` no pasan por `app.py` y tendrían el mismo 403 con Groq.
- **Hallazgo 2 (sin resolver)**: `llama-3.3-70b-versatile` no existe en la cuenta usada; los modelos de chat
  disponibles eran `openai/gpt-oss-120b`, `openai/gpt-oss-20b` y `qwen/qwen3.8-27b`.
- **Hallazgo 3 (corregido con aprobación de Ana; avisar a Oriana)**: `gpt-oss-120b` escribe las citas con espacios de ancho cero (`[​S4​]`),
  así que `_CITATION_RE` de `src/agent/agent.py` no las reconocía y `sources` quedaba vacío aunque el texto citaba. Se amplió la expresión para ignorar espacios de ancho cero (cambio de una línea); tras el cambio la app muestra la fuente con título y URL.
- **Hallazgo 4**: la capa gratuita de Groq limita a 8000 tokens por minuto; una pregunta seguida de otras dio HTTP 429.
  Una evaluación de 12 preguntas necesita pausas entre preguntas.

## Revisión visual de la app (Ana, navegador, `pair_01`, A* y Dijkstra)

Confirmado a ojo: mapa con origen, destino y ruta; tabla con 1069.8 m en ambos y 115 vs 277 nodos expandidos;
gráficos de nodos y tiempo; resumen global de los 10 pares (reducción media de nodos con A*: 43.9 %).
Chat: 3 preguntas (documental, ruta+métricas, información ausente). Problemas hallados y corregidos:
- Mapa: la línea de Dijkstra tapaba la de A* (como son idénticas, solo se veía una). Ahora Dijkstra se dibuja primero.
- **Hallazgo 6**: el modelo también cita con corchetes de ancho completo (`【S1】`), que el regex no reconocía y
  dejaba sin lista de fuentes. Se amplió `_CITATION_RE` (mismo cambio que el hallazgo 3).
- El texto "A*" se mostraba como cursiva de markdown; `app.py` lo escapa al mostrar las respuestas.
- Columnas de la tabla acortadas para que no se corte.
- La pregunta de información ausente (metro de Bogotá) fue respondida correctamente: dijo que el corpus no cubre ese dato.
- Sin verificar: que los horarios de bicicletas que dio el modelo coincidan literalmente con el corpus; conviene
  comparar la respuesta con los fragmentos S1 y S4 antes de citarla en el informe.

## Contraste de `docs/02_modelo.md` con `results/routes.csv`

- Nodos expandidos: A* redujo la expansión en los 10 pares (28.44 % a 62.08 %, media 43.93 %); misma distancia y mismo
  camino en los 10. Coincide con lo escrito por Wendy.
- **Discrepancia (tiempo)**: `02_modelo.md` afirma una "clara ventaja" de A* en tiempo. Los datos del CSV no la
  respaldan: A* fue más rápido en solo 5 de 10 pares y la media es 0.733 ms (A*) frente a 0.773 ms (Dijkstra), una
  diferencia dentro del ruido de una sola corrida. En el informe se reporta la ventaja en nodos expandidos y el tiempo
  como empate práctico. No se modificó el documento de Wendy; se avisa para que lo corrija si quiere.

## Documentos ausentes en las ramas (al 12 nov)

- `docs/ia_isabella.md` y `docs/ia_oriana.md` no existen en ninguna rama remota; `DECLARACION_IA.md` los marca como pendientes.
- `docs/README_tecnico.md` conserva el README técnico anterior, que usa nombres `src/agente/` y `scripts/agente/`;
  los nombres reales son `src/agent/` y `scripts/agent/`.

## Evaluación del agente (`results/agent_eval.csv`)

Ejecutada por Ana el 12 nov con `scripts/agent/run_agent_eval.py --sleep 25`, modelo `openai/gpt-oss-120b` (Groq),
índice `hashing`. Resultado automático: **6 de 9** acertadas; herramienta correcta 9/10, cita 3/3, cifras 3/6,
error de herramienta 1/1; 3 preguntas quedan pendientes de revisión manual.
- q01 y q03: la distancia del agente es correcta (1 069.82 y 1 336,34 m) pero el verificador no reconoce el espacio
  como separador de miles ni la coma decimal; el CSV se dejó tal como lo produjo el script.
- q08: fallo real; dio 307 y 587 nodos (correctos) pero no llamó a `plan_route`.
- q10, q11, q12 (revisión manual leyendo las respuestas): no inventó distancia, tarifa de Bogotá ni minutos de tráfico.
  La columna `manual_ok` del CSV **no se llenó**; Ana debe confirmar esta lectura.
- `docs/03_agente.md` conserva dos marcadores `[COMPLETAR]` de Oriana (backend de embeddings y resultados);
  con esta corrida: backend `hashing`, resultados arriba. No se editó su documento.

## Pruebas automáticas y saltos de línea

- `python -m unittest discover -s tests -t .`: 68 pruebas OK.
- **Hallazgo 5 (corregido)**: antes del arreglo fallaban 2 pruebas de `tests/test_data.py` ("El hash del OSM no coincide").
  Causa: en Windows con `core.autocrlf=true` el archivo `data/raw/medellin_centro.osm` se descargaba con CRLF y su
  SHA-256 dejaba de coincidir con `.source.json` (con LF coincide). Se añadió `.gitattributes` (`data/raw/* -text`,
  `corpus/** -text`) para que no se convierta. Afecta a cualquier revisor en Windows.
- `pytest` no está en `requirements.txt`; las pruebas corren con `unittest`.

## Prueba de punta a punta (instalación limpia)

12 nov, Windows, Python 3.11: copia del proyecto sin `.venv` ni `.git` en `C:\si3003_clean` (ruta corta), venv nuevo y
`pip install -r requirements.txt` (salida 0). Resultado: `check_contracts` TODO OK; 68 pruebas OK; la app (probada con
`streamlit.testing`) calcula la ruta sin excepciones, muestra el mensaje de igual distancia óptima y el chat responde
con tabla de A* frente a Dijkstra usando el LLM real.
- La copia incluyó `.env` (con la clave) para probar el chat; sin `.env` el chat avisa que falta configurarlo.
- Un primer intento falló por el límite de 260 caracteres de ruta de Windows (copia en una carpeta temporal muy
  larga). Conviene clonar el repositorio en una ruta corta (p. ej. `C:\proyectos\`).
- No verificado en esta prueba: arranque real de `streamlit run app.py` en un navegador sobre la copia limpia
  (sí se verificó en el entorno de desarrollo, con capturas de Ana) ni la clonación desde GitHub (aún sin push).
