from pathlib import Path
from typing import Protocol
from src.domain.models import Graph


class GraphReader(Protocol):
    def load(self, directory: Path) -> Graph: ...
