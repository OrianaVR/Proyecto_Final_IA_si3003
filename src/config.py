from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BBOX = (-75.574, 6.247, -75.566, 6.255)  # west, south, east, north
RAW_GRAPH = PROJECT_ROOT / "data/raw/medellin_centro.osm"
PROCESSED_DIR = PROJECT_ROOT / "data/processed"
