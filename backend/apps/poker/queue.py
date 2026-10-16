"""Cola de emparejamiento del póker.

El backend en memoria vale con una sola instancia de Daphne **siempre que sea la misma
instancia para todo el proceso** (de eso se encarga `get_match_queue`, que la guarda):
con una cola por conexión, cada jugador espera en su propia lista vacía y dos personas
nunca se emparejan. En cuanto hay varias réplicas (`docker compose up --scale
backend=2`) la cola tiene que vivir en Redis, porque entonces ni compartiendo instancia
se verían: dos jugadores conectados a procesos distintos no comparten memoria.

La interfaz es la misma en los dos backends y es asíncrona, que es como la usan los
consumers::

    await queue.join(entry)     # entry: {channel, user_id, username, stake, size}
    await queue.entries()       # lista ordenada por antigüedad (FIFO)
    await queue.remove(channel)
    await queue.purge()         # descarta entradas caducadas
    await queue.clear()         # vaciarla (tests)

El backend se elige con `MATCH_QUEUE_BACKEND` (`memory` | `redis`); por defecto, Redis
si hay `REDIS_URL` y memoria si no.
"""
from __future__ import annotations

import json
import time

from django.conf import settings

# Una entrada que lleva más de esto esperando es de una conexión que ya no está: el
# temporizador de reserva salta mucho antes (QUEUE_TIMEOUT, 15 s), así que en la
# práctica solo recoge restos de procesos muertos. Se caduca por tiempo en los dos
# backends (el channel layer no puede decir qué canales siguen vivos en otro proceso).
ENTRY_TTL = float(getattr(settings, "MATCH_QUEUE_TTL", 60))

REDIS_KEY_ENTRIES = "poker:queue:entries"
REDIS_KEY_ORDER = "poker:queue:order"


class InMemoryMatchQueue:
    """Cola del proceso. Correcta con una sola instancia de Daphne (dev y tests)."""

    def __init__(self) -> None:
        self._entries: dict[str, tuple[float, dict]] = {}

    async def join(self, entry: dict) -> None:
        self._entries[entry["channel"]] = (time.time(), dict(entry))

    async def entries(self) -> list[dict]:
        ordenadas = sorted(self._entries.values(), key=lambda par: par[0])
        return [dict(e) for _, e in ordenadas]

    async def remove(self, channel: str) -> None:
        self._entries.pop(channel, None)

    async def purge(self) -> None:
        """Descarta las entradas caducadas.

        Quien se va de la cola lo dice al desconectarse (`remove`); esto es la red de
        seguridad para procesos que mueren sin avisar. Se caduca por tiempo igual que
        en Redis, para que los dos backends se comporten igual.
        """
        limite = time.time() - ENTRY_TTL
        self._entries = {
            canal: par for canal, par in self._entries.items() if par[0] >= limite
        }

    async def clear(self) -> None:
        self._entries.clear()

    async def count(self) -> int:
        return len(self._entries)


class RedisMatchQueue:
    """Cola compartida entre réplicas.

    Dos claves: un hash con la entrada (canal → JSON) y un zset con la antigüedad de
    cada canal, que es lo que da el orden FIFO y permite caducar por tiempo.
    """

    def __init__(self, url: str) -> None:
        import redis.asyncio as aioredis

        # `protocol=2` explícito: el channel layer de channels-redis espera RESP2.
        self._redis = aioredis.from_url(url, decode_responses=True, protocol=2)

    async def join(self, entry: dict) -> None:
        canal = entry["channel"]
        await self._redis.hset(REDIS_KEY_ENTRIES, canal, json.dumps(entry))
        await self._redis.zadd(REDIS_KEY_ORDER, {canal: time.time()})

    async def entries(self) -> list[dict]:
        canales = await self._redis.zrange(REDIS_KEY_ORDER, 0, -1)
        if not canales:
            return []
        crudos = await self._redis.hmget(REDIS_KEY_ENTRIES, canales)
        salida = []
        for crudo in crudos:
            if not crudo:
                continue        # el hash y el zset se desincronizaron: se ignora
            try:
                salida.append(json.loads(crudo))
            except json.JSONDecodeError:
                continue
        return salida

    async def remove(self, channel: str) -> None:
        await self._redis.hdel(REDIS_KEY_ENTRIES, channel)
        await self._redis.zrem(REDIS_KEY_ORDER, channel)

    async def purge(self) -> None:
        limite = time.time() - ENTRY_TTL
        caducados = await self._redis.zrangebyscore(REDIS_KEY_ORDER, "-inf", limite)
        if not caducados:
            return
        await self._redis.hdel(REDIS_KEY_ENTRIES, *caducados)
        await self._redis.zrem(REDIS_KEY_ORDER, *caducados)

    async def clear(self) -> None:
        await self._redis.delete(REDIS_KEY_ENTRIES, REDIS_KEY_ORDER)

    async def count(self) -> int:
        return int(await self._redis.zcard(REDIS_KEY_ORDER))


#: La cola en memoria, única para todo el proceso (ver `get_match_queue`).
_MEMORY_QUEUE: InMemoryMatchQueue | None = None


def get_match_queue():
    """Devuelve la cola configurada.

    En memoria **tiene** que ser siempre la misma instancia: el consumer la pide al conectar,
    así que si cada conexión se llevara la suya, cada jugador esperaría en su propia lista
    vacía y dos personas no se emparejarían nunca (solo entraban bots, que no pasan por la
    cola). Con Redis da igual crear una instancia por llamada, porque el estado vive allí.
    """
    global _MEMORY_QUEUE

    backend = getattr(settings, "MATCH_QUEUE_BACKEND", "memory")
    if backend == "redis":
        url = getattr(settings, "REDIS_URL", "") or ""
        if not url:
            raise RuntimeError("MATCH_QUEUE_BACKEND=redis pero no hay REDIS_URL")
        return RedisMatchQueue(url)
    if _MEMORY_QUEUE is None:
        _MEMORY_QUEUE = InMemoryMatchQueue()
    return _MEMORY_QUEUE
