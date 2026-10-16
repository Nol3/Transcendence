"""Observabilidad mínima (roadmap 4.4).

Dos piezas:

- **Logs en JSON a stdout**: cada línea es un objeto con `time`, `level`, `logger`,
  `message` y, si la hay, `request_id`. En un contenedor eso es lo que permite buscar
  por petición o por nivel sin parsear texto libre.
- **Request id**: se toma de la cabecera `X-Request-ID` (útil detrás de un proxy) o se
  genera, se guarda en un `ContextVar` para que los logs de la petición lo lleven, y
  se devuelve en la respuesta.
"""
from __future__ import annotations

import json
import logging
import uuid
from contextvars import ContextVar

# Lo pone `RequestIdMiddleware` al empezar cada petición.
request_id_var: ContextVar[str] = ContextVar("request_id", default="-")

HEADER = "X-Request-ID"


class RequestIdMiddleware:
    """Asigna un id a cada petición y lo devuelve en la respuesta."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        rid = (request.headers.get(HEADER) or "").strip() or uuid.uuid4().hex[:16]
        token = request_id_var.set(rid)
        request.request_id = rid
        try:
            response = self.get_response(request)
        finally:
            request_id_var.reset(token)
        response[HEADER] = rid
        return response


class JsonFormatter(logging.Formatter):
    """Una línea de JSON por registro."""

    def format(self, record: logging.LogRecord) -> str:
        datos = {
            "time": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": request_id_var.get(),
        }
        if record.exc_info:
            datos["exc"] = self.formatException(record.exc_info)
        # Todo lo que se pase en `extra=` acaba en el JSON (p. ej. user_id).
        for clave, valor in getattr(record, "extra_fields", {}).items():
            datos[clave] = valor
        return json.dumps(datos, ensure_ascii=False)


def logging_config(debug: bool = False) -> dict:
    """Configuración de `LOGGING`: consola en JSON, con nivel INFO."""
    return {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {"json": {"()": "config.observability.JsonFormatter"}},
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "json",
                "stream": "ext://sys.stdout",
            },
        },
        "root": {"handlers": ["console"], "level": "INFO"},
        "loggers": {
            # Django y Channels al mismo sitio, con el nivel del proyecto.
            "django": {"handlers": ["console"], "level": "INFO", "propagate": False},
            "django.server": {"handlers": ["console"], "level": "INFO", "propagate": False},
            "django.request": {"handlers": ["console"], "level": "INFO", "propagate": False},
            "channels": {"handlers": ["console"], "level": "INFO", "propagate": False},
            "apps": {"handlers": ["console"], "level": "DEBUG" if debug else "INFO",
                     "propagate": False},
        },
    }
