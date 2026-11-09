"""Esquema OpenAPI de la autenticación por clave de API.

drf-spectacular no adivina un `BaseAuthentication` propio: en cada ruta que lo acepta avisa
«could not resolve authenticator ApiKeyAuthentication» y el esquema sale sin el candado. Con esta
extensión, `/api/docs/` muestra `X-API-Key` donde de verdad se puede usar.
"""
from drf_spectacular.extensions import OpenApiAuthenticationExtension


class ApiKeyAuthenticationScheme(OpenApiAuthenticationExtension):
    """Describe `X-API-Key` como esquema `apiKey` en la cabecera."""

    target_class = "apps.public_api.authentication.ApiKeyAuthentication"
    name = "ApiKeyAuth"

    def get_security_definition(self, auto_schema):
        return {
            "type": "apiKey",
            "in": "header",
            "name": "X-API-Key",
            "description": "Clave personal, creada en POST /api/public/keys/.",
        }
