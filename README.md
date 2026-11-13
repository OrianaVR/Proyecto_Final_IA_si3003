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

## Contenido

1. [Qué necesitas antes de empezar](#1-qué-necesitas-antes-de-empezar)
2. [Instalación paso a paso](#2-instalación-paso-a-paso)
3. [Configurar el LLM: API key, URL base y modelo](#3-configurar-el-llm-api-key-url-base-y-modelo)
4. [Ejecutar la aplicación](#4-ejecutar-la-aplicación)
5. [Qué se puede hacer en la aplicación](#5-qué-se-puede-hacer-en-la-aplicación)
6. [Pruebas y evaluación](#6-pruebas-y-evaluación)
7. [Problemas frecuentes](#7-problemas-frecuentes)
8. [Estructura, datos, limitaciones y equipo](#8-estructura-del-repositorio)

---

## 1. Qué necesitas antes de empezar

| Requisito | Detalle |
|---|---|
| **Python 3.11 o superior** | Las dependencias fijadas (numpy, pandas, streamlit) no soportan 3.10. Comprueba con `python --version`. |
| **Git** | Para clonar el repositorio. |
| **Conexión a internet** | Para instalar dependencias y para que el chat llame al proveedor del LLM. Las rutas funcionan sin red. |
| **Una API key de un LLM** | Solo para el **chat**. Sin ella, el mapa, la tabla y los gráficos funcionan igual. Ver sección 3. |
| **Ruta de carpeta corta (Windows)** | Clona en algo como `C:\proyectos\`. Windows limita las rutas a 260 caracteres y carpetas muy anidadas pueden fallar. |

## 2. Instalación paso a paso

> **La descarga de dependencias puede ser lenta.** Según tu conexión y equipo, `pip install -r requirements.txt`
> puede tardar **desde unos segundos hasta varios minutos** (en Windows y con internet lento, más de 10 minutos). Es
> normal que parezca detenido mientras descarga y compila paquetes como numpy, pandas y streamlit. **No lo
> interrumpas.** Si se cancela, vuelve a ejecutar el mismo comando: continúa con lo que ya descargó.
> **No instales `sentence-transformers`**: arrastra PyTorch (cientos de MB) y puede tardar mucho más; no es necesario.

```bash
# 1. Clonar el repositorio
git clone https://github.com/OrianaVR/Proyecto_Final_IA_si3003.git
cd Proyecto_Final_IA_si3003

# 2. Crear y activar el entorno virtual
python -m venv .venv
source .venv/bin/activate          # macOS / Linux
.venv\Scripts\Activate.ps1         # Windows PowerShell
.venv\Scripts\activate.bat         # Windows CMD

# 3. Instalar dependencias (puede demorar, ver el aviso de arriba)
pip install -r requirements.txt

# 4. Crear tu archivo de configuración del LLM
cp .env.example .env               # macOS / Linux
copy .env.example .env             # Windows
```

Después abre `.env` con un editor de texto y completa los tres valores (sección siguiente).

> **Windows PowerShell:** si `Activate.ps1` da error de permisos, ejecuta una vez
> `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` o usa `activate.bat` desde CMD.

El repositorio **ya incluye** los datos (`data/`), el corpus (`corpus/`) y el **índice RAG construido**
(`data/index/`). No hace falta descargar ni construir nada más para usar la aplicación.

## 3. Configurar el LLM: API key, URL base y modelo

El agente funciona con **cualquier servicio compatible con la API de OpenAI** (*chat completions*) que soporte
**llamadas a herramientas** (*tool calling*). Se configura con tres variables en el archivo `.env`:

| Variable | Qué es | Ejemplo (Groq) |
|---|---|---|
| `LLM_API_KEY` | Tu clave personal del proveedor. **Obligatoria** para el chat. | `gsk_...` |
| `LLM_BASE_URL` | URL base de la API del proveedor (sin `/chat/completions` al final). | `https://api.groq.com/openai/v1` |
| `LLM_MODEL` | Nombre exacto del modelo, tal como lo lista el proveedor. | `openai/gpt-oss-120b` |

Ejemplo de `.env` ya listo para Groq (solo pega tu clave):

```
LLM_API_KEY=pega_aquí_tu_clave
LLM_BASE_URL=https://api.groq.com/openai/v1
LLM_MODEL=openai/gpt-oss-120b
```

Reglas del archivo: una variable por línea, formato `NOMBRE=valor`, **sin espacios alrededor del `=`** y sin
comillas. Si `LLM_BASE_URL` queda vacía, el programa usa la de OpenAI (`https://api.openai.com/v1`).

### Opción A (recomendada): Groq, capa gratuita

1. Entra a <https://console.groq.com> y crea una cuenta (correo o Google/GitHub).
2. En el menú lateral abre **API Keys** y pulsa **Create API Key**. Ponle un nombre (por ejemplo `si3003`).
3. **Copia la clave en ese momento** (empieza por `gsk_`): Groq solo la muestra una vez. Si la pierdes, crea otra.
4. Pégala en `.env` como `LLM_API_KEY`. La URL base y el modelo del ejemplo ya sirven.

La capa gratuita limita las peticiones y los tokens por minuto. Ver "Problemas frecuentes".

### Opción B: NVIDIA NIM (capa gratuita)

1. Entra a <https://build.nvidia.com>, inicia sesión y elige un modelo con soporte de *tool calling*.
2. En la página del modelo pulsa **Get API Key** / **Generate API Key** y copia la clave (empieza por `nvapi-`).
3. En `.env`: `LLM_BASE_URL=https://integrate.api.nvidia.com/v1` y `LLM_MODEL=` el identificador que muestra la
   página del modelo (por ejemplo `meta/llama-3.1-70b-instruct`; confírmalo en su página).

### Opción C: Ollama (local, sin cuenta ni costo)

1. Instala Ollama desde <https://ollama.com> y descarga un modelo con herramientas, por ejemplo
   `ollama pull llama3.1`.
2. En `.env`: `LLM_BASE_URL=http://localhost:11434/v1`, `LLM_MODEL=llama3.1` y, aunque Ollama no use clave,
   pon **cualquier texto** en `LLM_API_KEY` (por ejemplo `ollama`): este proyecto exige que no esté vacía.
3. Requiere un equipo con memoria suficiente; los modelos pequeños pueden usar mal las herramientas.

### Opción D: OpenAI u otro proveedor compatible

Crea la clave en <https://platform.openai.com/api-keys>, usa `LLM_BASE_URL=https://api.openai.com/v1` y un modelo
como `gpt-4o-mini`. Cualquier otro servicio sirve si es compatible con *chat completions* y herramientas.

### Cómo saber qué modelos puedes usar

Los modelos disponibles **varían según la cuenta y cambian con el tiempo**. Si el chat responde *model not found*,
lista los tuyos y copia el nombre exacto en `LLM_MODEL`:

```bash
# macOS / Linux (reemplaza la clave y la URL base por las tuyas)
curl -s -H "Authorization: Bearer TU_CLAVE" https://api.groq.com/openai/v1/models
```

```powershell
# Windows PowerShell
Invoke-RestMethod -Uri "https://api.groq.com/openai/v1/models" -Headers @{Authorization="Bearer TU_CLAVE"} |
  Select-Object -ExpandProperty data | Select-Object id
```

### Seguridad de la clave

- `.env` está en `.gitignore`: **nunca subas tu clave** a GitHub, ni la pegues en `.env.example`, el código, el
  informe o capturas de pantalla.
- Si una clave se expone, **revócala** en la consola del proveedor y crea otra.
- Sin clave, la aplicación arranca igual: el chat avisa que falta configurarla y el resto funciona.

## 4. Ejecutar la aplicación

Con el entorno virtual activado y desde la raíz del repositorio:

```bash
streamlit run app.py
```

Se abre en <http://localhost:8501>. Si no abre sola, copia esa dirección en el navegador. Para detenerla, pulsa
`Ctrl + C` en la terminal. La primera carga puede tardar unos segundos mientras se lee el grafo.

## 5. Qué se puede hacer en la aplicación

1. **Barra lateral:** elegir un par de prueba o nodos libres, y el algoritmo (A\*, Dijkstra o ambos); pulsar
   *Calcular ruta*.
2. **Mapa:** ruta sobre OpenStreetMap (azul = Dijkstra, rojo = A\*) y tabla de distancia, nodos expandidos y tiempo.
3. **Comparación A\* vs Dijkstra:** gráficos del par elegido y resumen de los 10 pares de evaluación.
4. **Asistente (chat):** preguntas sobre rutas (por id de nodo o nombre de calle) y sobre el Metro. Muestra las
   fuentes citadas y la traza de herramientas. Requiere la configuración de la sección 3.

Ejemplos de preguntas: *"¿Cuál es la ruta más corta entre el nodo X y el nodo Y y cuántos nodos expandió A\* frente
a Dijkstra?"*, *"¿Qué dicen los documentos sobre llevar bicicletas en el Metro?"*.

## 6. Pruebas y evaluación

```bash
python -m scripts.check_contracts                    # contratos load_graph / plan_route / get_route_metrics / ask
python -m unittest discover -s tests -t .            # 68 pruebas automáticas (sin red ni clave)
python -m scripts.agent.run_agent_eval --sleep 25    # evaluación del agente: 12 preguntas (requiere .env)
```

- La evaluación del agente tarda varios minutos por las pausas (`--sleep 25`) que evitan el límite por minuto.
- Resultados de rutas: `results/routes.csv` · método: `docs/02_modelo.md`
- Evaluación del agente: `results/agent_eval.csv` y `results/agent_eval_summary.json` · diseño: `docs/03_agente.md`
- Informe breve: [`informe.pdf`](informe.pdf)

### Reconstruir el índice RAG (opcional)

```bash
python -m scripts.agent.build_index --backend hashing    # sin descargas; recuperación léxica (TF-IDF)
```

El índice incluido usa el backend `hashing` (`hashing-tfidf-4096`). Los embeddings semánticos
(`--backend sentence-transformers`) requieren instalar `sentence-transformers` (descarga PyTorch, cientos de MB) y
producen un índice distinto; no son necesarios.

## 7. Problemas frecuentes

| Síntoma | Causa probable y solución |
|---|---|
| `pip install` parece congelado | Está descargando. Espera; puede tardar varios minutos. No lo canceles. |
| `No matching distribution` / error de versión | Tu Python es anterior a 3.11. Instala 3.11+ y recrea el `.venv`. |
| El chat dice "Falta configurar el proveedor LLM" | `.env` no existe o `LLM_API_KEY` / `LLM_MODEL` están vacíos. Revisa la sección 3 y reinicia `streamlit run app.py`. |
| `HTTP 401` | Clave incorrecta, vencida o revocada. Genera otra y actualiza `.env`. |
| `HTTP 404` / *model not found* | `LLM_MODEL` no existe en tu cuenta o `LLM_BASE_URL` es incorrecta. Lista los modelos (sección 3). |
| `HTTP 403` (código 1010) | El proveedor rechaza el `User-Agent` de `urllib`. `app.py` ya lo fija; solo ocurre al ejecutar scripts de `scripts/agent/` directamente. |
| `HTTP 429` o error temporal | Límite por minuto de la capa gratuita. Espera 30–60 s y repite. |
| El cambio en `.env` no surte efecto | Detén Streamlit (`Ctrl + C`) y vuelve a lanzarlo. |
| El puerto 8501 está ocupado | `streamlit run app.py --server.port 8502` |
| Error de ruta larga en Windows | Clona el repositorio en una carpeta corta, por ejemplo `C:\proyectos\`. |

## 8. Estructura del repositorio

| Ruta | Contenido |
|---|---|
| `app.py` | Dashboard Streamlit (interfaz e integración) |
| `src/data.py`, `src/domain/`, `src/application/`, `src/infrastructure/` | Carga y validación del grafo |
| `src/routing.py` | A\* y Dijkstra propios, `plan_route`, `get_route_metrics` |
| `src/agent/` | Agente: `agent.py` (`ask`), `rag.py`, `tools.py`, `llm.py` |
| `data/raw/`, `data/processed/`, `data/index/` | Datos OSM, grafo procesado, índice RAG, `test_pairs.json` |
| `corpus/` | Documentos del Metro de Medellín y `sources.csv` |
| `results/` | Métricas de rutas y evaluación del agente |
| `tests/` | Pruebas automáticas y las 12 preguntas fijas del agente |
| `docs/` | Documentación por bloque y `README_tecnico.md` (detalle de datos y corpus) |
| `informe.pdf` | Informe breve de la entrega |
| `DECLARACION_IA.md` | Declaración de uso de IA generativa |

### Datos y fuentes

- **Red vial:** OpenStreetMap (extracto del centro de Medellín), copia local con su hash y procedencia en
  `data/raw/*.source.json`. © colaboradores de OpenStreetMap, licencia ODbL.
- **Corpus:** documentos públicos del Metro de Medellín (títulos, URL y fecha de consulta en `corpus/sources.csv`).
- Detalle y limitaciones: `docs/01_datos.md`, `docs/FUENTES.md`.

### Limitaciones

- Una sola zona pequeña; el costo es solo la distancia en metros (sin tráfico, pendiente, modo de transporte ni tarifas).
- El corpus tiene pocos documentos; si no respaldan una respuesta, el agente debe decirlo, pero el modelo puede
  fallar o resumir mal horarios y reglas. Verifica en la fuente citada.
- La recuperación del índice incluido es léxica, no semántica.
- La capa gratuita del proveedor limita las peticiones por minuto.
- Los tiempos de ejecución (ms) son de una sola corrida y varían entre ejecuciones; las comparaciones robustas son
  las de nodos expandidos.

### Uso de IA generativa

Declarado en [`DECLARACION_IA.md`](DECLARACION_IA.md).

### Equipo

Ana Sofía Angarita Barrios · Oriana Valoyes Renteria
