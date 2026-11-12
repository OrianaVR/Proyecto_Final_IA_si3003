from dataclasses import dataclass, field
from math import isfinite
from typing import Mapping


class DataValidationError(ValueError):
    """Los datos incumplen un contrato del proyecto."""


@dataclass(frozen=True)
class Node:
    id: str
    latitude: float
    longitude: float

    def __post_init__(self):
        if not isinstance(self.id, str) or not self.id.strip():
            raise DataValidationError("El id del nodo debe ser texto no vacío.")
        if not isfinite(self.latitude) or not -90 <= self.latitude <= 90:
            raise DataValidationError(f"Latitud inválida: {self.id}")
        if not isfinite(self.longitude) or not -180 <= self.longitude <= 180:
            raise DataValidationError(f"Longitud inválida: {self.id}")


@dataclass(frozen=True)
class Edge:
    id: str
    origin: str
    destination: str
    distance_m: float
    osm_way_id: str
    name: str = ""
    highway: str = ""

    def __post_init__(self):
        if not all(isinstance(x, str) and x for x in
                   (self.id, self.origin, self.destination, self.osm_way_id)):
            raise DataValidationError("Arista sin identificadores válidos.")
        if not isfinite(self.distance_m) or self.distance_m < 0:
            raise DataValidationError(f"Distancia inválida: {self.id}")
        if self.origin == self.destination:
            raise DataValidationError(f"Autociclo descartable: {self.id}")


@dataclass
class Graph:
    nodes: Mapping[str, Node]
    edges: tuple[Edge, ...]
    metadata: dict = field(default_factory=dict)
    adjacency: dict[str, tuple[Edge, ...]] = field(init=False)

    def __post_init__(self):
        if not self.nodes or not self.edges:
            raise DataValidationError("El grafo debe tener nodos y aristas.")
        if any(key != node.id for key, node in self.nodes.items()):
            raise DataValidationError("La clave del nodo no coincide con su id.")
        neighbors = {node_id: [] for node_id in self.nodes}
        edge_ids = set()
        for edge in self.edges:
            if edge.id in edge_ids:
                raise DataValidationError(f"Id de arista duplicado: {edge.id}")
            edge_ids.add(edge.id)
            if edge.origin not in self.nodes or edge.destination not in self.nodes:
                raise DataValidationError(f"Arista con extremo inexistente: {edge.id}")
            neighbors[edge.origin].append(edge)
        self.adjacency = {key: tuple(sorted(value, key=lambda e: e.id))
                          for key, value in neighbors.items()}
