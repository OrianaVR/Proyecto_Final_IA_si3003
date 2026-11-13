"""Cliente mínimo para proveedores LLM con API compatible con OpenAI (/chat/completions).

Solo usa la biblioteca estándar. La configuración sale de variables de entorno o de un archivo
``.env`` local (ignorado por Git):

    LLM_API_KEY   clave del proveedor (obligatoria)
    LLM_BASE_URL  URL base, p. ej. https://api.openai.com/v1 (si está vacía se usa la de OpenAI)
    LLM_MODEL     nombre del modelo (obligatorio)

La clave nunca se imprime ni se incluye en los mensajes de error.
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.config import PROJECT_ROOT

DEFAULT_BASE_URL = "https://api.openai.com/v1"
RETRY_STATUS = {429, 500, 502, 503, 504}


class LLMError(RuntimeError):
    """Falla al llamar al proveedor (red, autenticación, respuesta inesperada)."""


class LLMConfigError(LLMError):
    """Falta configuración (clave o modelo)."""


@dataclass(frozen=True)
class LLMConfig:
    api_key: str
    base_url: str
    model: str
    timeout_s: float = 60.0


def load_env_file(path: Path | None = None) -> None:
    """Carga pares CLAVE=valor de un .env sin pisar variables ya definidas en el entorno."""
    path = path or (PROJECT_ROOT / ".env")
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip("'\""))


def load_config() -> LLMConfig:
    load_env_file()
    api_key = os.environ.get("LLM_API_KEY", "").strip()
    model = os.environ.get("LLM_MODEL", "").strip()
    base_url = os.environ.get("LLM_BASE_URL", "").strip() or DEFAULT_BASE_URL
    if not api_key or not model:
        raise LLMConfigError(
            "Falta configurar el proveedor LLM: define LLM_API_KEY y LLM_MODEL "
            "(y LLM_BASE_URL si no usas OpenAI) en el archivo .env. Ver .env.example.")
    return LLMConfig(api_key=api_key, base_url=base_url.rstrip("/"), model=model)


class OpenAICompatibleClient:
    """Envía mensajes (con herramientas) y devuelve el mensaje del asistente."""

    def __init__(self, config: LLMConfig | None = None, retries: int = 2, temperature: float | None = 0.0):
        self.config = config or load_config()
        self.retries = retries
        self.temperature = temperature

    def chat(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]] | None = None) -> dict[str, Any]:
        payload: dict[str, Any] = {"model": self.config.model, "messages": messages}
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"
        if self.temperature is not None:
            payload["temperature"] = self.temperature
        request = urllib.request.Request(
            f"{self.config.base_url}/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json",
                     "Authorization": f"Bearer {self.config.api_key}"},
            method="POST")

        last_error = "sin respuesta"
        for attempt in range(self.retries + 1):
            try:
                with urllib.request.urlopen(request, timeout=self.config.timeout_s) as response:
                    body = json.loads(response.read().decode("utf-8"))
                return self._extract_message(body)
            except urllib.error.HTTPError as exc:
                detail = exc.read().decode("utf-8", errors="replace")[:300]
                last_error = f"HTTP {exc.code}: {detail}"
                if exc.code not in RETRY_STATUS or attempt == self.retries:
                    raise LLMError(f"El proveedor respondió un error. {last_error}") from None
            except (urllib.error.URLError, TimeoutError, OSError) as exc:
                last_error = f"{type(exc).__name__}: {getattr(exc, 'reason', exc)}"
                if attempt == self.retries:
                    raise LLMError(f"No se pudo contactar al proveedor. {last_error}") from None
            time.sleep(1.5 * (attempt + 1))
        raise LLMError(f"No se obtuvo respuesta del proveedor. {last_error}")

    @staticmethod
    def _extract_message(body: dict[str, Any]) -> dict[str, Any]:
        try:
            message = body["choices"][0]["message"]
        except (KeyError, IndexError, TypeError):
            raise LLMError("Respuesta del proveedor con formato inesperado.") from None
        return {"role": "assistant", "content": message.get("content"),
                "tool_calls": message.get("tool_calls") or []}
