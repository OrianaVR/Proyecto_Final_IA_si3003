# Declaración de uso de IA generativa

Proyecto final SI3003 – Copiloto de movilidad de Medellín. Cada integrante declara las herramientas de IA
generativa que usó y para qué, conforme al pacto pedagógico. Cada declaración la redacta y responde su autora.

## 1. Isabella: datos y corpus

> **PENDIENTE.** Isabella debe aportar `docs/ia_isabella.md` (herramienta(s) de IA usada(s), propósito, qué
> verificó personalmente). Al momento de cerrar este documento no existe en ninguna rama del repositorio.


## 1. Isabella: datos y corpus

**Herramienta:** ChatGPT con Codex, como asistente de explicación, programación y documentación.

**Para qué lo usé:**

- Recibir explicaciones sobre la organización del proyecto, la representación de la red vial mediante nodos y aristas y la separación entre datos geográficos y corpus documental.
- Apoyar la generación y organización del código para descargar, preparar y cargar los datos de OpenStreetMap, así como extraer el texto de los documentos oficiales del Metro.
- Preparar pruebas automatizadas y comprender sus resultados.
- Diagnosticar una diferencia de precisión numérica entre entornos que hacía fallar la comparación de archivos reconstruidos y ajustar la prueba para comparar las distancias con una tolerancia.
- Elaborar borradores del README, la descripción de los datos, las fuentes y las limitaciones.
- Recibir orientación para configurar el entorno virtual y utilizar Git y GitHub.

**Qué verifiqué personalmente:**

- Creé el entorno virtual e instalé las dependencias en mi Mac.
- Ejecuté `python -m scripts.demo_data` y comprobé la carga de **696 nodos y 858 aristas dirigidas**.
- Ejecuté `python -m scripts.validate` y confirmé el resultado **`status: ok`**, con **10 pares de prueba y 4 documentos**.
- Ejecuté los comandos de preparación de datos, extracción del corpus y análisis descriptivo, comprobando que finalizaran correctamente y produjeran **23 registros documentales y 9.287 palabras extraídas**.
- Volví a ejecutar la suite después del ajuste de precisión y confirmé que las **13 pruebas finalizaran con `OK`**.

**Fuentes y límites:** los datos geográficos proceden de OpenStreetMap y los documentos del sitio oficial del Metro de Medellín; no fueron inventados por la herramienta. Las verificaciones realizadas comprueban la carga, integridad y reproducción de los datos, pero no garantizan la exactitud de todas las vías ni la vigencia de todas las disposiciones documentales. El código y los textos generados con asistencia de IA requieren revisión y comprensión; las pruebas de este componente no evalúan los algoritmos de rutas, el agente ni la interfaz.


## 2. Wendy: algoritmos de enrutamiento

(Transcrito de `docs/ia_wendy.md`, escrito por Wendy.)


### 2.1 Herramienta y Propósito

Para el desarrollo de los **Algoritmos de Enrutamiento Vial**, utilicé un modelo de lenguaje (Gemini) como asistente de sintaxis y productividad, manteniendo el control, la revisión y la validación de la lógica implementada.

La herramienta se utilizó con los siguientes propósitos específicos:
- **Aceleración de código base:** Apoyo con la sintaxis nativa de Python para el manejo de colas de prioridad (`heapq`) en A* y Dijkstra, garantizando el cumplimiento de la restricción de no usar librerías de enrutamiento como NetworkX u OSMnx.
- **Estructuración de pruebas:** Generación del esqueleto de las pruebas unitarias (`tests/test_routing.py`), definiendo los casos de rutas vacías y nodos inexistentes.
- **Formato de datos:** Asistencia para estructurar el script de exportación de métricas a formato CSV (`evaluate_routes.py`).
- **Redacción técnica:** Revisión de estilo y gramática para la explicación de admisibilidad de la heurística en el informe (`docs/02_modelo.md`).

---

### 2.2 Decisiones Técnicas y Lógica Implementada

1. **Definición Rigurosa de "Nodo Expandido":**  
   Se definió y documentó que un nodo cuenta como expandido únicamente al ser extraído de la cola de prioridad (`heapq.heappop`) y procesarse sus aristas salientes. Se evitó el sesgo común de contabilizar inserciones o entradas obsoletas en la cola.
2. **Desempate en Cola de Prioridad:**  
   Se implementó un contador entero incremental (`entry_counter`) en las tuplas encoladas `(f_score, counter, node_id)`. Esto evita fallos de comparación de tipos entre identificadores o nodos en casos de empates numéricos de costos y mantiene estabilidad determinista.
