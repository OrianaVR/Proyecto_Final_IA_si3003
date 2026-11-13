# Declaración de uso de IA del bloque de Isabella

**Proyecto:** Copiloto de movilidad de Medellín  
**Responsable:** Isabella Cadavid Posada  
**Bloque:** Datos viales y corpus documental  
**Herramienta utilizada:** ChatGPT con Codex

## 1. Uso de la herramienta

Utilicé ChatGPT con Codex como apoyo para preparar los datos viales y el corpus documental. La herramienta propuso una estructura para organizar el código, generó código Python y ayudó a preparar los scripts de descarga y transformación, las pruebas automatizadas y los borradores de la documentación.

También la consulté para recibir explicaciones sobre la representación de la red mediante nodos y aristas, la organización del proyecto, la configuración del entorno de Python en mi Mac y la ejecución de las validaciones.

Durante las pruebas, utilicé su apoyo para diagnosticar una diferencia de precisión numérica que hacía fallar la comparación de los datos reconstruidos. La prueba se ajustó para comparar las distancias con una tolerancia, conservando las comprobaciones de estructura e integridad.

## 2. Procedencia de los datos

Los datos de la red vial se descargaron de OpenStreetMap y los documentos del corpus se obtuvieron del sitio oficial del Metro de Medellín. Se conservaron los archivos originales, sin generar coordenadas ni documentos sintéticos para reemplazarlos.

OpenStreetMap es una fuente abierta colaborativa. Los documentos del Metro son fuentes institucionales oficiales y se utilizan como contenido documental para el asistente.

Los registros de procedencia y manifiestos incluyen las fuentes y los hashes de los archivos. La fuente permite rastrear de dónde se obtuvo cada archivo y el hash permite comprobar si una copia coincide con la versión registrada.

## 3. Verificaciones automatizadas

Durante la preparación del bloque se ejecutaron 13 pruebas unitarias y de integración. Las verificaciones incluyeron:

- Comprobar que el grafo se pudiera cargar desde archivos locales sin realizar solicitudes HTTP.
- Validar las coordenadas, las distancias y los identificadores.
- Comprobar la interpretación de los sentidos de circulación y las restricciones básicas de acceso.
- Validar los 10 pares de origen y destino mediante alcanzabilidad dirigida.
- Comparar los datos reconstruidos con los incluidos en el proyecto, utilizando una tolerancia numérica para las distancias y comprobando la igualdad de los identificadores, la topología, los metadatos y los pares de prueba.
- Detectar duplicados y alteraciones de los archivos originales.

Además, el comando de validación comprobó la integridad de los archivos del corpus y la correspondencia entre los textos extraídos y los registros documentales.

Estas comprobaciones automatizadas no sustituyen la revisión ni la comprensión del código.

## 4. Trabajo y comprobaciones personales

Al intentar ejecutar los comandos en mi Mac, la terminal mostró `zsh: command not found: python`. Comprobé que el equipo reconocía `python3`, que reportaba la versión `3.15.0rc2`, y ejecuté:

```bash
python3 --version
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

Creé y activé el entorno virtual e instalé las dependencias. Después ejecuté personalmente:

```bash
python -m scripts.demo_data
python -m scripts.validate
python -m unittest discover -s tests -v
```

Comprobé la carga de **696 nodos y 858 aristas dirigidas**, la validación de **10 pares de prueba y cuatro documentos**, y la aprobación de las **13 pruebas** después del ajuste de precisión numérica.

También ejecuté los comandos de preparación y análisis:

```bash
python -m scripts.prepare_data
python -m scripts.prepare_corpus
python -m scripts.describe_data
```

Confirmé que finalizaran correctamente y que la extracción del corpus produjera **23 registros y 9.287 palabras**. Después repetí las pruebas y la validación, nuevamente con resultados correctos.

## 5. Alcance y limitaciones

La validación de los 10 pares dirigidos cubre los casos incluidos en el proyecto; no demuestra que todos los recorridos posibles estén evaluados. El grafo representa un extracto pequeño del centro de Medellín y utiliza distancias geométricas, sin incorporar tráfico en tiempo real, tarifas o tiempos de viaje.

En el corpus, los hashes permiten verificar la integridad de los archivos, pero no garantizan la fidelidad completa del texto extraído ni la vigencia de las disposiciones documentales. Estas comprobaciones requieren contrastar el contenido con los originales y considerar sus fechas y versiones.

Mi revisión personal incluyó la configuración del entorno, la ejecución de los comandos de preparación y la comprobación de los resultados de las validaciones y pruebas. No incluyó un cotejo página por página del corpus.

Mi participación en este bloque corresponde a la preparación de los datos y del corpus que sirven de entrada a los demás componentes. Los algoritmos de rutas, su comparación experimental, el agente LLM con RAG y la interfaz corresponden a otros bloques del proyecto. El uso de IA fue una asistencia para el desarrollo y la explicación; no sustituye mi responsabilidad de comprender y revisar el trabajo entregado.
