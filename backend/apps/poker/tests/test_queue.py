"""Cola de emparejamiento: los dos backends y la fábrica.

El backend en memoria se prueba de verdad; el de Redis se prueba con un cliente de
mentira que implementa las cuatro órdenes que usa (hash + zset), y además hay un test
de integración contra un Redis real que se salta si no hay ninguno levantado.
"""
import json
import os
import time

from django.test import SimpleTestCase, override_settings

from apps.poker.queue import (
    ENTRY_TTL,
    InMemoryMatchQueue,
    RedisMatchQueue,
    get_match_queue,
)


def entrada(canal, stake="low", size=2, user_id=1):
    return {
        "channel": canal, "user_id": user_id, "username": canal,
        "stake": stake, "size": size,
    }


class InMemoryQueueTests(SimpleTestCase):
    def setUp(self):
        self.queue = InMemoryMatchQueue()

    def test_entra_y_sale_en_orden_de_llegada(self):
        async def caso():
            await self.queue.join(entrada("c1"))
            await self.queue.join(entrada("c2"))
            await self.queue.join(entrada("c3"))
            return [e["channel"] for e in await self.queue.entries()]

        self.assertEqual(self.run_async(caso), ["c1", "c2", "c3"])

    def test_quitar_a_uno_no_toca_a_los_demas(self):
        async def caso():
            await self.queue.join(entrada("c1"))
            await self.queue.join(entrada("c2"))
            await self.queue.remove("c1")
            return [e["channel"] for e in await self.queue.entries()]

        self.assertEqual(self.run_async(caso), ["c2"])

    def test_quitar_algo_que_no_esta_no_revienta(self):
        async def caso():
            await self.queue.remove("fantasma")
            return await self.queue.count()

        self.assertEqual(self.run_async(caso), 0)

    def test_la_purga_descarta_lo_caducado(self):
        async def caso():
            await self.queue.join(entrada("viejo"))
            await self.queue.join(entrada("nuevo"))
            # Se envejece la primera entrada a mano.
            self.queue._entries["viejo"] = (time.time() - ENTRY_TTL - 1, entrada("viejo"))
            await self.queue.purge()
            return [e["channel"] for e in await self.queue.entries()]

        self.assertEqual(self.run_async(caso), ["nuevo"])

    def test_vaciar_la_deja_a_cero(self):
        async def caso():
            await self.queue.join(entrada("c1"))
            await self.queue.clear()
            return await self.queue.count()

        self.assertEqual(self.run_async(caso), 0)

    def run_async(self, coro_factory):
        from asgiref.sync import async_to_sync

        return async_to_sync(coro_factory)()


class FakeRedis:
    """Lo mínimo de Redis que usa `RedisMatchQueue` (hash + zset)."""

    def __init__(self):
        self.hashes: dict[str, dict[str, str]] = {}
        self.zsets: dict[str, dict[str, float]] = {}

    async def hset(self, key, field, value):
        self.hashes.setdefault(key, {})[field] = value

    async def hmget(self, key, fields):
        return [self.hashes.get(key, {}).get(f) for f in fields]

    async def hdel(self, key, *fields):
        for f in fields:
            self.hashes.get(key, {}).pop(f, None)

    async def zadd(self, key, mapping):
        self.zsets.setdefault(key, {}).update(mapping)

    async def zrange(self, key, start, end):
        items = sorted(self.zsets.get(key, {}).items(), key=lambda kv: kv[1])
        return [k for k, _ in items]

    async def zrem(self, key, *members):
        for m in members:
            self.zsets.get(key, {}).pop(m, None)

    async def zrangebyscore(self, key, minimo, maximo):
        items = sorted(self.zsets.get(key, {}).items(), key=lambda kv: kv[1])
        return [k for k, score in items if float(minimo) <= score <= float(maximo)]

    async def zcard(self, key):
        return len(self.zsets.get(key, {}))

    async def delete(self, *keys):
        for k in keys:
            self.hashes.pop(k, None)
            self.zsets.pop(k, None)


