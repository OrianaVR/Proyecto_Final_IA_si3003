# Fuentes reales y descarga

## Red vial OpenStreetMap

Se usa el centro de Medellín, Colombia, aproximadamente 0.9 km por 0.9 km. Bounding box west,south,east,north: `-75.574,6.247,-75.566,6.255`.

URL exacta del extracto incluido:
https://api.openstreetmap.org/api/0.6/map?bbox=-75.574,6.247,-75.566,6.255

Licencia y atribución: https://www.openstreetmap.org/copyright . Documentación de sentidos: https://wiki.openstreetmap.org/wiki/Key:oneway . Documentación para enrutamiento: https://wiki.openstreetmap.org/wiki/OSM_tags_for_routing .

La API devuelve XML OSM real; no son coordenadas escritas a mano. Se conserva el original íntegro y su SHA-256. La fecha ISO UTC del manifiesto corresponde a la captura registrada; en Colombia esta descarga se realizó el 9 de noviembre de 2026.

Para actualizar, usar `python -m scripts.prepare_data --download`. Para descarga manual, abrir la URL en el navegador y guardar el XML como `data/raw/medellin_centro.osm`. Después registrar procedencia de esa copia y reconstruir:

```python
# Ejecutar desde la raíz del proyecto con python.
from src.config import RAW_GRAPH
from src.infrastructure.provenance import record_download

record_download(
    RAW_GRAPH,
    "https://api.openstreetmap.org/api/0.6/map?bbox=-75.574,6.247,-75.566,6.255",
)
```

```bash
python -m scripts.prepare_data
python -m scripts.describe_data
python -m scripts.validate
```

No reutilizar un archivo `.source.json` cuyo hash pertenece a otra descarga. Si el servicio falla, usar los originales incluidos en este ZIP. No es necesario obtener una API key.

## Documentos del Metro de Medellín

| Documento | Fuente oficial |
|---|---|
| Reglamento del Usuario | https://www.metrodemedellin.gov.co/hubfs/reglamento-del-usuario-11052019-1.pdf |
| Condiciones de uso funcionalidad Bici | https://www.metrodemedellin.gov.co/hubfs/condiciones-de-uso-funcionalidad-bici-2.pdf |
| Convivencia de bicicletas en el sistema | https://www.metrodemedellin.gov.co/hubfs/NORMAS-CONVIVENCIA-BICI-MAS-METRO-DEF-26-10-2015.pdf |
| Información y servicios para usuarios | https://www.metrodemedellin.gov.co/usuarios |

Las cuatro fuentes se descargaron y extrajeron. `corpus/sources.csv` contiene la trazabilidad y `corpus/manifest.json` añade hashes y conteos. `config/corpus_sources.json` permite reproducir la selección. El nombre del archivo puede señalar una fecha histórica: no equivale a una certificación de vigencia. No se usa una noticia aislada para inventar reglas generales.

Para refrescar automáticamente: `python -m scripts.prepare_corpus --download`. Para hacerlo manualmente, guardar el archivo con el nombre definido en config y llamar a `record_download(path, url)` para esa fuente antes de `python -m scripts.prepare_corpus`.

Los PDF y la web son materiales del Metro, no datos numéricos para asignar distancias a calles. No se descargaron tarifas, tráfico ni tiempos reales. Las rutas no son recorridos operativos del Metro.
