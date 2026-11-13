# Copiloto de movilidad de Medellín

Proyecto final de **SI3003 – Inteligencia Artificial** (EAFIT, 2026-1). Un copiloto de movilidad para un extracto
pequeño del centro de Medellín:

- **Parte 1 (técnica clásica):** rutas de menor distancia con **A\*** y **Dijkstra** implementados por el equipo
  (`src/routing.py`), sobre una red vial real de OpenStreetMap, con comparación en nodos expandidos y tiempo.
- **Parte 2 (IA moderna):** un **agente LLM con RAG** sobre documentos oficiales del Metro de Medellín y cuatro
  herramientas (`plan_route`, `get_route_metrics`, `find_nodes`, `search_documents`), con citas a las fuentes.
- **Dashboard Streamlit** (`app.py`): selección de origen y destino, mapa de la ruta, comparación A\* vs Dijkstra y chat.

> **Aviso:** herramienta académica. Las rutas se calculan solo por distancia (sin tráfico, tiempos, tarifas ni
> emisiones) y el asistente puede equivocarse. No constituye consejo de movilidad, seguridad, legal ni médico;
> consulta siempre la información oficial del Metro de Medellín.

## Inicio rápido

Requiere Python 3.10 o superior. Desde la raíz del repositorio:

```bash
# 1. Entorno virtual
python -m venv .venv
source .venv/bin/activate          # macOS/Linux
.venv\Scripts\Activate.ps1         # Windows PowerShell

# 2. Dependencias
pip install -r requirements.txt

# 3. Clave del LLM (solo para el chat; las rutas funcionan sin ella)
cp .env.example .env               # Windows: copy .env.example .env
#    edita .env con LLM_API_KEY, LLM_BASE_URL y LLM_MODEL (ver más abajo)

# 4. Aplicación
streamlit run app.py               # abre http://localhost:8501
```

El repositorio ya incluye los datos (`data/`), el corpus (`corpus/`) y el **índice RAG construido** (`data/index/`),
así que no hace falta descargar ni construir nada para usar la aplicación.

### Configurar el LLM

El agente usa cualquier API compatible con *chat completions* que soporte llamadas a herramientas. Ejemplo con Groq
(capa gratuita; clave en https://console.groq.com):

```
LLM_API_KEY=tu_clave
LLM_BASE_URL=https://api.groq.com/openai/v1
LLM_MODEL=openai/gpt-oss-120b
```

`.env` está en `.gitignore`: **nunca subas tu clave**. Sin clave, el chat responde que falta configurarla y el resto
de la aplicación sigue funcionando. Los modelos disponibles varían por cuenta; `GET {LLM_BASE_URL}/models` los lista.
La capa gratuita limita los tokens por minuto: si el chat devuelve un error temporal, espera unos segundos.

### Reconstruir el índice (opcional)

```bash
python -m scripts.agent.build_index --backend hashing   # sin descargas; recuperación léxica
```

El índice incluido usa el backend `hashing` (`hashing-tfidf-4096`). Con `pip install sentence-transformers` y
`--backend sentence-transformers` se obtienen embeddings semánticos (descarga cientos de MB); el índice resultante
sería distinto al incluido.

## Qué se puede hacer en la aplicación

1. **Barra lateral:** elegir un par de prueba o nodos libres, y el algoritmo (A\*, Dijkstra o ambos); pulsar
   *Calcular ruta*.
2. **Mapa:** ruta sobre OpenStreetMap (azul = Dijkstra, rojo = A\*) y tabla de distancia, nodos expandidos y tiempo.
3. **Comparación A\* vs Dijkstra:** gráficos del par elegido y resumen de los 10 pares de evaluación.
4. **Asistente:** preguntas sobre rutas (por id de nodo o nombre de calle) y sobre el Metro. Muestra las fuentes
   citadas y la traza de herramientas.

## Pruebas y verificación

```bash
python -m scripts.check_contracts              # valida los contratos load_graph / plan_route / get_route_metrics / ask
python -m unittest discover -s tests -t .      # pruebas automáticas (no requieren red ni clave)
python -m scripts.agent.run_agent_eval --sleep 25   # evaluación del agente (12 preguntas; requiere .env)
```

- Resultados de rutas: `results/routes.csv` · método: `docs/02_modelo.md`
- Evaluación del agente: `results/agent_eval.csv` y `results/agent_eval_summary.json` · diseño: `docs/03_agente.md`
- Verificación de la integración final: `docs/verificacion_final.md`

> Nota: algunos proveedores (p. ej. Groq) rechazan con HTTP 403 el `User-Agent` por defecto de `urllib`. `app.py`
> lo fija al arrancar; si ejecutas los scripts de `scripts/agent/` directamente contra uno de ellos, verás ese error.

## Estructura

| Ruta | Contenido |
|---|---|
| `app.py` | Dashboard Streamlit (interfaz e integración) |
| `src/data.py`, `src/domain/`, `src/application/`, `src/infrastructure/` | Carga y validación del grafo |
| `src/routing.py` | A\* y Dijkstra propios, `plan_route`, `get_route_metrics` |
| `src/agent/` | Agente: `agent.py` (`ask`), `rag.py`, `tools.py`, `llm.py` |
| `data/raw/`, `data/processed/`, `data/index/` | Datos OSM, grafo procesado, índice RAG, `test_pairs.json` |
| `corpus/` | Documentos del Metro de Medellín y `sources.csv` |
| `results/` | Métricas de rutas y evaluación del agente |
| `docs/` | Documentación por bloque, `README_tecnico.md` (detalle de datos y corpus) |

## Datos y fuentes

- **Red vial:** OpenStreetMap (extracto del centro de Medellín), copia local con su hash y procedencia en
  `data/raw/*.source.json`. © colaboradores de OpenStreetMap, licencia ODbL.
- **Corpus:** documentos públicos del Metro de Medellín (títulos, URL y fecha de consulta en `corpus/sources.csv`).
- Detalle y limitaciones: `docs/01_datos.md`, `docs/FUENTES.md`.

## Limitaciones

- Una sola zona pequeña; el costo es solo la distancia en metros (sin tráfico, pendiente, modo de transporte ni tarifas).
- El corpus tiene pocos documentos; si no respaldan una respuesta, el agente debe decirlo, pero el modelo puede
  fallar o resumir mal horarios y reglas. Verifica en la fuente citada.
- La recuperación del índice incluido es léxica, no semántica.
- La capa gratuita del proveedor limita las peticiones por minuto.
- Los tiempos de ejecución (ms) son de una sola corrida y varían entre ejecuciones; las comparaciones robustas son
  las de nodos expandidos.

## Uso de IA generativa

Declarado en [`DECLARACION_IA.md`](DECLARACION_IA.md).

## Equipo

Isabella (datos y corpus) · Wendy (algoritmos) · Oriana (agente y RAG) · Ana (aplicación, integración y entrega).
