"""
Lightweight HashiCorp Vault secret loader.

The project runs Vault in dev mode (see ``compose.yaml`` and ``VAULT_DOC.md``):
a single fixed root token, secrets stored under the KV v2 mount ``secret/`` at
the path ``transcendence`` by ``scripts/vault-init.sh``.

This module fetches those secrets at startup so Django does not have to hardcode
them. It is intentionally defensive: if Vault is disabled, unreachable, or the
secret is missing, it returns an empty dict and the caller falls back to plain
environment variables (``python-decouple``). That keeps ``manage.py runserver``
working locally without Docker or Vault.
"""

from __future__ import annotations

import logging
import os

import requests

logger = logging.getLogger(__name__)

# KV v2 read path for `secret/transcendence` (the `data` segment is mandatory
# for version-2 mounts, which is what Vault dev mode enables by default).
_SECRET_API_PATH = "/v1/secret/data/transcendence"

# Short timeout: a missing/slow Vault must never stall app startup.
_TIMEOUT_SECONDS = 3

_cache: dict[str, str] | None = None


def _truthy(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "on"}


def load_vault_secrets() -> dict[str, str]:
    """Return the secrets stored at ``secret/transcendence``.

    Returns an empty dict (never raises) when Vault is disabled or unavailable,
    so settings can transparently fall back to environment variables.
    """
    global _cache
    if _cache is not None:
        return _cache

    if not _truthy(os.environ.get("USE_VAULT", "false")):
        _cache = {}
        return _cache

    addr = os.environ.get("VAULT_ADDR", "http://vault:8200").rstrip("/")
    token = os.environ.get("VAULT_TOKEN", "")
    if not token:
        logger.warning("USE_VAULT is on but VAULT_TOKEN is empty; using env vars.")
        _cache = {}
        return _cache

    try:
        response = requests.get(
            f"{addr}{_SECRET_API_PATH}",
            headers={"X-Vault-Token": token},
            timeout=_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        # KV v2 response shape: {"data": {"data": {...secrets...}, "metadata": {...}}}
        secrets = response.json()["data"]["data"]
    except (requests.RequestException, KeyError, ValueError) as exc:
        logger.warning("Could not load secrets from Vault (%s); using env vars.", exc)
        _cache = {}
        return _cache

    logger.info("Vault secrets loaded successfully (%d keys).", len(secrets))
    _cache = {str(k): str(v) for k, v in secrets.items()}
    return _cache
