from pathlib import Path
from src.application.datasets import read_graph
from src.config import PROCESSED_DIR
from src.domain.models import Graph
from src.infrastructure.json_store import JsonGraphRepository


def load_graph(directory: str | Path | None = None) -> Graph:
    """Carga únicamente archivos locales; no realiza descargas ni pide claves."""
    return read_graph(JsonGraphRepository(), Path(directory) if directory is not None else PROCESSED_DIR)
