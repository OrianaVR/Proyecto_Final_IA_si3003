from pathlib import Path
from urllib.request import Request, urlopen


class DownloadError(RuntimeError):
    pass


def download(url: str, destination: Path, timeout: int = 45, max_bytes: int = 25_000_000) -> None:
    if not url.startswith("https://"):
        raise DownloadError("Solo se aceptan URLs HTTPS.")
    request = Request(url, headers={"User-Agent": "EAFIT-MobilityAcademicMVP/0.1"})
    try:
        with urlopen(request, timeout=timeout) as response:
            data = response.read(max_bytes + 1)
        if len(data) > max_bytes:
            raise DownloadError("La respuesta excede el tamaño permitido.")
        if not data:
            raise DownloadError("La respuesta está vacía.")
        if destination.suffix == ".pdf" and not data.startswith(b"%PDF"):
            raise DownloadError("El servidor no devolvió un PDF.")
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = destination.with_suffix(destination.suffix + ".part")
        temporary.write_bytes(data)
        temporary.replace(destination)
    except (OSError, ValueError) as error:
        raise DownloadError(f"No se pudo descargar {url}: {error}") from error