class RedisQueueTests(SimpleTestCase):
    """El backend de Redis, contra un cliente de mentira."""

    def setUp(self):
        self.queue = RedisMatchQueue.__new__(RedisMatchQueue)   # sin conectar
        self.queue._redis = FakeRedis()

    def test_guarda_y_devuelve_en_orden_de_llegada(self):
        from asgiref.sync import async_to_sync

        async def caso():
            await self.queue.join(entrada("c1"))
            await self.queue.join(entrada("c2"))
            return [e["channel"] for e in await self.queue.entries()]

        self.assertEqual(async_to_sync(caso)(), ["c1", "c2"])

    def test_la_entrada_va_en_json_al_hash(self):
        from asgiref.sync import async_to_sync

        async def caso():
            await self.queue.join(entrada("c1", stake="mid", size=4))
            return json.loads(self.queue._redis.hashes["poker:queue:entries"]["c1"])

        guardada = async_to_sync(caso)()
        self.assertEqual(guardada["stake"], "mid")
        self.assertEqual(guardada["size"], 4)

    def test_quitar_limpia_las_dos_claves(self):
        from asgiref.sync import async_to_sync

        async def caso():
            await self.queue.join(entrada("c1"))
            await self.queue.remove("c1")
            return await self.queue.count(), await self.queue.entries()

        cuantas, restantes = async_to_sync(caso)()
        self.assertEqual(cuantas, 0)
        self.assertEqual(restantes, [])
        self.assertEqual(self.queue._redis.hashes["poker:queue:entries"], {})

    def test_la_purga_borra_solo_lo_caducado(self):
        from asgiref.sync import async_to_sync

        async def caso():
            await self.queue.join(entrada("viejo"))
            await self.queue.join(entrada("nuevo"))
            self.queue._redis.zsets["poker:queue:order"]["viejo"] = time.time() - ENTRY_TTL - 5
            await self.queue.purge()
            return [e["channel"] for e in await self.queue.entries()]

        self.assertEqual(async_to_sync(caso)(), ["nuevo"])

    def test_una_entrada_corrupta_no_tumba_la_cola(self):
        from asgiref.sync import async_to_sync

        async def caso():
            await self.queue.join(entrada("buena"))
            self.queue._redis.hashes["poker:queue:entries"]["rota"] = "{no es json"
            self.queue._redis.zsets["poker:queue:order"]["rota"] = time.time() + 1
            return [e["channel"] for e in await self.queue.entries()]

        self.assertEqual(async_to_sync(caso)(), ["buena"])


class MatchQueueFactoryTests(SimpleTestCase):
    def test_por_defecto_en_memoria(self):
        with override_settings(MATCH_QUEUE_BACKEND="memory"):
            self.assertIsInstance(get_match_queue(), InMemoryMatchQueue)

    def test_en_memoria_es_la_misma_instancia_para_todo_el_proceso(self):
        """Dos conexiones tienen que compartir la cola, o no se empareja nadie.

        El fallo que fija: `get_match_queue()` devolvía una instancia nueva por llamada, así
        que cada jugador esperaba en su propia lista vacía y dos personas no se encontraban
        nunca (solo entraban bots, que no pasan por la cola). Los tests de la cola inyectan la
        instancia a mano, así que nada lo detectaba.
        """
        with override_settings(MATCH_QUEUE_BACKEND="memory"):
            self.assertIs(get_match_queue(), get_match_queue())

    def test_lo_que_encola_una_conexion_lo_ve_la_otra(self):
        """La prueba de verdad, desde fuera: uno entra en la cola y el otro lo ve esperando."""
        from asgiref.sync import async_to_sync

        with override_settings(MATCH_QUEUE_BACKEND="memory"):

            async def caso():
                de_ana = get_match_queue()      # lo que pide la conexión de ana
                de_luis = get_match_queue()     # lo que pide la de luis
                await de_ana.join(
                    {
                        "channel": "ana",
                        "user_id": 1,
                        "username": "ana",
                        "stake": 0,
                        "size": 2,
                    }
                )
                esperando = [e["username"] for e in await de_luis.entries()]
                await de_ana.clear()            # no dejar restos a otros tests
                return esperando

            self.assertEqual(async_to_sync(caso)(), ["ana"])

    def test_redis_sin_url_falla_claro(self):
        with (
            override_settings(MATCH_QUEUE_BACKEND="redis", REDIS_URL=""),
            self.assertRaises(RuntimeError),
        ):
            get_match_queue()

    def test_redis_con_url_devuelve_el_backend_de_redis(self):
        with override_settings(MATCH_QUEUE_BACKEND="redis", REDIS_URL="redis://localhost:6379/0"):
            self.assertIsInstance(get_match_queue(), RedisMatchQueue)


# Integración real: se ejecuta solo si hay un Redis levantado (el del compose).
REDIS_TEST_URL = os.environ.get("REDIS_TEST_URL", "")


class RedisRealTests(SimpleTestCase):
    @classmethod
    def setUpClass(cls):
        if not REDIS_TEST_URL:
            raise cls.skipTest(cls, "sin REDIS_TEST_URL: se salta la integración real")
        super().setUpClass()

    def test_ciclo_completo_contra_redis_de_verdad(self):
        from asgiref.sync import async_to_sync

        queue = RedisMatchQueue(REDIS_TEST_URL)

        async def caso():
            await queue.clear()
            await queue.join(entrada("real-1"))
            await queue.join(entrada("real-2"))
            orden = [e["channel"] for e in await queue.entries()]
            await queue.remove("real-1")
            quedan = [e["channel"] for e in await queue.entries()]
            cuantas = await queue.count()
            await queue.clear()
            return orden, quedan, cuantas

        orden, quedan, cuantas = async_to_sync(caso)()
        self.assertEqual(orden, ["real-1", "real-2"])
        self.assertEqual(quedan, ["real-2"])
        self.assertEqual(cuantas, 1)
