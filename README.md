# Copiloto de movilidad de Medellín

Proyecto académico de Inteligencia Artificial que utiliza datos reales de Medellín para explorar rutas de menor distancia y consultar información documental del sistema Metro.

La solución contempla algoritmos de búsqueda implementados por el equipo, un agente basado en modelos de lenguaje con recuperación documental —RAG— y una interfaz interactiva para consultar rutas, visualizar resultados y conversar con el asistente.

## Objetivo

Desarrollar un prototipo reproducible que permita:

- Representar una zona de Medellín mediante un grafo vial dirigido y ponderado.
- Calcular rutas de menor distancia con A* y Dijkstra.
- Comparar los algoritmos mediante distancia, nodos expandidos y tiempo de ejecución.
- Consultar documentos oficiales del Metro mediante un agente con fuentes verificables.
- Presentar los resultados mediante visualizaciones y una interfaz conversacional.

## Alcance

La red geográfica corresponde a un extracto pequeño del centro de Medellín.

Los datos de OpenStreetMap representan calles y conexiones viales. Los documentos del Metro constituyen el corpus del asistente; no representan una red de recorridos ferroviarios ni determinan los costos de las calles.

El costo de cada arista es su distancia geométrica en metros. El proyecto no incorpora tráfico en tiempo real, tiempos de viaje, tarifas ni emisiones.

## Estado de implementación

| Componente | Estado |
|---|---|
| Datos viales reales y copia local de los originales | Implementado |
| Grafo dirigido con coordenadas y distancias | Implementado |
| Validación de integridad y procedencia | Implementado |
| Generación de pares de prueba alcanzables | Implementado |
| Descarga y extracción del corpus documental | Implementado |
| Estadísticas descriptivas y de conectividad | Implementado |
| Pruebas automatizadas del módulo de datos | Implementado |
| A* y Dijkstra con evaluación comparativa | Pendiente de integración |
| Agente LLM con RAG y herramientas | Implementado (evaluación con LLM real: ver `docs/03_agente.md`) |
| Dashboard, visualizaciones y chat | Pendiente de integración |

La versión actual se ejecuta mediante comandos de consola. Las instrucciones del agente y del dashboard se incorporarán cuando esos componentes estén disponibles.

## Tecnologías

| Tecnología | Uso |
|---|---|
| Python 3.10 o superior | Procesamiento y lógica del proyecto |
| Biblioteca estándar de Python | XML, JSON, HTTP, geometría y pruebas |
| pypdf | Extracción de texto de archivos PDF |
| Beautiful Soup | Extracción del contenido HTML |
| OpenStreetMap | Fuente de datos geográficos |
| Documentos oficiales del Metro de Medellín | Corpus documental |

Las dependencias y sus versiones se encuentran en `requirements.txt`.

## Instalación

### Clonar el repositorio

```bash
git clone https://github.com/OrianaVR/Proyecto_Final_IA_si3003.git
cd Proyecto_Final_IA_si3003
```

Los siguientes comandos deben ejecutarse desde la carpeta que contiene `README.md`, `requirements.txt`, `src/` y `scripts/`.

### Crear el entorno en macOS o Linux

```bash
python3 --version
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

### Crear el entorno en Windows PowerShell

```powershell
py --version
py -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

En cada terminal nueva debe activarse nuevamente el entorno virtual.

El procesamiento local de datos no necesita credenciales. `.env.example` contiene variables reservadas para la configuración del futuro agente LLM.

## Ejecución

### Consultar los datos del grafo

```bash
python -m scripts.demo_data
```

Muestra el tamaño del grafo, un par origen y destino válido, las coordenadas del origen y sus vecinos salientes.

Para la copia incluida, la salida comienza con:

```text
Grafo local: 696 nodos y 858 aristas
```

Este comando inspecciona la red; no calcula una ruta óptima.

### Validar los datos

```bash
python -m scripts.validate
```

Comprueba la integridad del grafo y del corpus, incluyendo:

- Existencia de los extremos de las aristas.
- Coherencia de las distancias.
- Alcanzabilidad de los pares de prueba.
- Hashes de los archivos originales.
- Correspondencia entre los textos extraídos y los registros documentales.

La salida incluye:

