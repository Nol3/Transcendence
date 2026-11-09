"""Base para las vistas de API que declaran su respuesta en el esquema OpenAPI.

drf-spectacular solo sabe adivinar la respuesta de una `GenericAPIView` o de un `ViewSet`. En un
`APIView` a secas avisa —`drf_spectacular.W002: unable to guess serializer`— y **la ruta
desaparece** de `/api/docs/`: el esquema se queda mintiendo por omisión, que es peor que avisar.

Estas vistas devuelven el sobre del proyecto (`{"data": …, "error": …}`), así que se documenta
como objeto genérico. Una vista que quiera precisión solo tiene que poner su propio
`@extend_schema` en el método (`get`/`post`), que tiene prioridad sobre esto.
"""
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework.views import APIView

METODOS_HTTP = ("get", "post", "put", "patch", "delete")

# Los códigos que usan estas vistas: crear devuelve 201 y borrar 204. Declarar solo el 200 dejaba
# a las de 201 sin respuesta documentada (y seguían avisando).
RESPUESTAS = {200: OpenApiTypes.OBJECT, 201: OpenApiTypes.OBJECT, 204: None}


class VistaAPI(APIView):
    """`APIView` cuya respuesta se declara como objeto (el sobre `data`/`error`).

    La anotación se pone en `__init_subclass__` porque drf-spectacular mira los **métodos**
    (`get`, `post`…), no `dispatch`: decorar `dispatch` no le dice nada. Si una subclase ya puso
    su propio `@extend_schema`, se respeta.
    """

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        for nombre in METODOS_HTTP:
            metodo = cls.__dict__.get(nombre)
            if metodo is None or hasattr(metodo, "_spectacular_annotation"):
                continue
            setattr(cls, nombre, extend_schema(responses=RESPUESTAS)(metodo))
