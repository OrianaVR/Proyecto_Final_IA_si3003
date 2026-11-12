# Declaración de uso de IA del bloque de Wendy (Bloque 2)

## 1. Herramienta y Propósito

Para el desarrollo del **Bloque 2: Algoritmos de Enrutamiento Vial**, utilicé como asistente de programación un modelo avanzado de lenguaje de inteligencia artificial (Antigravity con Gemini 3.8 Flash).

La herramienta se utilizó con propósitos de:
- Co-diseño de la arquitectura limpia de búsqueda sin librerías de terceros (prohibición estricta de NetworkX y OSMnx).
- Generación de la plantilla base y optimización del manejo de colas de prioridad con `heapq`.
- Generación del script de benchmarking y exportación tabular en CSV (`scripts/evaluate_routes.py`).
- Implementación de la suite de pruebas unitarias exhaustivas en `tests/test_routing.py`.
- Asistencia en la estructuración de la demostración matemática formal de admisibilidad y consistencia para el informe técnico (`docs/02_modelo.md`).

---

## 2. Decisiones Técnicas y Lógica Implementada

1. **Definición Rigurosa de "Nodo Expandido":**  
   Se definió y documentó que un nodo cuenta como expandido únicamente al ser extraído de la cola de prioridad (`heapq.heappop`) y procesarse sus aristas salientes. Se evitó el sesgo común de contabilizar inserciones o entradas obsoletas en la cola.
2. **Desempate en Cola de Prioridad:**  
   Se implementó un contador entero incremental (`entry_counter`) en las tuplas encoladas `(f_score, counter, node_id)`. Esto previene fallos de comparación de tipos entre identificadores o nodos en casos de empates numéricos de costos y mantiene estabilidad determinista.
3. **Admisibilidad de la Heurística:**  
   Se integró la función de dominio geodésico `src.domain.geo.haversine_m` como la función $h(n)$. Al ser la distancia euclidiana/ortodrómica sobre la superficie esférica una cota inferior no sobreestimable frente a cualquier trayecto vial curvo y canalizado, se asegura la admisibilidad teórica y la optimalidad del resultado.
4. **Cumplimiento Estricto del Contrato de Datos:**  
   Se implementó `plan_route` garantizando las llaves exactas solicitadas (`status`, `path`, `distance_m`, `expanded_nodes`, `elapsed_ms`, `error`), controlando explícitamente rutas inexistentes, nodos inválidos, origen igual a destino (costo 0.0) y algoritmos no reconocidos.

---

## 3. Verificaciones y Validación Realizada Personalmente

Como estudiante responsable del bloque, verifiqué personalmente todo el código y artefactos generados mediante las siguientes acciones:

- **Ejecución de Pruebas Unitarias:**  
  Ejecuté la suite completa `python -m unittest tests/test_routing.py -v`, verificando con éxito los 7 casos de prueba (equivalencia exacta de costos A* vs. Dijkstra en los 10 pares, casos extremos de origen igual a destino, nodos fantasma, algoritmos inválidos y grafos desconectados).
- **Inspección de Resultados Experimentales:**  
  Ejecuté `python scripts/evaluate_routes.py` y verifiqué fila por fila el archivo `results/routes.csv`, corroborando que en todos los pares evaluados `same_optimal_distance == True`, con un ahorro de expansiones de hasta un 62.08% a favor de A*.
- **Revisión de Código Línea por Línea:**  
  Inspeccioné el código en `src/routing.py` comprobando que no existieran dependencias no permitidas, que la reconstrucción del camino mediante el diccionario de predecesores fuera correcta y que las mediciones de tiempo (`perf_counter`) no tuvieran sobrecostos artificiales.

---

## 4. Estado de Integración y Próximos Pasos

El Bloque 2 se encuentra completamente funcional, verificado y desacoplado, listo para ser consumido por el Bloque 3 (agente LLM / RAG a cargo de Oriana) y el Bloque 4 (interfaz y visualización a cargo de Ana).

