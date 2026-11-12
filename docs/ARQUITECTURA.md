# Arquitectura y decisiones de código

Se usa una arquitectura por capas con entidades de dominio independientes y dependencias orientadas hacia ellas. El objetivo es cambiar un origen de datos sin cambiar el grafo que utilizará Wendy. No se necesita un framework, un servidor ni una carpeta de servicios para este bloque.

| Capa | Módulo | Decisión |
|---|---|---|
| Dominio | `domain/models.py` | Dataclasses y validación al construir objetos |
| Dominio | `domain/geo.py` | Una única función de distancia, reutilizable para la heurística |
| Aplicación | `application/ports.py` | `GraphReader` desacopla el caso de uso del formato de almacenamiento |
| Aplicación | `application/datasets.py` | Carga a través del puerto y controles de conectividad |
| Infraestructura | `infrastructure/json_store.py` | Adaptador JSON que implementa el puerto |
| Infraestructura | `infrastructure/osm.py` | Traduce XML y etiquetas OSM a entidades |
| Infraestructura | `infrastructure/http_client.py` | Descarga HTTPS acotada y reemplazo atómico del archivo |
| Infraestructura | `infrastructure/provenance.py` | Hash, tamaño, URL y fecha de captura |
| Infraestructura | `infrastructure/corpus.py` | Extracción de PDF/HTML y exportación con fuentes |
| Composición | `src/data.py` y `scripts/` | Conectan adaptadores y casos de uso; exponen comandos |

`domain/` no importa infraestructura ni aplicación. `application/` depende de dominio y de un protocolo, no de JSON o HTTP. `src/data.py` es la raíz de composición y fachada estable: allí se elige el adaptador concreto. Los comandos son explícitos; importar un módulo no dispara descargas ni crea archivos.

Los identificadores son strings para evitar conversiones inconsistentes. `Graph.nodes` indexa nodos por id y `Graph.adjacency` ofrece aristas salientes. Esto evita recorrer todas las aristas en cada paso de A*. Los nodos y aristas son inmutables; el contenedor Graph debe tratarse como de solo lectura después de cargarlo.

Se mantienen los nodos de geometría de OSM. Cada arista mide la distancia entre dos nodos consecutivos mediante haversine con radio 6 371 008.8 m, sin redondear el costo almacenado. A* puede usar la misma función entre un nodo y la meta: la desigualdad triangular la hace una cota inferior respecto a la suma de estos segmentos. Wendy deberá comprobar y documentar la igualdad de costos con Dijkstra y usar tolerancias para coma flotante.

El BFS incluido solo verifica alcanzabilidad y genera casos; no calcula la ruta óptima ni sustituye la implementación exigida a Wendy. No se usa NetworkX u OSMnx para resolver rutas.

Errores de datos se expresan como `DataValidationError`; errores HTTP como `DownloadError`. Los comandos terminan con error si no pueden preparar datos válidos. Nunca sustituyen una descarga fallida por datos ficticios.

Para próximos bloques: Wendy puede añadir `domain/routing.py` o `src/routing.py` como fachada y mantener el resultado definido en CONTRATOS. Oriana puede añadir adaptadores LLM y RAG sin alterar las entidades. Ana consume las fachadas desde Streamlit.
