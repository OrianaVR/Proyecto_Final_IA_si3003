# Informe Técnico: Algoritmos de Enrutamiento Vial (Bloque 2 - Wendy)

## 1. Contexto y Formulación del Problema

El presente informe documenta el desarrollo y evaluación experimental del componente de búsqueda de rutas óptimas en la red vial del centro de Medellín. El grafo en memoria —generado a partir de OpenStreetMap en el Bloque 1— es un grafo dirigido $G = (V, E)$ compuesto por $|V| = 696$ nodos con coordenadas geográficas WGS84 y $|E| = 858$ aristas dirigidas ponderadas por su longitud geodésica real en metros ($c(u, v) = \text{distance\_m} \ge 0$).

El objetivo consiste en encontrar el camino de menor distancia entre pares de nodos de origen y destino mediante algoritmos clásicos de búsqueda en grafos, comparando una técnica informada frente a una línea base no informada, sin recurrir a paquetes de alto nivel como NetworkX u OSMnx.

---

## 2. Línea Base y Técnica Seleccionada

- **Línea Base: Algoritmo de Dijkstra.**  
  Implementado como búsqueda de costo uniforme (*Uniform Cost Search*). Mantiene una cola de prioridad basada en `heapq` que ordena los nodos frontera según su costo acumulado desde el origen $g(n)$. Garantiza la obtención del camino de costo mínimo al extraer el nodo destino, explorando el grafo de forma radial e isótropa sin noción direccional hacia el objetivo.

- **Técnica Elegida: Algoritmo A\*.**  
  Búsqueda heurística informada que prioriza la exploración según la función de evaluación $f(n) = g(n) + h(n)$, donde $g(n)$ es el costo acumulado exacto y $h(n)$ es una estimación del costo restante hasta el nodo de destino.

- **Criterio de "Nodo Expandido":**  
  Se contabiliza rigurosamente como **nodo expandido** todo nodo que es extraído de la cola de prioridad (`heapq.heappop`) y cuyas aristas salientes son examinadas para actualizar las distancias tentativas de sus vecinos. No se contabilizan las inserciones en la cola ni las extracciones redundantes descartadas por haberse cerrado previamente con un camino más corto.

---

## 3. Justificación de la Heurística Geográfica (Admisibilidad y Consistencia)

Se utiliza la distancia ortodrómica calculada con la fórmula de Haversine (`src.domain.geo.haversine_m`) entre las coordenadas geográficas del nodo actual $n$ y el nodo destino $t$:

$$h(n) = \text{haversine}(n, t)$$

1. **Admisibilidad ($h(n) \le h^*(n)$):**  
   La distancia de Haversine representa la longitud del arco de círculo máximo (la trayectoria geodésica más corta sobre la esfera terrestre) entre dos pares de coordenadas. Puesto que los vehículos terrestres transitan confinados a la topología de la malla vial (calles, avenidas, rotondas y restricciones de sentido único), cualquier ruta física factible en el grafo satisface $\text{costo\_real}(n, t) \ge \text{haversine}(n, t)$. Al no sobreestimar jamás el costo real, la heurística es estrictamente **admisible**, lo que garantiza que A\* siempre encuentra el camino óptimo.

2. **Consistencia / Monotonía ($h(u) \le c(u, v) + h(v)$):**  
   Por la desigualdad triangular en la métrica geodésica esférica:
   $$\text{haversine}(u, t) \le \text{haversine}(u, v) + \text{haversine}(v, t)$$
   Dado que las aristas del grafo se construyeron asignando a cada segmento la distancia de Haversine entre sus nodos extremos ($c(u, v) = \text{haversine}(u, v)$), se cumple con igualdad que $h(u) \le c(u, v) + h(v)$ para toda arista $(u, v)$. En consecuencia, la heurística es monótona, garantizando que el primer cierre de cualquier nodo ya posee el costo óptimo $g(n)$ sin requerir reaperturas.

---

## 4. Análisis de Resultados Experimentales

La evaluación se ejecutó sobre los 10 pares dirigidos de prueba fijos en `data/test_pairs.json`. Los resultados consolidados en `results/routes.csv` demuestran lo siguiente:

| ID Par | Distancia Óptima (m) | Expandidos Dijkstra | Expandidos A\* | Reducción de Expansión (%) | Salto de Nodos (Hops) |
|---|:---:|:---:|:---:|:---:|:---:|
| `pair_01` | 1 069.82 | 277 | 115 | **58.48%** | 76 |
| `pair_02` | 1 076.10 | 452 | 176 | **61.06%** | 46 |
| `pair_03` | 1 105.49 | 371 | 262 | **29.38%** | 57 |
| `pair_04` | 1 556.45 | 587 | 307 | **47.70%** | 71 |
| `pair_05` | 1 014.10 | 320 | 225 | **29.69%** | 71 |
| `pair_06` | 1 500.79 | 537 | 381 | **29.05%** | 76 |
| `pair_07` | 411.94 | 84 | 35 | **58.33%** | 27 |
| `pair_08` | 1 336.34 | 564 | 366 | **35.11%** | 80 |
| `pair_09` | 626.04 | 109 | 78 | **28.44%** | 37 |
| `pair_10` | 1 308.84 | 451 | 171 | **62.08%** | 57 |

### Hallazgos Clave:
- **Equivalencia de Optimización:** En el 100% de los casos analizados, A\* y Dijkstra obtuvieron **exactamente la misma distancia métrica óptima** y secuencias de ruta idénticas (`same_optimal_distance = True`, `same_path = True`).
- **Eficiencia en el Espacio de Búsqueda:** A\* redujo de forma contundente la cantidad de nodos expandidos, alcanzando ahorros de entre **28.44% y 62.08%** (reducción promedio superior al **43.9%**). En pares con alineación geográfica directa hacia el destino (como `pair_02` y `pair_10`), A\* expandió menos de la mitad de los nodos explorados por Dijkstra.
- **Rendimiento Temporal:** En un grafo de 696 nodos, los tiempos de ejecución de ambos algoritmos se ubicaron por debajo de 1 milisegundo por consulta en CPU estándar. A\* demostró una clara ventaja en poda del árbol de búsqueda, resultando en una solución altamente escalable para grafos viales urbanos de mayor envergadura.

