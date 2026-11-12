# Problema datos y preparación

El proyecto propone un copiloto académico de movilidad para un extracto pequeño del centro de Medellín. El objetivo del MVP es comparar rutas de menor distancia calculadas con A* y Dijkstra implementados por el equipo, y complementar la consulta con un asistente basado en documentos oficiales del Metro. Esta entrega cubre la preparación de datos y del corpus; todavía no presenta resultados de los algoritmos ni del agente.

## Fuente y alcance

La red se obtuvo de OpenStreetMap mediante su API de mapas, con bounding box `-75.574,6.247,-75.566,6.255` en orden oeste, sur, este, norte. Se conservó el archivo OSM XML original y un registro de URL, fecha, tamaño y SHA-256. La copia preparada contiene **696 nodos y 858 aristas dirigidas**. Los datos corresponden a vías reales de Colombia; se atribuyen a OpenStreetMap contributors bajo ODbL 1.0.

## Preparación y controles

Se seleccionaron vías de categorías admitidas para un modelo simplificado de automóvil y se excluyeron accesos explícitamente restringidos según la jerarquía de etiquetas y sentidos reversibles o desconocidos. Se mantuvieron únicamente segmentos con ambos nodos dentro del extracto, se eliminaron autociclos y nodos sin segmentos conservados, y se respetaron `oneway=yes`, `oneway=-1` y rotondas. Los cruces geométricos solo conectan cuando comparten id de nodo OSM. Las vías bidireccionales generan aristas en ambos sentidos.

Cada costo se calculó con haversine entre puntos consecutivos, en metros y sin redondear durante el almacenamiento. La arquitectura separa dominio, casos de uso y adaptadores. `load_graph()` lee JSON locales sin conexión. Se verificaron identificadores, extremos existentes, coordenadas y costos finitos no negativos. También se eligieron 10 pares distintos con alcanzabilidad dirigida por BFS para la evaluación posterior; el BFS no calcula rutas óptimas.

El EDA detectó dos componentes débilmente conexas de 694 y 2 nodos, y 14 nodos sin salidas. Estos hechos se conservaron como limitaciones de la red; no se inventaron conexiones para unirlos. La longitud media de arista dirigida es aproximadamente 18.96 m, porque se conservan nodos de geometría y no solo intersecciones. Los conteos por tipo de vía y las verificaciones están en `results/data_validation.json` y `results/eda.json`.

## Corpus y limitaciones

Se descargaron tres PDF oficiales del Metro y una captura de su página de usuarios, con 9 287 palabras extraídas y 23 registros por página o documento web. Se guardaron los originales, texto, URL, título, página, notas de versión y hashes. Estos datos se entregan a Oriana para fragmentación, embeddings y recuperación. La preparación del corpus no constituye aún un sistema RAG.

Los documentos históricos pueden diferir de la información posterior; el agente deberá distinguir versión y fecha y no afirmar vigencia que no pueda verificar. La red es vial, no una red multimodal del Metro; no se modelan tráfico, tiempos, tarifas, giros prohibidos, barreras o todas las restricciones condicionales. El óptimo futuro será dentro de este extracto y para el costo geométrico definido. No se presenta como navegación operativa.

Fuentes: https://www.openstreetmap.org/copyright y las cuatro URLs oficiales registradas en `corpus/sources.csv`. Captura registrada el 9 de noviembre de 2026, hora de Colombia.
