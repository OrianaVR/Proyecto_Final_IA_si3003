from pathlib import Path
import xml.etree.ElementTree as ET
from src.domain.geo import haversine_m
from src.domain.models import DataValidationError, Edge, Graph, Node

ALLOWED_HIGHWAYS = frozenset({"primary", "primary_link", "secondary", "secondary_link",
    "tertiary", "tertiary_link", "residential", "unclassified", "living_street", "service"})
DENIED_ACCESS = frozenset({"no", "private", "agricultural", "forestry", "delivery",
                          "customers", "destination", "permit"})


def validate_bbox(bbox):
    west, south, east, north = bbox
    if not (-180 <= west < east <= 180 and -90 <= south < north <= 90):
        raise DataValidationError("BBox inválida: west,south,east,north.")
    if (east-west)*(north-south) > 0.01:
        raise DataValidationError("Para este MVP use una región pequeña (área angular <= 0.01).")


def is_allowed(tags: dict[str, str]) -> bool:
    if tags.get("highway") not in ALLOWED_HIGHWAYS or tags.get("area") == "yes":
        return False
    # La restricción específica de automóvil prevalece sobre la genérica.
    access = next((tags[key] for key in ("motorcar", "motor_vehicle", "vehicle", "access")
                   if key in tags), "yes")
    return access not in DENIED_ACCESS and tags.get("oneway") not in {"reversible", "alternating"}


def directions(tags: dict[str, str]) -> tuple[bool, bool]:
    """(forward, reverse); respeta -1 y excepciones explícitas en rotondas."""
    oneway = tags.get("oneway", "").lower()
    if oneway in {"no", "false", "0"}:
        return True, True
    if oneway == "-1":
        return False, True
    if oneway in {"yes", "true", "1"} or tags.get("junction") in {"roundabout", "circular"}:
        return True, False
    if oneway:
        # Evitar interpretar valores desconocidos como una calle bidireccional.
        return False, False
    return True, True


def build_graph(xml_path: Path, bbox: tuple, source: dict) -> Graph:
    validate_bbox(bbox)
    try:
        root = ET.parse(xml_path).getroot()
    except (ET.ParseError, OSError) as error:
        raise DataValidationError(f"OSM XML inválido: {error}") from error
    if root.tag != "osm":
        raise DataValidationError("El archivo no tiene raíz <osm>.")
    west, south, east, north = bbox
    all_nodes = {}
    for element in root.findall("node"):
        node = Node(element.attrib["id"], float(element.attrib["lat"]), float(element.attrib["lon"]))
        if south <= node.latitude <= north and west <= node.longitude <= east:
            all_nodes[node.id] = node
    edges = []
    used = set()
    eligible_ways = 0
    for way in root.findall("way"):
        tags = {tag.attrib["k"]: tag.attrib["v"] for tag in way.findall("tag")}
        if not is_allowed(tags):
            continue
        forward, reverse = directions(tags)
        if not forward and not reverse:
            continue
        eligible_ways += 1
        refs = [node.attrib["ref"] for node in way.findall("nd")]
        for index, (first, second) in enumerate(zip(refs, refs[1:])):
            if first not in all_nodes or second not in all_nodes or first == second:
                continue
            distance = haversine_m(all_nodes[first], all_nodes[second])
            for origin, destination, enabled, suffix in ((first, second, forward, "f"),
                                                         (second, first, reverse, "r")):
                if enabled:
                    edges.append(Edge(f"{way.attrib['id']}:{index}:{suffix}", origin, destination,
                                      distance, way.attrib["id"], tags.get("name", ""), tags["highway"]))
                    used.update((origin, destination))
    metadata = {"schema_version": 1, "source": source, "bbox_wsen": list(bbox),
                "mode": "motor_vehicle_simplified", "distance_method": "haversine_segments",
                "earth_radius_m": 6371008.8, "raw_nodes": len(root.findall("node")),
                "raw_ways": len(root.findall("way")), "eligible_ways": eligible_ways,
                "node_count": len(used), "edge_count": len(edges),
                "limitations": ["No incluye restricciones de giro, tráfico, horarios ni tarifas.",
                    "Grafo recortado a bbox: no garantiza óptimo fuera del extracto.",
                    "Acceso condicional, barreras y restricciones por vehículo no modelados.",
                    "Las rutas son experimentales; no son indicaciones de navegación."]}
    return Graph({key: all_nodes[key] for key in sorted(used)}, tuple(sorted(edges,key=lambda e:e.id)), metadata)