```json
{
  "status": "ok",
  "nodes": 696,
  "directed_edges": 858,
  "test_pairs": 10,
  "corpus_documents": 4,
  "corpus_records": 23
}
```

El reporte completo se guarda en `results/data_validation.json`.

### Generar estadísticas descriptivas

```bash
python -m scripts.describe_data
```

Calcula componentes débilmente conexas, nodos sin salidas y cantidad de nodos alcanzables desde los orígenes de prueba.

Los resultados se guardan en `results/eda.json`.

## Agente LLM con RAG y herramientas

El agente (`src/agente/agent.py`) combina un modelo de lenguaje con cuatro herramientas reales y un índice
documental local sobre los documentos del Metro. Interfaz: `ask(message, history)` devuelve
`answer`, `sources` (título, URL, página y fragmento) y `tool_trace` (más un campo `error`).

### Configuración

1. Copia `.env.example` a `.env` y completa `LLM_API_KEY` y `LLM_MODEL` (y `LLM_BASE_URL` si no usas OpenAI).
   El proveedor debe ser compatible con la API de chat completions y soportar llamadas a herramientas.
2. Construye el índice documental (la primera vez descarga el modelo de embeddings):

```bash
python -m scripts.agente.build_index
```

El backend usado queda registrado en `data/index/index.json`. Con `--backend hashing` no se descarga nada,
pero la recuperación es léxica (no semántica): decláralo si lo usas.

### Probar sin interfaz

```bash
python -m scripts.agente.demo_tools      # herramientas y recuperación, sin LLM ni claves
python -m scripts.agente.ask_cli         # conversación con el agente (necesita .env)
python -m scripts.agente.run_agent_eval  # 12 preguntas fijas -> results/agent_eval.csv
```

### Herramientas del agente

| Herramienta | Qué hace |
|---|---|
| `plan_route` | Ruta de menor distancia con A* o Dijkstra (Bloque 2) |
| `get_route_metrics` | Compara A* y Dijkstra sobre el mismo par |
| `find_nodes` | Convierte nombres de calle o intersecciones en ids de nodo |
| `search_documents` | Recupera fragmentos del corpus del Metro con su fuente |

Más detalles de diseño y evaluación en `docs/03_agente.md`.

## Pruebas automatizadas

```bash
python -m unittest discover -s tests -v
```

La versión actual contiene 13 pruebas. El resultado esperado es:

```text
Ran 13 tests
OK
```

Las pruebas verifican:

- Coordenadas y distancias válidas.
- Identificadores y extremos de las aristas.
- Detección de duplicados.
- Interpretación de sentidos de circulación.
- Restricciones básicas de acceso.
- Recorte de la red al área seleccionada.
- Carga local sin llamadas HTTP.
- Alcanzabilidad de los pares.
- Reconstrucción de los datos.
- Detección de archivos originales alterados.

La comparación de distancias admite una tolerancia absoluta de `1e-8` metros para contemplar diferencias de precisión entre plataformas. Los identificadores, la topología, los metadatos y los pares deben coincidir.

## Datos geográficos

### Fuente

La red se obtuvo de OpenStreetMap mediante un extracto XML:

https://api.openstreetmap.org/api/0.6/map?bbox=-75.574,6.247,-75.566,6.255

OpenStreetMap es una fuente abierta colaborativa. No constituye una base de datos gubernamental.

### Cobertura

Las coordenadas utilizan WGS84.

| Límite | Coordenada |
|---|---:|
| Oeste | -75.574 |
| Sur | 6.247 |
| Este | -75.566 |
| Norte | 6.255 |

La copia incluida contiene:

| Elemento | Cantidad |
|---|---:|
| Nodos | 696 |
| Aristas dirigidas | 858 |
| Pares origen y destino | 10 |

### Preparación

Cada nodo conserva su identificador y sus coordenadas. Cada arista conecta dos nodos consecutivos de una vía y almacena su distancia en metros, calculada mediante haversine.

Se conservan los sentidos de circulación admitidos por el procesamiento. Las vías bidireccionales generan aristas en ambos sentidos y las aristas paralelas mantienen identificadores independientes.

Los cruces geométricos solo se conectan cuando comparten un nodo OSM. Se conservan únicamente segmentos cuyos extremos estén dentro del área seleccionada.

