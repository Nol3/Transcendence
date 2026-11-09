"""Public API app config."""
from django.apps import AppConfig


class PublicApiConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.public_api"
    verbose_name = "Public API"

    def ready(self):
        # Registra el esquema OpenAPI de `X-API-Key`; sin esto drf-spectacular avisa en cada
        # ruta que usa esa autenticación y el candado no sale en /api/docs/.
        from . import schema  # noqa: F401
