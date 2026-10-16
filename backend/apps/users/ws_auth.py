"""Autenticación de WebSockets por JWT en el query string.

El navegador no puede mandar cabeceras `Authorization` al abrir un WebSocket, así que el
token viaja en la URL (`?token=...`). Es el mismo sistema que usa la mesa de póker; se
deja aquí, en un sitio compartido, para que cada juego no invente el suyo.
"""
from __future__ import annotations

from urllib.parse import parse_qs


def authenticate_ws(scope) -> tuple[int, str] | None:
    """Valida el JWT del query string y devuelve (id, nombre) o `None`."""
    token = (parse_qs(scope.get("query_string", b"").decode()).get("token") or [None])[0]
    if not token:
        return None
    try:
        from rest_framework_simplejwt.authentication import JWTAuthentication

        auth = JWTAuthentication()
        user = auth.get_user(auth.get_validated_token(token))
        return (user.id, user.username)
    except Exception as exc:  # noqa: BLE001
        # Token caducado, manipulado o de otro sitio: simplemente no está autenticado.
        # Se deja el motivo en el log, que si no estos fallos son invisibles.
        import logging

        logging.getLogger(__name__).info("WS sin autenticar: %s", exc)
        return None
