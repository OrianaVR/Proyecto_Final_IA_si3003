# Declaración de uso de IA

## 1. Herramienta y Propósito

Para el desarrollo de los **Algoritmos de Enrutamiento Vial**, utilicé un modelo de lenguaje (Gemini) como asistente de sintaxis y productividad, manteniendo el control, la revisión y la validación de la lógica implementada.

La herramienta se utilizó con los siguientes propósitos específicos:
- **Aceleración de código base:** Apoyo con la sintaxis nativa de Python para el manejo de colas de prioridad (`heapq`) en A* y Dijkstra, garantizando el cumplimiento de la restricción de no usar librerías de enrutamiento como NetworkX u OSMnx.
- **Estructuración de pruebas:** Generación del esqueleto de las pruebas unitarias (`tests/test_routing.py`), definiendo los casos de rutas vacías y nodos inexistentes.
- **Formato de datos:** Asistencia para estructurar el script de exportación de métricas a formato CSV (`evaluate_routes.py`).
- **Redacción técnica:** Revisión de estilo y gramática para la explicación de admisibilidad de la heurística en el informe (`docs/02_modelo.md`).

---

## 2. Decisiones Técnicas y Lógica Implementada

1. **Definición Rigurosa de "Nodo Expandido":**  
   Se definió y documentó que un nodo cuenta como expandido únicamente al ser extraído de la cola de prioridad (`heapq.heappop`) y procesarse sus aristas salientes. Se evitó el sesgo común de contabilizar inserciones o entradas obsoletas en la cola.
2. **Desempate en Cola de Prioridad:**  
   Se implementó un contador entero incremental (`entry_counter`) en las tuplas encoladas `(f_score, counter, node_id)`. Esto evita fallos de comparación de tipos entre identificadores o nodos en casos de empates numéricos de costos y mantiene estabilidad determinista.
3. **Admisibilidad de la Heurística:**  
   Se integró la función de dominio geodésico `src.domain.geo.haversine_m` como la función $h(n)$. Al ser la distancia euclidiana sobre la superficie esférica una cota inferior no sobreestimable frente a cualquier trayecto vial curvo y canalizado, se asegura la admisibilidad teórica y la optimalidad del resultado.
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