Los pares de prueba se verifican mediante una búsqueda de conectividad. Esta comprobación no sustituye el cálculo de rutas óptimas.

### Archivos

| Ruta | Contenido |
|---|---|
| `data/raw/medellin_centro.osm` | Extracto geográfico original |
| `data/raw/medellin_centro.osm.source.json` | Procedencia, fecha, tamaño y hash |
| `data/processed/nodes.json` | Nodos y coordenadas |
| `data/processed/edges.json` | Aristas dirigidas y distancias |
| `data/processed/metadata.json` | Fuente, cobertura y metadatos |
| `data/test_pairs.json` | Pares para evaluación controlada |

## Corpus documental

El corpus contiene tres PDF y una captura HTML del sitio oficial del Metro de Medellín.

| Documento | Fuente |
|---|---|
| Reglamento del Usuario | [PDF oficial](https://www.metrodemedellin.gov.co/hubfs/reglamento-del-usuario-11052019-1.pdf) |
| Condiciones de uso de la funcionalidad Bici | [PDF oficial](https://www.metrodemedellin.gov.co/hubfs/condiciones-de-uso-funcionalidad-bici-2.pdf) |
| Convivencia de bicicletas en el sistema | [PDF oficial](https://www.metrodemedellin.gov.co/hubfs/NORMAS-CONVIVENCIA-BICI-MAS-METRO-DEF-26-10-2015.pdf) |
| Información y servicios para usuarios | [Página oficial](https://www.metrodemedellin.gov.co/usuarios) |

### Organización

| Ruta | Contenido |
|---|---|
| `corpus/raw/` | Documentos originales |
| `corpus/text/` | Textos extraídos |
| `corpus/sources.csv` | Fuentes y registros de consulta |
| `corpus/manifest.json` | Metadatos, hashes y conteos |
| `corpus/documents.jsonl` | Registros documentales para recuperación |

Cada registro de `documents.jsonl` incluye:

- `document_id`
- `title`
- `url`
- `page_number`
- `text`
- `retrieved_at_utc`
- `version_note`

La numeración PDF corresponde a la posición física de la página, comenzando en 1. Para HTML, `page_number` es `null`.

Estos registros permiten incorporar fragmentación, embeddings y recuperación conservando la información necesaria para citar las fuentes.

## Reproducibilidad

Los originales están incluidos para permitir la preparación local sin nuevas descargas.

```bash
python -m scripts.prepare_data
python -m scripts.prepare_corpus
python -m scripts.describe_data
python -m scripts.validate
python -m unittest discover -s tests -v
```

La extracción del corpus requiere las dependencias instaladas. Estos comandos utilizan las copias locales cuando no se especifica `--download`.

Los hashes SHA-256 permiten comprobar que los originales coincidan con su registro de procedencia.

## Actualización de fuentes

Para obtener una nueva captura con acceso a Internet:

```bash
python -m scripts.prepare_data --download
python -m scripts.prepare_corpus --download
python -m scripts.describe_data
python -m scripts.validate
```

La actualización reemplaza los originales y regenera los datos derivados. Puede modificar los conteos y los pares de prueba.

Para comparar algoritmos se debe utilizar una misma versión del grafo y de los pares. Se recomienda conservar la versión anterior antes de actualizar.

El área puede especificarse en orden oeste, sur, este y norte:

```bash
python -m scripts.prepare_data --download --bbox -75.574 6.247 -75.566 6.255
```

Las fuentes documentales se configuran en `config/corpus_sources.json`.

## Arquitectura

El código separa entidades de dominio, casos de uso y adaptadores de infraestructura.

| Ruta | Responsabilidad |
|---|---|
| `src/domain/` | Entidades, validaciones y geometría |
| `src/application/` | Carga mediante interfaces y controles de conectividad |
| `src/infrastructure/` | HTTP, XML, JSON, extracción y procedencia |
| `src/data.py` | Interfaz pública de carga del grafo |
| `src/config.py` | Rutas y cobertura predeterminada |
| `scripts/` | Comandos de preparación, consulta y validación |
| `config/` | Configuración de fuentes |
| `data/` | Datos geográficos |
| `corpus/` | Documentos y textos |
| `tests/` | Pruebas automatizadas |
| `results/` | Estadísticas y evidencias |
| `docs/` | Documentación técnica y académica |

El dominio no depende de archivos, HTTP ni interfaces gráficas. Los adaptadores convierten los datos externos a las entidades utilizadas por la aplicación.

### Acceso al grafo

```python
from src.data import load_graph

graph = load_graph()
node = graph.nodes["10311382890"]

print(node.latitude, node.longitude)

for edge in graph.adjacency[node.id]:
    print(edge.destination, edge.distance_m)
```

Los identificadores se manejan como cadenas de texto.

| Atributo | Descripción |
|---|---|
| `graph.nodes` | Nodos indexados por identificador |
| `graph.edges` | Aristas dirigidas |
| `graph.adjacency` | Aristas salientes de cada nodo |
| `graph.metadata` | Fuente, cobertura y metadatos |

`load_graph()` consulta únicamente archivos locales y admite un directorio alternativo de datos procesados.

## Evaluación

La evaluación del proyecto contempla:

| Componente | Criterio |
|---|---|
| Búsqueda | Distancia, nodos expandidos y tiempo de ejecución |
| Corrección | Coincidencia del costo óptimo entre A* y Dijkstra |
| Agente | Uso correcto de herramientas, citas y manejo de información ausente |
| Interfaz | Selección de parámetros, visualizaciones y conversación |
| Reproducción | Instalación y ejecución siguiendo este documento |

La evaluación del agente utilizará entre 10 y 15 preguntas fijas. La interfaz deberá ofrecer al menos dos visualizaciones significativas.

Los resultados de búsqueda y del agente se documentarán cuando sus implementaciones estén integradas.

## Limitaciones

- La red cubre una zona pequeña del centro de Medellín.
- El costo representa distancia geométrica, no tiempo de viaje.
- No se incorporan tráfico en tiempo real, tarifas ni emisiones.
- El modelo vial no contempla giros prohibidos, barreras ni todas las restricciones condicionales.
- El grafo puede contener componentes desconectadas y nodos sin salidas.
- La existencia de una ruta de ida no garantiza una ruta de regreso.
- Los documentos históricos pueden diferir de condiciones posteriores.
- La captura web no garantiza información vigente en tiempo real.
- La extracción PDF puede separar palabras o perder la estructura de tablas; las citas deben contrastarse con los originales.

El sistema tiene un alcance académico y experimental y no se presenta como una herramienta de navegación operativa.

## Solución de problemas

| Situación | Acción |
|---|---|
| `python: command not found` | Activar el entorno con `source .venv/bin/activate` en macOS o Linux |
| `No module named src` o `scripts` | Ejecutar los comandos desde la raíz del proyecto |
| Falta `pypdf` o `bs4` | Activar el entorno e instalar `requirements.txt` |
| Faltan archivos procesados | Comprobar los originales y ejecutar `python -m scripts.prepare_data` |
| Un hash no coincide | Revisar si el original fue modificado y recuperar una copia coherente |
| Falla una descarga | Utilizar los originales incluidos y omitir `--download` |

No se deben subir `.venv/`, `.env` ni credenciales al repositorio. Los datos, el corpus y sus metadatos forman parte de la reproducción del proyecto.

## Documentación

- [Datos y preparación](docs/01_datos.md)
- [Arquitectura](docs/ARQUITECTURA.md)
- [Fuentes](docs/FUENTES.md)

La entrega académica debe incluir un informe de máximo cuatro páginas y una declaración del uso de IA generativa que describa las herramientas utilizadas y su propósito.

## Atribución y licencias

© OpenStreetMap contributors.

Los datos geográficos originales y la base derivada se distribuyen bajo [Open Database License ODbL 1.0](https://opendatacommons.org/licenses/odbl/1-0/).

Información adicional: [Copyright de OpenStreetMap](https://www.openstreetmap.org/copyright).

La atribución debe conservarse con los datos y mostrarse en el mapa cuando se incorpore la interfaz.

Los documentos del Metro de Medellín conservan su autoría institucional y condiciones originales. Sus fuentes se registran en `corpus/sources.csv`.

La licencia de los datos no determina automáticamente la licencia del código del proyecto.