from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from .json_store import write_json


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def file_hash(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def record_download(path: Path, url: str) -> dict:
    record = {"url": url, "retrieved_at_utc": utc_now(),
              "sha256": file_hash(path), "size_bytes": path.stat().st_size}
    write_json(path.with_suffix(path.suffix + ".source.json"), record)
    return record
