# Agente LLM con RAG y herramientas (Bloque 3 - Oriana)

## Diseño

El agente (`src/agente/agent.py`) recibe una pregunta y el historial, y ejecuta un ciclo de *tool calling*: el modelo decide si responde o llama una herramienta, el sistema ejecuta la herramienta y le devuelve el resultado, y el ciclo se repite hasta que hay respuesta final. El límite es de **5 llamadas al modelo** por pregunta; si se alcanza, el agente lo comunica en lugar de seguir. `ask(message, history)` devuelve `answer`, `sources` (título, URL, página y fragmento), `tool_trace` (herramienta, argumentos y resultado completo de cada paso) y un campo adicional `error` para que la interfaz pueda mostrar fallos de forma comprensible.

El proveedor se aísla en `src/agente/llm.py`: cualquier API compatible con *chat completions* y *tool calling* se configura con `LLM_API_KEY`, `LLM_BASE_URL` y `LLM_MODEL` en `.env` (fuera de Git). Las pruebas automáticas usan un modelo simulado, por lo que no requieren red ni claves.

## Herramientas

Las cuatro herramientas calculan resultados reales y no dependen del modelo: `plan_route` y `get_route_metrics` envuelven los A* y Dijkstra propios del Bloque 2; `find_nodes` traduce nombres de calle o intersecciones a ids de nodo del grafo (el usuario rara vez conoce los ids de OpenStreetMap); `search_documents` consulta el índice documental. El modelo recibe una vista compacta (sin la lista completa de nodos) y el `tool_trace` conserva el camino completo para dibujar el mapa en el dashboard.

## RAG

El corpus son los 4 documentos del Metro de Medellín preparados en el Bloque 1 (23 registros por página). Cada registro se divide en fragmentos de 140 palabras con 40 de solapamiento, lo que produce 97 fragmentos que conservan título, URL, página, fecha de captura y la nota de versión del documento. Los fragmentos se convierten en vectores y se guardan en `data/index/`; la búsqueda usa similitud coseno, devuelve los k mejores y descarta los que quedan por debajo de un umbral mínimo por backend. El índice guarda el backend, el modelo y el hash del corpus, y se rechaza si el corpus cambió.

- **Backend de embeddings:** [COMPLETAR con lo que diga `data/index/index.json`: `sentence-transformers` con `paraphrase-multilingual-MiniLM-L12-v2`, o el respaldo `hashing`]. El respaldo `hashing` es TF-IDF léxico, no semántico; si se usó, debe decirse así.
- **Umbral mínimo:** 0.30 para sentence-transformers (valor inicial sin calibrar con este corpus) y 0.07 para hashing (calibrado con consultas de prueba).

**Citas.** Cada fragmento recuperado recibe un `source_id` (S1, S2...) válido solo durante esa pregunta. El modelo debe citar con esas marcas y `ask()` devuelve únicamente las fuentes realmente citadas; una marca inexistente se ignora. Si los pasajes no respaldan la respuesta, el *prompt* le exige decirlo en vez de responder de memoria. Los documentos son históricos y a veces se contradicen (por ejemplo, horarios de bicicletas de 2015 frente a las condiciones de la funcionalidad Bici); por eso cada fragmento lleva su nota de versión y el modelo debe mencionar ambos cuando haya conflicto. El texto de los pasajes se trata como información, no como instrucciones.

## Evaluación

Son 12 preguntas fijas (`tests/agent_questions.json`): 4 de rutas, 3 documentales con cita, 2 que encadenan ruta y métricas, y 3 de error o información ausente. `scripts/agente/run_agent_eval.py` las ejecuta con el modelo real y registra en `results/agent_eval.csv` la herramienta esperada y la llamada, la cita, la verificación numérica contra lo que devolvió la herramienta y el resultado. Los criterios que no aplican a una pregunta quedan como `n/a` y no cuentan como aciertos. Las 3 preguntas de error o ausencia se califican a mano con el criterio escrito en el CSV, porque que el agente "diga que no sabe" no se puede verificar de forma automática confiable.

**Resultados:** [COMPLETAR tras ejecutar `python -m scripts.agente.run_agent_eval`: aciertos automáticos X de 9; herramienta correcta X de N aplicables; cita correcta X de 3; verificación numérica X de N; y revisión manual X de 3. Indicar el modelo LLM y el backend de embeddings usados.]

## Limitaciones

- La calidad de las respuestas depende del modelo configurado; con temperatura 0 los resultados son más estables pero no garantizados idénticos entre ejecuciones.
- El corpus es pequeño y parcialmente histórico: las tarifas y horarios deben contrastarse con la fuente oficial vigente.
- La recuperación puede fallar con preguntas muy generales o con sinónimos poco comunes, sobre todo con el respaldo léxico.
- Las rutas usan solo distancia y respetan los sentidos de circulación del extracto de OpenStreetMap; por eso puede no haber ruta dirigida entre dos nodos aunque exista la inversa.
- Los documentos del Metro no se conectan al grafo vial: el agente no ubica estaciones ni calcula recorridos del Metro.