3. **Admisibilidad de la Heurística:**  
   Se integró la función de dominio geodésico `src.domain.geo.haversine_m` como la función $h(n)$. Al ser la distancia euclidiana sobre la superficie esférica una cota inferior no sobreestimable frente a cualquier trayecto vial curvo y canalizado, se asegura la admisibilidad teórica y la optimalidad del resultado.
4. **Cumplimiento Estricto del Contrato de Datos:**  
   Se implementó `plan_route` garantizando las llaves exactas solicitadas (`status`, `path`, `distance_m`, `expanded_nodes`, `elapsed_ms`, `error`), controlando explícitamente rutas inexistentes, nodos inválidos, origen igual a destino (costo 0.0) y algoritmos no reconocidos.

---

### 2.3 Verificaciones y Validación Realizada Personalmente

Como estudiante responsable del bloque, verifiqué personalmente todo el código y artefactos generados mediante las siguientes acciones:

- **Ejecución de Pruebas Unitarias:**  
  Ejecuté la suite completa `python -m unittest tests/test_routing.py -v`, verificando con éxito los 7 casos de prueba (equivalencia exacta de costos A* vs. Dijkstra en los 10 pares, casos extremos de origen igual a destino, nodos fantasma, algoritmos inválidos y grafos desconectados).
- **Inspección de Resultados Experimentales:**  
  Ejecuté `python scripts/evaluate_routes.py` y verifiqué fila por fila el archivo `results/routes.csv`, corroborando que en todos los pares evaluados `same_optimal_distance == True`, con un ahorro de expansiones de hasta un 62.08% a favor de A*.
- **Revisión de Código Línea por Línea:**  
  Inspeccioné el código en `src/routing.py` comprobando que no existieran dependencias no permitidas, que la reconstrucción del camino mediante el diccionario de predecesores fuera correcta y que las mediciones de tiempo (`perf_counter`) no tuvieran sobrecostos artificiales.

---

## 3. Oriana: agente y RAG

> **PENDIENTE.** Oriana debe aportar `docs/ia_oriana.md` (herramienta(s) de IA usada(s) para el agente, el RAG y la
> evaluación, propósito, qué verificó personalmente). Al momento de cerrar este documento no existe en ninguna rama.
>
> Nota factual para su sección: el agente usa un modelo de lenguaje en tiempo de ejecución como parte del producto
> (ver `docs/03_agente.md` y `docs/verificacion_final.md`); eso es distinto de las herramientas de IA usadas para escribir el código.

## 4. Ana: aplicación, integración y entrega

**Herramienta:** Claude Code (modelo Claude Sonnet 5.5, de Anthropic), como asistente de programación en mi equipo.

**Para qué lo usé:**
- Revisar el repositorio recibido y comprobar los contratos entre bloques (`scripts/check_contracts.py`).
- Escribir el borrador de la aplicación Streamlit (`app.py`), el README final, `requirements.txt` consolidado y
  `docs/verificacion_final.md`.
- Diagnosticar fallas de integración: el error HTTP 403 del proveedor por el `User-Agent`, las citas con caracteres
  invisibles o de ancho completo que dejaban vacía la lista de fuentes, y la falla de dos pruebas por la conversión
  de saltos de línea (CRLF) en Windows.
- Ejecutar la evaluación del agente de Oriana con mi clave y mi proveedor (`results/agent_eval.csv`).
- Ayudar a unir los textos del informe.

**Cambios en código de otras integrantes, con mi aprobación:** una línea de `src/agent/agent.py` (expresión regular de
citas, ahora tolerante a espacios de ancho cero y corchetes de ancho completo) y un `.gitattributes` para que Git no
convierta a CRLF los datos crudos, cuyo hash está registrado. Ambos quedan documentados en `docs/verificacion_final.md`.

**Qué verifiqué yo personalmente:** abrí la aplicación en el navegador, comprobé el mapa, los gráficos, la tabla y el
chat con preguntas de ruta, del Metro y de información ausente, y revisé que los números coincidieran con
`results/routes.csv`. Proporcioné la clave del proveedor (guardada solo en `.env`, fuera de Git) y decidí los cambios
anteriores.

**Límites:** el asistente no sustituye la comprensión del trabajo; las respuestas del LLM en tiempo de ejecución
pueden contener errores y deben contrastarse con las fuentes citadas.
