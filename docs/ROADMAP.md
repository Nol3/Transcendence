# ROADMAP — ft_transcendence

Plan de mejora derivado de [`AUDITORIA_PROYECTO.md`](AUDITORIA_PROYECTO.md).
Cada punto tiene **por qué**, **cómo se verifica** y **esfuerzo**, para poder ejecutarlo sin
volver a investigar nada.

## Cómo usar este documento

- Estados: `[ ]` pendiente · `[~]` en curso · `[x]` hecho.
- Prioridades: **P0** rompe la confianza o la demo · **P1** calidad y coherencia · **P2** producto
  · **P3** extras.
- «Hecho cuando» es siempre una comprobación ejecutable (un test, un `curl`, un comando).
- Esfuerzo en horas de una persona que ya conoce el código.

### Resumen

| Bloque | Prioridad | Esfuerzo | Qué arregla |
|---|---|---|---|
| 0. Integridad y privacidad | **P0** | 6–10 h | A1, A2, C1 — ✅ **hecho y verificado** |
| 1. Chat: arreglar o retirar | **P0** | 2–8 h | B1, B2 — ✅ **hecho** (API arreglada + página `/chat`) |
| 2. Calidad y confianza | P1 | 12–18 h | Tests de las 4 apps sin cobertura, CI, linters, e2e caídos |
| 3. Coherencia y documentación | P1 | 8–12 h | i18n incompleto, lobby falso, README para la evaluación, índice de docs |
| 4. Producción y escalado | P1–P2 | 10–16 h | Redis, PostgreSQL, compose de producción, observabilidad |
| 5. El juego como producto | P2 | 20–30 h | 5.1–5.4 ✅ **hechos** (torneos en mesas reales, mesas de 3–6, historial, espectadores y chat de mesa); queda 5.5 |
| 6. Modo local C/WASM | P3 | 4–6 h | Highscores que no persisten, código muerto |
| 7. Extras que suben nota | P3 | variable | Logros, replays, accesibilidad, PWA |
| 8. Juegos nuevos | P2 | 55–75 h | **Mentiroso, Brisca, Tute y Mus** (reglas ya escritas y listas para programar) |

**Total P0 + P1: unas 40–55 h** (una semana de trabajo) para dejar el proyecto sólido y defendible.

---

## ⏸️ DÓNDE RETOMAR — estado a 15-10-2026 (sesión 9)

> **Bloques 0, 1, 2, 3, 5, 6 y 7 completos**; del **4** falta solo la mitad de 4.1 (registro de mesas
> entre réplicas Daphne, con el diseño ya escrito). Además: módulo **Navegadores** (e2e en los cuatro
> motores), apartado **Juegos** (catálogo en `/games`) y los juegos **Culo** (Presidente, local y
> **online entre amigos**), **Mentiroso**, **Brisca**, **Tute** y **Mus** — los cuatro nuevos, con
> motor en TS y en Python, bot, mesa jugable contra bots y **modo servidor** sobre la capa de salas
> compartida. Todo lo marcado ✅ está **verificado con ejecución real**, no supuesto.
>
> **Hecho en las sesiones 9 y 10** (15-10-2026): el **Mus** completo, el modo **«con amigos»** de
> las cuatro pantallas nuevas —lobby compartido y adaptador por juego— y **el e2e de dos navegadores
> de los cuatro**, verificado contra el stack (60/60 en la suite e2e). Lo que queda: la **fase de las
> señas** del Mus (botones que solo ve el compañero y que el servidor verifica) y los modos de 4 por
> parejas de brisca y tute. Los detalles, en el **Bloque 8**.
>
> Las reglas de los cuatro están en [docs/REGLAS_JUEGOS.md](REGLAS_JUEGOS.md) y la investigación que
> llevó a ese orden, en [docs/INVESTIGACION_JUEGOS.md](INVESTIGACION_JUEGOS.md).
>
> **Estado a 15-10-2026 (tarde)**: **los cuatro juegos nuevos están hechos y jugables con amigos**
> —el **Mentiroso** (§8.1), la **Brisca** (§8.2), el **Tute** (§8.3) y el **Mus** (§8.4)—: motor en
> TS y en Python (los mismos casos de test a los dos lados), bot, mesa jugable contra bots y modo
> servidor sobre la capa de salas compartida (`apps/salas/`, 366 tests de backend).
>
> El modo **«con amigos» ya está enchufado en las cuatro pantallas**: un **lobby compartido**
> (`shared/components/sala-lobby/`) que usan los cuatro, y un adaptador por juego que traduce lo que
> manda el servidor a la forma del motor local, para que la mesa sea **la misma** en los dos modos
> en vez de tener una pantalla paralela que se va separando. Verificado con ejecución real: las
> cuatro salas se crean en el servidor (`mentiroso` GUQ7, `brisca` ZCJC, `tute` V89X, `mus` K8P2).
>
> Y **verificado de punta a punta desde el navegador**: el e2e `juegos-online.spec.ts` levanta
> **dos navegadores distintos** (dos cuentas registradas al momento), uno crea la sala, el otro entra
> con el código, el anfitrión añade los bots que falten hasta el mínimo y reparte; después se
> comprueba que los dos ven **su** mano, que las cartas cargan y que a uno de los dos se le activa la
> acción. Los cuatro pasan, y la suite e2e entera queda en **60/60**.
>
> Lo que queda: la **fase de las señas** del Mus, y los modos de 4 por parejas de brisca y tute. El
> Culo sigue con su propia capa de salas: migrarlo a `apps/salas/` es una limpieza pendiente, no un
> requisito.
>
> **Lo que queda por decidir**:
> 1. Los **ficheros siguen sin commitear** — conviene trocear en commits con sentido.
> 2. **4.1, la otra mitad**: el registro de salas/mesas sigue viviendo en el proceso. Con **una**
>    réplica de Daphne (el despliegue normal) no afecta; con varias, dos jugadores podrían no verse.
>    El diseño está escrito abajo (§4.1). **No es necesario para jugar con amigos tal cual está.**

### Estado verificado (números reales de la última ejecución)

| Comprobación | Comando | Resultado |
|---|---|---|
| Tests de backend | `make test-backend` (contenedor, `--parallel auto`) | **366 OK**, 2 skipped, en **3,8 s** (25,5 s en serie) |
| Linter backend | `ruff check .` | **limpio** (24 avisos corregidos, ninguno silenciado) |
| Cobertura backend | `coverage run --source=apps … && coverage report` | **79 %** (exigido ≥70 %) |
| Tests unitarios del front | `make test-front` | **183/183** (24 Mentiroso, 20 Brisca, 21 Tute y 29 Mus) |
| Linter front | `npm run lint` | **limpio** (ESLint + angular-eslint) |
| Traducciones | `npm run i18n:check` | **662 claves** en en/es/fr, las tres alineadas, sin literales sueltos |
| e2e de navegador | `make test-e2e` (todos los núcleos) | **52/52** en 37 s (incluye la partida online entre dos amigos y su recarga) |
| e2e en los cuatro motores | `npx playwright test --project=<chromium\|firefox\|webkit\|msedge>` | **34/34** en cada uno |
| Accesibilidad (axe) | `cd front && npx playwright test e2e/a11y.spec.ts --project=chromium` | **8/8 pantallas sin violaciones** |
| PWA instalable | `node scripts/audit/probe_pwa.js` | **8/8** (service worker + manifiesto + cachés) |
| Replay de manos | `cd front && npx playwright test e2e/poker-history.spec.ts` | **5/5** (incluye el paso a paso) |
| Integridad P0 (A1/C1/B1) | `bash scripts/audit/audit_integrity.sh` | A1 **OK** · C1 **OK** · B1 **200/200** |
| Match de torneo en mesa real | `python scripts/audit/probe_tournament_table.py https://localhost:8443` | **18/18** |
| Mesas de 3–6 | `python scripts/audit/probe_multi_seat.py https://localhost:8443` | **11/11** |
| Chat de punta a punta | `node scripts/audit/probe_chat_ui.js https://localhost:8443 https://localhost:8443` | **10/10** |
| Póker en navegador real | `node scripts/audit/probe_poker_ui_deploy.js https://localhost:8443 https://localhost:8443` | **15/15** |
| Mesa de 6 desde la UI | `node scripts/audit/probe_poker_ui_6.js …` | **8/8** |
| Tema del tapete | `node scripts/audit/probe_poker_theme.js …` | **8/8** |
| Espectadores y chat de mesa | `python scripts/audit/probe_spectators.py https://localhost:8443` | **12/12** |
| Salud del stack | `curl -sk https://localhost:8443/api/health/` | `{"status":"healthy","checks":{"db":"ok","redis":"ok"}}` |
| Juego C/WASM arranca | `node scripts/audit/probe_wasm.js https://localhost:8443/game-embed/index.html` | canvas 1280×720 · WebGL · 0 excepciones |
| Highscores persistentes | `node scripts/audit/probe_wasm_persistencia.js …` | **7/7** (escribe, recarga y sigue ahí) |
| Idioma de la API | `curl -sk -H "Accept-Language: fr" https://localhost:8443/api/health/` | `…,"lang":"fr"` |
| Errores de la API traducidos | `curl -sk -H "Accept-Language: fr" -X POST -H "Content-Type: application/json" -d '{"email":"x@y.z","password":"n"}' https://localhost:8443/api/auth/login/` | `{"error":"Identifiants incorrects"}` |
| Reglas del Culo | `cd backend && python manage.py test apps.culo` | **47 OK** (28 del motor con una partida entera; 16 de salas; 3 del WebSocket) |
| Motor del Culo en el front | `cd front && npm test` | **25 tests** del motor + 4 e2e (mesa, turno, ronda entera) |
| **Culo online entre dos amigos** | `cd front && npx playwright test e2e/culo-online.spec.ts --project=chromium` | **1/1**: dos navegadores distintos, cuentas creadas al vuelo, uno crea la sala, el otro entra con el código, se reparte y cada uno ve **su** mano |
| Crear sala (API) | `curl -sk -X POST -H "Authorization: Bearer $TOKEN" -d '{"decks":1}' https://localhost:8443/api/culo/rooms/` | `201 {"code":"932R","decks":1,"status":"lobby","maxPlayers":6}` |
| Recargar a mitad de partida | dentro de `e2e/culo-online.spec.ts` | Luis recarga la página y vuelve **a su mesa y a su mano** (el código va en la URL) |
| Carrera de reconexión | `python manage.py test apps.culo` | `test_la_conexion_vieja_no_echa_al_que_ya_ha_vuelto` **OK** |
| Salas genéricas (nuevo) | `python manage.py test apps.mentiroso` | **48 OK** (motor, sala, API y 5 de WebSocket real) |
| Brisca | `python manage.py test apps.brisca` | **20 OK** (bazas, motor, cambio de triunfo y partida entera) |
| Tute (nuevo) | `python manage.py test apps.tute` | **22 OK** (obligaciones, acuses, tute, diez últimas y partida entera) |
| Mus (nuevo) | `python manage.py test apps.mus` | **30 OK** (ocho reyes, pares, orden del juego, envites, 40 piedras y una vaca entera) |
| Juegos online de los cuatro (nuevo) | `npx playwright test e2e/juegos-online.spec.ts` | **4/4** con dos navegadores de verdad contra el servidor |
| Suite e2e completa | `npx playwright test --project=chromium` | **60/60** en 42,8 s |
| Juegos online disponibles | `curl -sk .../api/salas/juegos/` | `mentiroso`, `brisca`, `tute` y `mus`, cada uno con sus límites y opciones |
| Juegos online por API | `curl -sk .../api/salas/juegos/ -H "Authorization: Bearer ***"` | `{"mentiroso":{"minPlayers":3,"maxPlayers":6,"opciones":{"manos":3}}}` |
| Crear sala de cualquier juego | `curl -sk -X POST .../api/salas/ -d '{"juego":"mentiroso"}'` | `201 {"code":"H7QK","juego":"mentiroso","status":"lobby",…}` |

Los probes que apuntan a `https://localhost:8443` necesitan el stack levantado (`docker compose up -d`).

### Lo que se hizo en esta sesión (por orden)

1. **2.4 · Linters y cobertura** — `backend/ruff.toml`; los 24 avisos **corregidos**, no silenciados.
   Cobertura **79 %**. En el front no había ni ESLint: `eslint.config.js` + `npm run lint`.
2. **2.5 · Tests unitarios del front** — **42 tests**. Dos defectos reales por el camino: `npm test`
   **no arrancaba** (target `test` de `angular.json` incompleto) y la app es **zoneless** (faltaba
   `provideZonelessChangeDetection` en el TestBed → `src/test-providers.ts`).
3. **3.2 · i18n completo** — 39 literales → 9 legítimos; las 12 notificaciones a claves `notify.*`.
   **Claves que faltaban de verdad** (`notifications.title`, `notifications.noNotifications`,
   `profile.username` en los tres idiomas → el panel mostraba la clave cruda). Guardia:
   `npm run i18n:check`, también en el CI.
4. **3.4 · Índice y documentación** — versiones reales (Angular 20, no 21/18) y `backend/README.md`
   ya lista la app `poker` con sus endpoints.
5. **4.1 (mitad) · Redis** — `channels-redis`, `CHANNEL_LAYERS` por entorno y la **cola de
   emparejamiento en Redis** (`apps/poker/queue.py`, dos backends con la misma interfaz asíncrona).
   14 tests, incluido uno **contra un Redis real dentro del contenedor** (verde).
6. **4.2 · PostgreSQL** — servicio, `psycopg`, settings por motor y `CONN_MAX_AGE`. Verificado: con
   `DB_ENGINE=django.db.backends.postgresql` migra y crea las 17 tablas.
7. **4.3 · Compose de producción** — `compose.prod.yaml` con `!override` (quita el bind mount del
   código) y **Daphne**. Verificado end-to-end con health `healthy` y logs JSON.
8. **4.4 · Observabilidad** — logs JSON con `request_id` y `/api/health/` que comprueba BD y Redis
   y devuelve **503** si alguno cae. 13 tests.
9. **6.2 · Código muerto del C** — tres declaraciones huérfanas, `game_api.{c,h}` y una función de
   animación sin usar; fuera. WASM reconstruido y probado en navegador.
10. **6.1 · Highscores persistentes** — `highscores.dat` pasa a `/persist` montado como **IDBFS**
    (con `FS.syncfs` al guardar); sondeo nuevo `probe_wasm_persistencia.js` → **7/7**.
11. **7.5 · i18n de la API** — `LocaleMiddleware` + `LANGUAGES`, 27 mensajes envueltos en
    `gettext_lazy` (15 únicos) y catálogos es/en/fr; verificado en los tres idiomas contra el stack.
12. **7.1 · Logros del póker** — `achievements.py` (sin modelo nuevo) + endpoint + tarjeta en
    `/poker/history`; 11 tests.
13. **Módulo «Navegadores»** — los e2e pasan a correr en **los cuatro motores** (antes solo
    chromium). Chromium, firefox, webkit y msedge: **34/34 en cada uno**. El CI instala e ejecuta
    chromium+firefox+webkit. Nota: firefox en local, con el paralelismo por defecto, es *flaky*
    (3 fallos de timing de 34); con `--workers=2` da 34/34, y en CI va con 1 worker y 2 reintentos.
14. **7.3 · Accesibilidad** — `e2e/a11y.spec.ts` con axe (`wcag2a`/`wcag2aa`) sobre 7 pantallas.
    Dos defectos reales: el botón de avisos era solo un SVG (sin nombre accesible) y
    `--color-text-muted` daba **2,1:1** de contraste. Arreglados los dos (y la opacidad de los
    logros bloqueados, que bajaba a 2,35:1): **7/7 sin violaciones**.
15. **7.4 · PWA** — `@angular/service-worker` (a mano: `ng add` exige la versión exacta de
    `@angular/core`), `ngsw-config.json`, 8 iconos maskable y nginx con `no-cache` para el worker y
    el MIME del manifiesto. `probe_pwa.js` → **8/8**. Los e2e se cuelgan contra un build con service
    worker (sirve de su caché y se salta los mocks) → `serviceWorkers: 'block'` en el config: la
    suite bajó de 2,4 min a 23 s.
16. **7.2 · Replays de manos** — el motor ya emitía el log de la mano; ahora se **guarda**
    (`PokerHandRecord.actions` + migración) y se puede **volver a ver** mano a mano desde
    `/poker/history`, con controles y autoplay. Endpoint propio que devuelve 403 si no jugaste esa
    mano. 7 tests + 10 unitarios.
17. **Apartado «Juegos»** — `core/games/game-catalog.ts` es la **única fuente de verdad**: añadir un
    juego es una entrada más una ruta (ver `docs/JUEGOS.md`). Pantalla `/games` y menú
    Inicio · Juegos · Torneos · Chat · Perfil. El Culo entra también en la auditoría de axe.
18. **Juego «Culo» (Presidente)** — baraja española de 40 cartas, motor **puro** en TS (recibe
    estado, devuelve estado) y bots. Reglas: se responde con **la misma cantidad** de cartas y
    **valor superior**; el **5 de oros** está por encima de todo; al final, Presidente /
    Vicepresidente / neutros / Viceculo / Culo con intercambio de cartas. 25 tests del motor.
19. **Culo online (lo que pidió el usuario)** — `backend/apps/culo/`: salas con código de 4
    caracteres, **servidor autoritativo** por WebSocket (el navegador no decide nada), rutas
    genéricas `ws/culo/room/<código>/`. El front estrena un servicio de sala que **normaliza el
    estado del servidor a la misma forma que el motor local**, así que la mesa es la misma en los
    dos modos; el menú ofrece local, crear sala (con código para dictar y enlace
    `/culo?codigo=XXXX`) y entrar con código. 46 tests de backend y la prueba de los dos amigos.

20. **Aguantar una recarga (y los cabos sueltos)** — jugar con amigos en el móvil significa que el
    navegador recarga solo al volver del segundo plano. Ahora el **código de la sala queda en la
    URL** al crearla o al entrar, así que al recargar se vuelve directo a la partida (el arranque
    del componente lee el código y entra solo), y si se corta la conexión hay un botón para volver
    sin salir de la mesa. Por el camino salió una **carrera real**: al recargar, la conexión nueva
    entra antes de que la vieja acabe de cerrarse, y la vieja marcaba al jugador como desconectado
    estando dentro. Arreglado pasando el canal (`Room.disconnect(user_id, channel)`: solo se da por
    ido si la que cae es la conexión actual) y con un test que reproduce el orden real.
    Además: `RoomService` del front **retirado** (137 líneas que apuntaban a unos `/api/rooms` que
    devuelven 404, código del póker que quedó huérfano) y los artefactos de Playwright **fuera del
    índice** (`git rm -r --cached`, que es lo que indicaba el propio `.gitignore`; los ficheros
    siguen en disco).

### ⚠️ Pasar los tests: en paralelo, y el contenedor no es el mismo entorno

**En paralelo, siempre.** En un solo núcleo estas suites tardan ~5 veces más: la de backend,
21 s en serie y **4,7 s** con `--parallel auto`; los e2e, **3,1 min** con `--workers=1` y **37 s**
con todos los núcleos. Está en `make test`, `make test-backend`, `make test-front` y `make test-e2e`,
para no tener que acordarse.

**Y ojo con dónde se corre.** La lección antigua decía «mejor dentro del contenedor»; resulta que
dentro del contenedor la suite **no pasaba**: daba **40 fallos y 29 errores**, todos `301 != 200`.
La causa no era el código: el contenedor corre con `DJANGO_DEBUG=false`, y con eso los settings
activan `SECURE_SSL_REDIRECT`, así que **cada petición de los tests recibía un 301 a HTTPS**. Se
arregla pasando el entorno de desarrollo al ejecutar:

```bash
docker compose exec -T -e DJANGO_DEBUG=true backend python manage.py test --parallel auto
```

Además salió un test que **dependía del entorno sin decirlo** (`test_sin_redis_configurado_no_lo_cuenta_como_fallo`
daba por hecho que no había `REDIS_URL`; dentro del contenedor sí la hay, así que el health devolvía
`ok` y el test fallaba). Ahora fuerza el escenario con `self.settings(REDIS_URL="")`: un test tiene
que montar su propio escenario, no heredar el de la máquina donde corre.

> Detalle de Django: con `--parallel`, si un worker falla, a veces revienta al intentar devolver el
> traceback (`TypeError: cannot pickle 'traceback' object`) y te tapa el fallo de verdad. Si ves eso,
> corre la suite **en serie** una vez para leer el error real.

### ⚠️ Cambiar una pantalla rompe los e2e que la conocían

El menú nuevo del Culo tiene **tres** botones (local, crear sala, entrar) donde antes había uno, y
cinco e2e que hacían `.inicio app-button button` pasaron a fallar por *strict mode violation* (o a
esperar un `<select>` que ya no era el que creían, porque los ajustes cambiaron de orden). Lección:
cuando una pantalla gana controles, **los localizadores de los tests hay que revisarlos en el mismo
cambio**; dejar clases estables (`.modo__local`, `.inicio__campo--jugadores`) ahorra el problema.

### ⚠️ Lo que costó encontrar la prueba online (y su lección)

**1) `baseURL` de Playwright no es un prefijo.** Con `baseURL: 'https://host/api'`, una llamada a
`post('/auth/register')` va a **`https://host/auth/register`**: Playwright resuelve las rutas que
empiezan por «/» contra la **raíz**. El POST acababa en el contenedor del front (estático) y nginx
devolvía **405**. La lección: el prefijo va en cada llamada, no en el `baseURL`.

**2) La app hay que abrirla por nginx, no por el contenedor del front.** Servida desde `:4200` no
hay proxy de `/api` (el `301` a HTTPS lo delataba), así que crear sala fallaba aunque el endpoint
respondiera 201 por curl. Por `:8443` conviven app, API y WebSocket, que es como la usa la gente.
Los e2e que van con mocks no lo notan nunca; el que habla con el servidor de verdad, sí.

**3) El guard mira el usuario, no solo el token.** `isAuthenticated` sale de `_user()`, que se
restaura de `current_user` en localStorage: con solo `access_token` la app te manda a `/login`.

### ⚠️ Los dos fallos que costaron encontrar (y su lección)

**1) Claves enteras y msgpack.**

Al pasar el channel layer a Redis, los sondeos de navegador empezaron a fallar (1011 en
espectadores, la mano no avanzaba, la mesa no repartía segunda mano). No era Redis ni la cola:
`channels_redis` serializa con **msgpack**, y msgpack **rechaza las claves de diccionario que no
son de texto** (`int is not allowed for map key`). El motor mandaba `revealed`, `hands` y `payouts`
con **claves enteras**, y con la capa en memoria eso no se notaba **porque no se serializa nada**.

- Arreglado en `engine/game.py` (claves `str(i)`, que además es lo que el front ya esperaba con
  `String(seat)`).
- **Guardián nuevo**: `apps/poker/tests/test_channel_payloads.py` recorre los payloads reales
  (resultado, estado por asiento, log de la mesa) y comprueba que ninguna clave es entera y que
  msgpack los empaqueta. Encontró el segundo sitio (`payouts` del log) él solo.
- **Lección**: todo lo que cruce el channel layer tiene que ser serializable; con la capa en memoria
  esa regla no se comprueba sola.

**2) SQLite se bloquea con escrituras a la vez.** Al correr los sondeos en paralelo aparecieron
`database is locked` (y un registro tardó 19 s y acabó en 500). SQLite admite **un solo escritor**;
sin espera, la segunda petición falla en el acto. Arreglado en `settings.py`: `PRAGMA
journal_mode=WAL` en cada conexión (con la señal `connection_created`) y `timeout` de 20 s, así la
escritura espera en vez de reventar. Verificado en el contenedor: `journal_mode: wal`,
`busy_timeout: 20000`. **Esto no sustituye a PostgreSQL** (4.2): es para que la demo aguante la
concurrencia; el despliegue de verdad sigue queriendo Postgres.

### Siguiente paso recomendado (en este orden)

1. **Re-correr los sondeos de navegador** (póker UI, mesa de 6, tema, espectadores) con el arreglo
   de msgpack desplegado: es la prueba de que la regresión está cerrada.
2. **4.1, la otra mitad** — el **registro de mesas** sigue siendo del proceso que creó la mesa. El
   diseño: la mesa se une a un grupo `poker_table_<id>` con su propio canal (`new_channel()` + tarea
   que escucha) y el `TableConsumer` que caiga en otra réplica le **reenvía la acción** por ese
   grupo; las vistas ya viajan por el channel layer. Ojo: con `--scale backend=2`, nginx resuelve
   `backend` una sola vez al arrancar, así que hace falta un `resolver` + variable en el
   `proxy_pass` para que reparta de verdad; sin eso el test no probaría nada.
3. **Bloque 7 — Extras** (P3): **completo** — 7.5 (i18n de la API), 7.1 (logros), 7.2 (replays),
   7.3 (accesibilidad) y 7.4 (PWA) ✅.
5. **Preparar los commits** del póker: `backend/apps/poker/`, `front/.../poker.*` y
   `front/.../chat.*` siguen apareciendo como nuevos en `git status`.

### Cabos sueltos conocidos (no bloquean nada)

- **Decisión del usuario pendiente**: dejar de versionar `front/test-results/` y
  `front/playwright-report/` (`git rm -r --cached …`). Las reglas de `.gitignore` ya están puestas.
- **`RoomService`** (`core/services/room.service.ts`): sus endpoints `/api/rooms` son 404 y no lo usa
  nadie. Decidir: implementar `/rooms` o borrarlo (3.1 lo dejó señalado).
- **Inasistencia en un match de torneo**: si un jugador no entra, la mesa le espera sin límite.
- **ELO en mesas de 3–6**: no puntúa (el ELO del proyecto es 1v1); el resultado sí queda en el
  historial. Documentado en `POKER_ONLINE.md` §8.
- **El chat se refresca por sondeo** (5 s), no por WebSocket. Suficiente para una demo.
- **Base de datos**: el `.env` del usuario se queda en SQLite a propósito, para no vaciarle la demo
  (47 usuarios y sus torneos). Cambiar a PostgreSQL son dos líneas (`DB_ENGINE` y `DB_NAME`).
- **Sentry** (4.4, opcional): no añadido para no meter una dependencia externa en una demo.
- **No pasar la suite de tests desde WSL sobre la base de datos real**: `coverage run manage.py test`
  ejecutado en WSL sobre `/mnt/c/...` deja el fichero SQLite (WAL) en un estado que el contenedor
  no puede abrir — el backend pasa a `degraded` con `unable to open database file`, mientras que
  `select 1` sí funciona. Se arregla reiniciando el backend (`docker compose restart backend`), que
  vuelve a crear `-wal`/`-shm`. Lo limpio es ejecutar la suite **dentro del contenedor**.
- **`runserver` se atasca al reiniciar en Windows** (observado 12-10-2026): el backend de
  desarrollo monta `./backend:/app` y el *autoreloader* de Django vigila un bind mount de Windows;
  a veces el proceso queda escuchando en el 8000 sin responder y nginx devuelve **502**. Se
  arregla recreando el contenedor: `docker compose up -d --force-recreate backend`. No afecta al
  despliegue de producción (4.3), que no monta el código y sirve con Daphne.
- **Modo local C/WASM** (Bloque 6): el juego de cartas sigue siendo un scorer tipo Balatro; no es
  póker y no se ha tocado (su auditoría está en `AUDITORIA_JUEGO_POKER.md`).

### Cómo arrancar la próxima sesión (2 minutos)

```bash
cd C:/Users/aleja/Desktop/github/Transcendence
docker compose up -d                 # stack completo (HTTPS en :8443)
docker compose ps                    # los seis servicios en healthy
curl -sk https://localhost:8443/api/health/

# verificación rápida de que todo sigue verde
wsl.exe -d Ubuntu -- bash -lc 'cd /mnt/c/Users/aleja/Desktop/github/Transcendence/backend &&   /mnt/c/Users/aleja/AppData/Local/hermes/cache/scratch/tsc_venv/bin/python manage.py test'
cd front && npm run lint && npm test -- --watch=false && npx playwright test --project=chromium --reporter=line
bash scripts/audit/audit_integrity.sh
```

Ojo con dos trampas ya documentadas: el backend lee `DJANGO_DEBUG` (no `DEBUG`) y en local manda
`backend/.env` (no el `.env` de la raíz, que es el de Compose).
---

## Bloque 0 — Integridad y privacidad · P0

Verificación de todo el bloque: `bash scripts/audit/audit_integrity.sh` (reproduce los tres
hallazgos y debe dejar de marcar «VULNERABLE» al terminar).

### 0.1 · Cerrar la vía de ELO regalado 🔴
- **Qué**: `POST /api/games/create_game/` + `/finish/` permiten a un usuario declararse ganador
  contra el bot fantasma y subir ELO. Medido: `wins 0→1`, `elo 1600→1616`, nº 1 del ranking.
- **Por qué**: es la integridad del ranking y de la estadística; un evaluador lo ve en 30 segundos.
- **Cómo** (elegir una):
  1. **Marcar como no puntuables** las partidas del modo local: `create_game` crea el `Game` con
     `rated=False` (ya existe el parámetro en `finish_game`) y `finish` lo respeta. Es el cambio
     mínimo y conserva el historial.
  2. Además, exigir que `finish` solo lo pueda cerrar el servidor para las partidas puntuables
     (las del póker online ya lo hacen así).
- **Hecho cuando**: un test llama a `create_game` + `finish` declarándose ganador y el perfil
  sigue con `win_count=0` y `elo_rating=1600`; y el ranking público no lo muestra arriba.
- **Ficheros**: `backend/apps/games/views.py`, `services.py`, `backend/apps/games/tests.py` (nuevo).
- Esfuerzo: **2–3 h**.
- **Hecho** ✅ (12-10-2026) Campo `Game.rated` (migración `games/0002_game_rated`); `create_game`
  crea `rated=False` y `finish` respeta `game.rated`: el resultado del navegador queda en el
  historial pero no mueve ELO ni victorias. De paso se arregló la **racha** de `/users/me/stats/`
  (contaba todas las victorias seguidas sin cortar en las derrotas, y sumaba partidas no
  puntuables). Verificado con `apps/games/tests.py` (10 tests) y `scripts/audit/audit_integrity.sh`
  contra el stack desplegado: `wins 0`, `elo 1600`, `streak 0`.

### 0.2 · El resultado de un torneo no puede declararlo el jugador 🔴
- **Qué**: hoy cualquiera de los dos jugadores puede reportar `winner_slot` sin jugar.
- **Cómo**:
  1. Cuando el bracket lanza una partida, crear la mesa de póker correspondiente y **cerrar el
     resultado desde el servidor** (el hook `on_match_end` ya existe).
  2. Mientras eso no esté, exigir **confirmación de los dos jugadores** (o del creador) para dar
     un match por cerrado, y dejar registro de quién lo reportó.
- **Hecho cuando**: un test comprueba que un jugador que reporta su propia victoria sin que el
  rival confirme no avanza el bracket (o que el resultado lo escribe el servidor).
- **Ficheros**: `backend/apps/tournament/views.py`, `services.py`, `tests.py`.
- Esfuerzo: **3–5 h** (versión «doble confirmación») · se abarata si se hace junto con 5.1.
- **Depende de**: decisión D2 (abajo).
- **Hecho** ✅ (12-10-2026) versión «doble confirmación»: estado `awaiting_confirmation` +
  `result_winner_slot` + `result_reported_by` (migración `tournament/0003`). El **creador arbitra**
  (su reporte cierra el match); un **jugador declara** y el match queda pendiente hasta que **el
  rival confirma el mismo ganador**; si declaran ganadores distintos → **409** y decide el creador.
  El bracket **no avanza** mientras el match no esté `completed`. En el front, el bracket muestra el
  estado y los botones pasan a «✔ Confirmar» / «✖ No estoy de acuerdo». Verificado con
  `apps/tournament/tests.py::ResultConfirmationTests` (7 tests: declarar solo no avanza, el rival
  confirma y cierra, conflicto 409, el creador arbitra, desconocido 403, corregir la declaración).
  Queda pendiente la vía fuerte (5.1: cerrar el resultado desde la mesa de póker, sin humanos).

### 0.3 · Dejar de exponer emails 🔴
- **Qué**: `GET /api/users/` devuelve el email de todos los usuarios; el chat hace lo mismo con
  emisor y receptor.
- **Cómo**: crear un serializador público (`id`, `username`, `avatar`, `elo`, `wins/losses`) y
  usarlo en el listado de usuarios y en el chat. El email solo se devuelve en `/api/auth/me/` y en
  el propio perfil.
- **Hecho cuando**: `curl /api/users/` no contiene la cadena `@` en ningún campo; un test lo fija.
- **Ficheros**: `backend/apps/users/serializers.py`, `views.py`, `apps/chat/serializers.py`,
  `apps/public_api/serializers.py`, tests de `users`.
- Esfuerzo: **2 h**.
- **Hecho** ✅ (12-10-2026) `PublicUserSerializer` (sin email) en `users` (listado y ficha) y en
  chat, partidas y torneos (participantes, creador, ganador y jugadores de cada match). El email
  solo lo devuelven `/api/auth/me/`, el login/registro y el perfil propio. Verificado con
  `apps/users/tests.py` (6 tests) y `audit_integrity.sh` contra el stack: **11 usuarios, 0 con email**.

---

## Bloque 1 — Chat: arreglar o retirar · P0

### 1.1 · Decidir: ¿se queda el chat? (decisión D1) — ✅ decidido: se queda, con interfaz
- **Decisión del equipo (12-10-2026)**: el chat **se queda** y pasa a tener interfaz propia
  (`/chat`), porque es un módulo típico de ft_transcendence y ahora sí aporta (1.2 + 1.3 + 1.5).

### 1.2 · Arreglar el `NameError` que devuelve 500 🔴 — ✅ hecho
- **Qué**: `apps/chat/views.py` usa `models.Q` sin importar `models`.
- **Cómo**: `from django.db import models` (o `from django.db.models import Q` y usarlo).
- **Hecho cuando**: `GET /api/chat/messages/` y `/conversation/?user_id=N` devuelven 200.
- Esfuerzo: **30 min**.
- **Hecho** ✅ (12-10-2026) `from django.db.models import Q` (el `NameError` era `models.Q` sin
  importar `models`), orden explícito en el queryset, `SendMessageSerializer` que valida antes de
  tocar la BD (destinatario inexistente → **400** en vez de IntegrityError 500, contenido vacío →
  400, mensaje a uno mismo → 400), `conversation` valida `user_id` (400 en vez de 500),
  `http_method_names` sin edición/borrado y nueva acción `mark_read`. Verificado con
  `apps/chat/tests.py` (12 tests) y contra el stack desplegado: los dos endpoints → **200**.

### 1.3 · Endurecer el chat (si se queda) — ✅ hecho
- Validar que el destinatario existe y no es uno mismo; no permitir leer conversaciones ajenas;
  marcar `is_read`; paginar; WebSocket para tiempo real (o dejarlo REST y decirlo).
- **Hecho cuando**: tests de `send_message` (destinatario inexistente → 400), de aislamiento entre
  usuarios y de `conversation` (no devuelve mensajes de terceros).
- Esfuerzo: **4–6 h** (+ 4–6 h la UI).
- **Hecho** ✅ (12-10-2026) Todo eso está cubierto por los 12 tests de `apps/chat/tests.py`:
  destinatario inexistente/vacío/a uno mismo → 400, aislamiento (solo se ven los mensajes en los que
  participas), `conversation` valida `user_id`, `mark_read`, y sin sesión → 401/403. **El tiempo
  real se resuelve por sondeo** (cada 5 s desde la UI), no con WebSocket: el chat no tiene consumer y
  no merece la pena por ahora; queda anotado abajo.

### 1.5 · Página de chat en la web — ✅ hecho
- **Qué**: el chat solo existía como API (invisible para quien evalúa).
- **Cómo**: `/chat` con lista de conversaciones (agrupadas por usuario, con último mensaje y
  contador de sin leer), hilo abierto, caja de escritura (Enter envía, Mayús+Enter salta de línea)
  y buscador para empezar una conversación nueva. Enlace en la cabecera (escritorio y móvil) y
  claves i18n en es/en/fr. Refresco por sondeo cada 5 s.
- **Ficheros**: `front/src/app/core/services/chat.service.ts`, `front/src/app/features/chat/*`,
  `app.routes.ts`, `header.html`, `public/i18n/*.json`.
- **Hecho** ✅ verificado con `front/e2e/chat.spec.ts` (4 tests) y, contra el stack desplegado,
  `scripts/audit/probe_chat_ui.js` → **10/10**: A escribe a B por API, B abre `/chat` en un
  navegador real, ve la conversación con el aviso de sin leer, la abre, responde por la UI y **el
  servidor confirma la respuesta** (comprobado por API como A).

### 1.4 · O retirarlo limpiamente
- Quitar `apps.chat` de `INSTALLED_APPS`, la ruta `/api/chat/`, la app y sus migraciones.
- **Hecho cuando**: `manage.py check` limpio y `/api/chat/` → 404; ningún 500 en el proyecto.
- Esfuerzo: **1 h**.

---

## Bloque 2 — Calidad y confianza · P1

### 2.1 · Tests para las apps sin cobertura
- **Qué**: `users` (registro/login/validaciones/perfil/stats), `games` (crear/finish/permisos/ELO),
  `public_api` (API key válida/inválida/rate limit), `chat` (si se queda).
- **Hecho cuando**: `manage.py test` pasa de 58 a **≥ 90 tests** y ninguna app queda a cero.
- Esfuerzo: **6–8 h**.

### 2.2 · Arreglar los 2 e2e caídos — ✅ hecho
- **Qué**: los tests `tournaments.spec.ts:73` y `:87` fallan en su `click` (líneas **78** y **91**)
  esperando un botón `getByRole('button', { name: /view bracket/i })` que ya no existe.
- **Cómo**: actualizar los selectores al DOM real del bracket (o exponer `data-testid` estables en
  el bracket y usarlos).
- **Hecho cuando**: `npx playwright test --project=chromium` → **20/20**.
- Esfuerzo: **2 h**.
- **Hecho** ✅ (12-10-2026) la causa no era la UI: los mocks de Playwright (`mockTournaments` y
  `mockTournamentFlow`, en `front/e2e/helpers.ts`) devolvían un **array plano**, pero
  `TournamentService.getTournaments()` espera el sobre **paginado** de DRF (`{results: [...]}`) →
  `response.results.map(...)` reventaba, la lista quedaba vacía y el botón «View Bracket» nunca
  aparecía. Arreglados los dos mocks: `tournaments.spec.ts` pasa **7/7** (antes 5/7).

### 2.3 · CI en GitHub Actions
- **Qué**: no hay `.github/workflows`.
- **Cómo**: un workflow con dos jobs:
  - backend: `python manage.py check`, `check --deploy`, `manage.py test`.
  - frontend: `npm ci`, `npm run build`, `npx playwright test`.
  - (opcional) publicar la cobertura.
- **Hecho cuando**: el workflow pasa en un PR de prueba y falla si se rompe un test.
- Esfuerzo: **2–3 h**.

### 2.4 · Linters y cobertura — ✅ hecho
- **Backend**: `ruff` (lint + formato) y `coverage`/`pytest-cov`; objetivo ≥ 70 % en `apps/`.
- **Frontend**: ESLint (Angular trae el esquema) sobre `front/src`.
- **Hecho cuando**: `ruff check` limpio, `coverage report` ≥ 70 %, `npm run lint` limpio, y todo
  enchufado al CI de 2.3.
- Esfuerzo: **3–5 h**.
- **Hecho** ✅ (12-10-2026). `backend/ruff.toml` con `E,F,W,I,UP,B,SIM` y `line-length=100`. Los 24
  avisos iniciales se **corrigieron**, no se silenciaron: líneas largas partidas, `zip(..., strict=False)`,
  `raise … from None` / `from exc` (B904), `contextlib.suppress` (SIM105), ternarios (SIM108),
  `enumerate` en vez de contador a mano (SIM113) y el `from datetime import timedelta` que estaba en
  medio de `settings.py` (E402). El auto-fix dejó además tres sentencias muertas
  (`id_info.get("name", "")`, `users[start:end]`) que se eliminaron. Cobertura **78 %**.
  En el front **no había ESLint**: se añadió `eslint.config.js` (formato plano, ESLint 9 +
  `angular-eslint`), `npm run lint` y los 9 avisos que salieron, corregidos. Todo en el CI (2.3).

### 2.5 · Tests unitarios de frontend — ✅ hecho
- **Qué**: solo existe `app.spec.ts`. Cubrir lo que más duele: `PokerService` (estados del socket,
  acciones legales, temporizadores), `AuthService`, `I18nService` y 2–3 componentes.
- **Hecho cuando**: `npm test` con ≥ 15 tests en verde.
- Esfuerzo: **4–6 h**.
- **Hecho** ✅ (12-10-2026): **42 tests** en 5 ficheros (`poker.service` 17, `chat.service` 11,
  `i18n` 7, `poker-history.service` 5, `app` 2). Dos defectos reales por el camino: **`npm test` no
  arrancaba** (el target `test` de `angular.json` estaba incompleto: sin `buildTarget`, `tsConfig` ni
  `runner`) y **la app es zoneless** (Angular 20), así que el TestBed necesitaba
  `provideZonelessChangeDetection` — resuelto con `src/test-providers.ts` (`providersFile`) y
  `resolveJsonModule` en `tsconfig.spec.json`. El `app.spec.ts` original era el boilerplate de
  Angular (buscaba «Hello, front»), reescrito. `PokerService` se prueba con un **WebSocket de
  mentira** que empuja mensajes del servidor: cola → match → mesa, acciones legales, espectador,
  chat y reset.

---

## Bloque 3 — Coherencia del producto y documentación · P1

### 3.1 · Limpiar el lobby antiguo (`/game`) 🟡 — ✅ hecho
- **Qué**: muestra badges «Searching…/Matched» y llama a `/api/rooms`, `/api/matchmaking/start`
  (404). Ahora que el matchmaking real está en `/poker`, esto engaña.
- **Cómo**: quitar `onlineStatus`, `connectMatchmaking` y `RoomService` (borrar el servicio: todos
  sus endpoints son 404), y dejar `/game` como **«Modo local (mismo dispositivo)»** con su texto
  correcto. Enlazar desde ahí a `/poker`.
- **Hecho cuando**: `grep -r "api/rooms" front/src` no devuelve nada y `/game` no muestra ningún
  estado de conexión falso.
- Esfuerzo: **2 h**.
- **Hecho** ✅ (12-10-2026, parcial) fuera `connectMatchmaking`, `onlineStatus` y el `RoomService`
  del lobby: `/game` ya no finge buscar partida. La insignia dice **«JUEGO LOCAL»** y se añadió un
  acceso visible al póker online real (`/poker`, con su cola de espera). El subtítulo ya describe
  el modo hotseat. Claves i18n nuevas en es/en/fr: `lobby.localMode`, `lobby.onlineCta`,
  `lobby.onlineCtaHint`. **Pendiente de decisión**: `RoomService` (y el `/api/rooms` que no existe)
  sigue en `core/services/room.service.ts` sin usar — o se implementa `/rooms` o se borra.

### 3.2 · Completar el i18n — ✅ hecho
- **Qué**: literales sin traducir en plantillas y en el código (listados en `AUDITORIA_PROYECTO.md` §E2).
- **Cómo**: pasar todo a claves en `public/i18n/{es,en,fr}.json`; en las notificaciones del
  torneo, usar el `TranslatePipe`/`I18nService` en vez de literales en inglés.
- **Hecho cuando**: un script busca texto visible en inglés en los templates y no encuentra nada
  fuera de `translate`; los tres JSON tienen las mismas claves (test de paridad de claves).
- Esfuerzo: **3–4 h**.
- **Hecho** ✅ (12-10-2026). De 39 literales sueltos quedan **9 legítimos** (el logo partido
  «TRANS»/«CENDENCE», los puntos del campo de contraseña y los nombres propios GitHub/Discord).
  Traducidos también los títulos pixel (LOGIN/REGISTER/TOURNAMENTS/INSERT COIN), los enlaces de
  cambio de formulario, el separador «OR» y los `aria-label`. Las **12 notificaciones** del código
  (`'WELCOME BACK'`, `'Result reported'`, `'File Too Large'`…) pasaron a claves `notify.*` con
  `I18nService.t()` e interpolación `{{param}}`.
  **Claves que faltaban de verdad** (la UI mostraba la clave cruda): `notifications.title`,
  `notifications.noNotifications` y `profile.username` en los **tres** idiomas, y
  `tournament.maxPlayers` solo en `es`.
  Guardia automática: `npm run i18n:check` (`front/scripts/check-i18n.mjs`) comprueba paridad de
  claves, traducciones vacías, parámetros `{{…}}` coherentes y literales sueltos en las plantillas;
  **313 claves** en en/es/fr y enchufado al CI. Además, `i18n.spec.ts` repite la paridad dentro de
  los tests unitarios (7 tests).

### 3.3 · README para la evaluación
- **Qué**: faltan secciones que la hoja de evaluación exige: **project management approach**,
  **individual contributions of each member** y roles **PO / PM / Tech Lead**.
- **Cómo**: añadir esas secciones (reparto de roles, cómo se organizó el trabajo, quién hizo qué)
  y **actualizar la justificación del Major «Web game multijugador»**: ya no es «2-4 jugadores
  locales», es multijugador remoto real con póker autoritativo, cola de emparejamiento y bots.
- **Hecho cuando**: `grep -ci "project management" README.md` ≥ 1, hay una tabla de contribuciones
  individuales y la tabla de módulos refleja el estado real.
- Esfuerzo: **3–4 h**.

### 3.4 · Índice de documentación — ✅ hecho
- **Qué**: el README dice «Angular 21» y el `package.json` fija 20. El índice (`docs/INDEX.md`) ya
  enlaza los documentos nuevos ✅; falta repasar el resto del índice y `backend/README.md` (que
  lista la app de chat entre las apps del proyecto).
- **Hecho cuando**: el README dice la versión real y ningún documento lista apps que ya no existen.
- Esfuerzo: **1 h**.
- **Hecho** ✅ (12-10-2026). README «Angular 21» → **20**; `DEVELOPMENT.md` e `INDEX.md` decían
  «Angular 18» → **20** (y el árbol del índice decía `frontend/` cuando la carpeta es `front/`, con
  `modules/` cuando ahora es `features/` + `core/` + `i18n/`). `backend/README.md` **no listaba la
  app `poker`**: añadida al árbol y con su propia sección (motor en `engine/`, mesas y WebSockets,
  bots, mesas de torneo, historial y los cinco endpoints `/api/poker/*`).

### 3.5 · Higiene de git — ✅ hecho
- **Qué**: `front/test-results/` no está ignorado (los artefactos de Playwright se colarían en un
  commit), `front/playwright-report/` **ya está versionado** y el `.gitignore` raíz ignora
  `frontend/…`, una carpeta que no existe (la real es `front/`).
- **Cómo**: añadir `test-results/` y `playwright-report/` a `front/.gitignore`, quitar el informe
  del índice (`git rm -r --cached front/playwright-report`) y corregir las rutas del `.gitignore` raíz.
- **Hecho cuando**: `git status` queda limpio tras ejecutar los e2e y el informe no está en el repo.
- Esfuerzo: **30 min**.
- **Hecho** ✅ (12-10-2026, parcial) `.gitignore` corregido: las rutas `frontend/…` (carpeta que no
  existe) pasan a `front/…` y se añaden `front/test-results/`, `front/playwright-report/` y
  `front/.playwright/`. Ya no aparecen artefactos de tests en `git status`. **Ojo**: dos ficheros de
  esos directorios ya estaban versionados; dejar de seguirlos requiere
  `git rm -r --cached front/test-results front/playwright-report` (no se ha hecho: decisión del
  usuario).

### 3.6 · El `.env` de la raíz rompía el desarrollo local — ✅ hecho
- **Qué** (hallazgo nuevo, 12-10-2026): `python-decouple` busca el `.env` desde el directorio del
  `settings.py` **hacia arriba** y se queda con el primero que encuentra, así que al crear el `.env`
  de la raíz (el que usa `docker compose`, con `DJANGO_DEBUG=false`) el backend local arrancaba con
  `DEBUG=False` → `SECURE_SSL_REDIRECT=True` → **cualquier test HTTP fallaba con 301** y
  `manage.py runserver` redirigía todo a HTTPS.
- **Cómo**: un `backend/.env` (no versionado) con los valores de desarrollo local; decouple lo
  encuentra antes que el de la raíz. El contenedor no se ve afectado porque `os.environ` tiene
  prioridad sobre el fichero.
- **Hecho cuando**: `python manage.py test` pasa en local y `manage.py runserver` no redirige.
- **Hecho** ✅: creado `backend/.env` (con el porqué documentado dentro). Los 91 tests pasan en local.
- Esfuerzo: **30 min**.

### 3.7 · `compose.yaml` pasaba `DEBUG` y `settings.py` lee `DJANGO_DEBUG` — ✅ hecho
- **Qué** (hallazgo nuevo, 12-10-2026): el servicio `backend` definía `- DEBUG=${DJANGO_DEBUG:-false}`,
  pero `settings.py` hace `config("DJANGO_DEBUG", default=True)`. Esa variable **no se leía nunca**,
  así que el contenedor dependía del fichero `.env`; con el problema del 3.6 llegó a arrancar con
  `DEBUG=True` en un despliegue que se supone de producción.
- **Cómo**: pasar `DJANGO_DEBUG=${DJANGO_DEBUG:-false}` (y mantener `DEBUG` por compatibilidad).
- **Hecho cuando**: dentro del contenedor, `settings.DEBUG` es `False` aunque exista un `.env`.
- **Hecho** ✅: comprobado con `docker compose exec backend python -c "...settings.DEBUG"` →
  `DEBUG = False`, `SECURE_SSL_REDIRECT = True`.
- Esfuerzo: **15 min**.

---

## Bloque 4 — Producción y escalado · P1–P2

### 4.1 · Redis para el channel layer, la cola y las mesas — 🟡 mitad hecha
- **Qué**: `InMemoryChannelLayer` + cola y registro de mesas en memoria → con más de una réplica de
  Daphne dos jugadores pueden no verse.
- **Cómo**: `channels-redis`, `CHANNEL_LAYERS` por entorno, y mover la cola de matchmaking y el
  registro de mesas a Redis (claves con TTL) manteniendo la misma API interna.
- **Hecho cuando**: con `docker compose up --scale backend=2` dos navegadores se emparejan y juegan
  una mano completa.
- Esfuerzo: **6–8 h**.
- **Hecho** ✅ (12-10-2026) lo que toca al **channel layer y a la cola**:
  - `channels-redis==4.2.1` en `requirements.txt`; `CHANNEL_LAYERS` pasa a
    `RedisChannelLayer` en cuanto hay `REDIS_URL` (y sigue en memoria si no, para dev y tests).
  - La cola de emparejamiento es ahora `apps/poker/queue.py`, con dos backends detrás de la misma
    interfaz asíncrona: `InMemoryMatchQueue` (una instancia) y `RedisMatchQueue` (hash + zset, con
    caducidad por tiempo). El consumer ya no guarda la cola en un atributo de clase.
  - Servicio `redis` (7-alpine) en `compose.yaml` con healthcheck y volumen; el backend depende de
    él y recibe `REDIS_URL`/`MATCH_QUEUE_BACKEND=redis`.
  - Tests: `apps/poker/tests/test_queue.py` (14) — los dos backends, la fábrica por entorno y un
    **test de integración contra un Redis de verdad** (`REDIS_TEST_URL`), ejecutado dentro del
    contenedor contra `redis://redis:6379/0`: **verde**.
  - **Pendiente (la otra mitad)**: el **registro de mesas** sigue siendo del proceso que creó la
    mesa (`TableRegistry` en `tables.py`). El diseño para cerrarlo: la mesa se une a un grupo
    `poker_table_<id>` con su propio canal (`new_channel()` + tarea que escucha) y el
    `TableConsumer` que caiga en otra réplica le **reenvía la acción** por ese grupo en vez de
    tocar la mesa en local; las vistas ya viajan por el channel layer, así que la difusión
    funcionaría tal cual. Ojo con un detalle de infraestructura: con `--scale backend=2`, nginx
    resuelve `backend` una sola vez al arrancar, así que **hace falta un `resolver` + variable en
    el `proxy_pass`** para que reparta de verdad entre réplicas; sin eso el test no probaría nada.

### 4.2 · PostgreSQL en el despliegue — ✅ hecho
- **Qué**: el stack usa SQLite; con escritura concurrente y varias réplicas es frágil.
- **Cómo**: servicio `postgres` en compose, `DB_ENGINE=django.db.backends.postgresql`, migrar y
  añadir el volumen de datos.
- **Hecho cuando**: `docker compose up` levanta con Postgres, las migraciones corren solas y el
  póker + torneos siguen funcionando.
- Esfuerzo: **3–4 h**.
- **Hecho** ✅ (12-10-2026): servicio `postgres:16-alpine` con volumen propio y healthcheck
  (`pg_isready`); `psycopg[binary]` en `requirements.txt`; `settings.py` añade usuario, contraseña,
  host, puerto y `CONN_MAX_AGE` **solo** cuando el motor es PostgreSQL (SQLite sigue igual, sin esas
  claves). El backend espera a que Postgres esté sano antes de arrancar y las migraciones corren
  solas en el `command`.
  **Verificado de verdad**: con `DB_ENGINE=django.db.backends.postgresql DB_NAME=transcendence`
  (y un volumen nuevo, porque el anterior se había inicializado con el nombre del `.env`) el
  contenedor levanta, migra y responde con `ENGINE: django.db.backends.postgresql`.
  **Decisión**: el `.env` del usuario se queda en SQLite a propósito, para no vaciarle la demo (47
  usuarios y los torneos están ahí); `.env.example` explica las dos líneas que hay que cambiar
  (`DB_ENGINE` y `DB_NAME`, que además es el nombre de la base que crea el servicio `postgres`).

### 4.3 · Compose de producción — ✅ hecho
- **Qué**: hoy monta `./backend:/app` (código del host) y usa `runserver`.
- **Cómo**: quitar el bind mount, servir con `gunicorn`+`daphne` (o `uvicorn`) y `collectstatic`;
  separar `compose.yaml` (dev) y `compose.prod.yaml`.
- **Hecho cuando**: la imagen del backend no contiene el código montado y arranca sin `runserver`.
- Esfuerzo: **3–4 h**.
- **Hecho** ✅ (12-10-2026): `compose.prod.yaml` como overlay
  (`docker compose -f compose.yaml -f compose.prod.yaml up -d`). Usa `!override` en `volumes`, que
  es lo que permite **quitar** el bind mount `./backend:/app` sin duplicar el fichero de desarrollo
  (se queda solo `./juego:/juego:ro` y `vault_creds`), arranca con **Daphne** (ASGI: HTTP y
  WebSockets, ya estaba en `requirements.txt`) en vez de `runserver`, hace `collectstatic` y fuerza
  `DJANGO_DEBUG=false`. Se eligió Daphne en solas en vez de gunicorn+uvicorn porque es el servidor
  ASGI de referencia de Channels y ya venía instalado: añadir gunicorn solo aporta gestión de
  workers, que en este despliegue no hace falta.
  Comprobado con `docker compose config`: el backend resultante no tiene el bind mount del código y
  su `command` es `migrate && collectstatic && daphne`.

### 4.4 · Observabilidad mínima — ✅ hecho
- **Qué**: no hay logs estructurados, métricas ni captura de errores.
- **Cómo**: logging JSON a stdout, un endpoint `/api/health/` que ya existe (añadir comprobación de
  DB/Redis) y, opcional, Sentry.
- **Hecho cuando**: los logs del contenedor son JSON con nivel y request id, y el healthcheck
  distingue DB caída.
- Esfuerzo: **3–4 h**.
- **Hecho** ✅ (12-10-2026): `config/observability.py` con (1) `JsonFormatter` — una línea de JSON
  por registro con `time`, `level`, `logger`, `message`, `request_id` y los `extra=` que se pasen —
  y (2) `RequestIdMiddleware`, que toma el id de `X-Request-ID` (o lo genera), lo deja en un
  `ContextVar` para que **todos** los logs de la petición lo lleven y lo devuelve en la respuesta.
  `LOGGING` se construye desde ahí (Django, Channels y `apps` a stdout; `apps` en DEBUG si
  `DJANGO_DEBUG`).
  `/api/health/` ya no responde `{"status":"healthy"}` a ciegas: hace `SELECT 1` a la base de datos
  y un PING al channel layer de Redis, devuelve `checks: {db, redis}` y **503 con `degraded`** si
  alguno falla (Redis sin configurar no cuenta como fallo).
  Tests: `backend/tests/test_observability.py` (**11**, incluido el 503 cuando la BD falla).
  Pendiente opcional: Sentry, que el roadmap deja como «opcional» y no se ha añadido para no
  meter una dependencia externa en una demo.

---

## Bloque 5 — El juego como producto · P2

### 5.1 · Los torneos se juegan en mesas de póker reales — ✅ hecho
- **Qué**: el botón «Jugar» del bracket lleva al modo local (WASM) con `?tournament=…&match=…`.
- **Cómo**: al pulsar «Jugar», crear una mesa con los dos jugadores del match y navegar a
  `/poker/table/<id>`; al terminar, el servidor cierra el match (engancha con 0.2).
- **Hecho cuando**: un torneo de 4 jugadores se completa jugando las partidas de verdad, sin
  reportar resultados a mano.
- Esfuerzo: **6–8 h**.
- **Hecho** ✅ (12-10-2026) El match se juega en una **mesa real del motor de póker**:
  `apps/poker/tournament_tables.py` crea la mesa con los dos jugadores del bracket
  (`context={'tournament_id', 'match_id'}`, ciegas 5/10, 1000 fichas) y el endpoint
  `POST /api/tournament/<id>/matches/<mid>/table/` la devuelve (solo a los dos participantes,
  idempotente: los dos acaban en la misma mesa). El botón «Jugar» del bracket navega ahora a
  `/poker?tournament=…&match=…` y esa página entra directo a la mesa, sin cola ni bots.
  La mano **no se reparte hasta que están los dos** sentados, y al terminar la partida el
  **servidor** cierra el match (`_close_tournament_match` en `apps/poker/services.py`): mapea el
  ganador por **usuario** (no por asiento), escribe marcadores, elimina al perdedor y el bracket
  avanza solo. Con esto el hallazgo **A2 queda cerrado por la vía fuerte**: ya no hace falta que
  nadie confirme el resultado (la doble confirmación del 0.2 sigue disponible como red de
  seguridad para los matches que se reporten a mano).
- **Verificado**: `apps/poker/tests/test_tournament_tables.py` (10 tests: mesa compartida,
  no reparte sin los dos, 403 a un desconocido, 409 si el match está cerrado, 400 en un pase
  directo, cierre por el servidor con el ganador correcto por usuario y avance del bracket) y
  `scripts/audit/probe_tournament_table.py` contra el stack desplegado → **18/18** (torneo de 4,
  bracket, misma mesa para los dos, mano repartida solo al estar ambos, cartas privadas, sin bots,
  acción aplicada y acción fuera de turno rechazada). e2e: `front/e2e/poker.spec.ts` (2) y la
  navegación desde el bracket en `tournaments.spec.ts`.
- **Pendiente**: si un jugador no aparece, la mesa espera (no hay límite de espera por
  inasistencia); el creador puede cerrar el match a mano. Se puede añadir un tiempo máximo de
  espera en una iteración siguiente.

### 5.2 · Mesas de 3–6 jugadores en la UI — ✅ hecho
- **Qué**: el motor ya soporta 2–6 asientos y los tests lo cubren; la cola solo hace heads-up.
- **Cómo**: cola con «mesa de 6» (empareja por antigüedad, rellena con bots), y en la UI disponer
  los asientos alrededor del tapete.
- **Hecho** ✅ (12-10-2026) La cola empareja por **(nivel de apuesta, tamaño de mesa)** y el
  tamaño se fija en la URL (`/ws/poker/matchmaking?token=…&size=N`), antes de entrar en la cola:
  si se cambiara después, dos clientes que quieren mesa de 6 podrían emparejarse de dos. Hacen
  falta `size - 1` compañeros; los huecos que falten se cubren con bots al agotarse el tiempo de
  espera (`BOT_NAMES` ampliado a 5 para llenar mesas grandes). En la UI hay un selector 2–6 y la
  mesa pinta todos los asientos (mis cartas abajo, los demás en fila).
- **De paso, dos fallos reales encontrados al escribir los tests**:
  1. `_join_queue`/`_bot_fallback` usaban `self.channel` en vez de `self.channel_name` (habría
     roto el emparejamiento múltiple en producción).
  2. **La mesa no copiaba los stacks del motor a sus asientos al acabar la mano**: nadie llegaba
     nunca a 0 fichas (la partida no terminaba) y cada mano volvía a repartir el stack inicial, así
     que el hook de fin de partida **no se disparaba nunca** y no se registraba resultado ni ELO en
     las partidas online. Arreglado con `PokerTable._sync_stacks()`.
- **Regla de ELO**: el ELO del proyecto es 1v1, así que una mesa de 3+ humanos se guarda en el
  historial pero **no puntúa** (`rated=False`).
- **Verificado**: `apps/poker/tests/test_multi_seat.py` (7 tests: los tres en la misma mesa, los
  tamaños no se mezclan, relleno con bots, mano de 6 completa con conservación de fichas, la
  partida termina al arruinarse alguien con el hook disparado, y una mesa de 3 no mueve el ELO) y
  `scripts/audit/probe_multi_seat.py` contra el stack → **11/11**; UI real con
  `scripts/audit/probe_poker_ui_6.js` → **8/8** (mesa de 6 desde el navegador, 5 bots).
- **Hecho cuando**: 3 navegadores + bots juegan una mano de 6 con botes laterales correctos.
- Esfuerzo: **8–12 h**.

### 5.3 · Historial de manos y estadísticas del póker — ✅ hecho
- **Qué**: hoy solo se guarda una fila `Game` por partida; no hay historial de manos.
- **Cómo**: modelos `PokerTable`/`PokerHandRecord` en `apps/poker` (la app aún no tiene `models.py`),
  guardando el resumen que ya genera el motor (`result`), y una pestaña de historial en el perfil.
- **Hecho cuando**: el perfil lista las últimas manos con tablero, ganador y bote.
- Esfuerzo: **6–8 h**.
- **Hecho** ✅ (12-10-2026) Modelos nuevos en `apps/poker/models.py`: `PokerHandRecord` (partida,
  mesa, nº de mano, tablero, bote, showdown, ganadores) y `PokerHandPlayer` (asiento, usuario o
  bot, cartas, nombre de la jugada, stack final, ganado y si se retiró). El motor ya calculaba ese
  resumen (`Hand.result`), así que la mesa solo lo copia en `PokerTable._hand_summary()` y se
  persiste al terminar la partida en `services._save_hands()` (dentro del mismo camino que ya
  escribía el `Game`, sin meter base de datos en el motor).
- **API**: `GET /api/poker/history/` (mis últimas 20 partidas con rival, resultado, fichas y nº de
  manos), `GET /api/poker/history/<game_id>/` (las manos de una partida; **403** si no es tuya) y
  `GET /api/poker/stats/` (manos jugadas/ganadas, showdowns, bote mayor, retiradas y % de victoria).
- **Web**: página `/poker/history` con las estadísticas, la lista de partidas y, al abrir una, sus
  manos con tablero, bote, ganador y jugadores (cartas solo si hubo showdown). Enlazada desde el
  lobby del póker. Claves i18n en es/en/fr.
- **Verificado**: `apps/poker/tests/test_history.py` (**10 tests**: se guardan las manos con bote y
  ganadores, las cartas solo salen con showdown, partidas humano-humano, los tres endpoints, 403 en
  partida ajena, sin sesión y sin filtrar emails) → suite completa **118 OK**; contra el stack
  desplegado, historial real generado con el motor (`seed_poker_history.py`) y los tres endpoints
  comprobados con `curl`, más `scripts/audit/probe_poker_history_ui.js` en navegador real → **8/8**
  (estadísticas, lista de partidas y manos con bote/ganador/jugadores).

### 5.4 · Espectadores y chat de mesa — ✅ hecho
- **Qué**: el consumer ya distingue asiento y vista; un espectador es `you=null`.
- **Cómo**: permitir conexión sin asiento (solo lectura), y chat de mesa sobre el mismo WebSocket.
- **Hecho cuando**: un tercer navegador ve la partida en vivo sin poder actuar ni ver cartas
  privadas hasta el showdown.
- Esfuerzo: **6–8 h** (más si el chat se arregla en el Bloque 1).
- **Depende de**: 1.1 (resuelto: el chat se quedó y ya tiene UI).
- **Hecho** ✅ (12-10-2026) **Espectadores**: `/ws/poker/table/<id>` acepta conexiones **sin
  asiento** (antes cerraba con 4404). El espectador recibe siempre la vista sin asiento
  (`you=None`), así que no ve ninguna carta ajena hasta el showdown, y cualquier acción se
  rechaza («no estás sentado en esta mesa»). La mesa difunde esa vista por el grupo
  `poker_spectators_<id>`, derivado del id: sin estado extra.
- **Chat de mesa**: mensajes efímeros por el mismo WebSocket (`{"type":"chat","text":…}`),
  **sin base de datos**. Los ven jugadores y espectadores; se recorta a 200 caracteres y hay
  anti-spam por conexión (0,5 s). El mensaje va marcado con quién escribe y si es espectador.
- **Web**: el lobby lista las **mesas en vivo** (`GET /api/poker/tables/`) con un botón «Ver» que
  lleva a `/poker?table=<id>` (URL compartible); en modo espectador sale la insignia ESPECTADOR,
  no hay botones de acción y aparece el panel de chat de mesa.
- **Verificado**: `apps/poker/tests/test_spectators.py` (**13 tests**: la vista de espectador no
  filtra cartas, en showdown sí revela, un no-sentado no puede actuar, la mesa manda la vista al
  grupo de espectadores, chat normal/espectador/vacío/recortado/anti-spam y el listado de mesas
  vivas con las terminadas al final) → suite completa **131 OK**; `scripts/audit/probe_spectators.py`
  contra el stack → **12/12** (tercer cliente mirando la mesa: sin asiento, sin cartas, acción
  rechazada, chat en ambos sentidos y cartas reveladas al llegar el showdown); e2e
  `front/e2e/spectators.spec.ts` (2 tests: la lista de mesas en vivo y que «Ver» entra en modo
  espectador). Suite e2e completa: **33/33**.
- **Bug de UI que destapó el e2e (y ya está arreglado)**: al pulsar «Ver» se navega a la **misma
  ruta** con `?table=…`, y Angular **reutiliza** el componente, así que el constructor no volvía a
  correr y el modo espectador no se activaba nunca. Ahora la página escucha
  `route.queryParamMap` en vez de leer solo el snapshot inicial.
- **Nota sobre el e2e**: el WebSocket de la mesa **no** se puede simular en este entorno
  (`page.routeWebSocket` no intercepta: se comprobó que el handler no llegaba a ejecutarse), así que
  el e2e cubre la parte REST y de navegación y el modo espectador de verdad lo verifica el sondeo
  contra el servidor real.

### 5.5 · Customización del juego online
- **Qué**: el módulo Minor «game customization» hoy solo aplica al modo local (nº de jugadores,
  objetivo, rondas, tema). En el póker online ya se pueden elegir ciegas: falta el resto.
- **Cómo**: temas del tapete (la paleta ya existe en el front) y límites de stack configurables.
- **Hecho cuando**: se puede cambiar el tema de la mesa desde la UI y queda guardado.
- Esfuerzo: **4–6 h**.

---

## Bloque 6 — Modo local C/WASM · P3

### 6.1 · Persistir los highscores — ✅ hecho
- **Qué**: `highscores.dat` vive en el sistema de ficheros en memoria de Emscripten y se pierde al
  recargar.
- **Cómo** (elegir): montar `IDBFS` para que persista en el navegador, **o** enviar la puntuación
  al backend (`/api/games/…`) y pintarla desde ahí.
- **Hecho cuando**: se juega una partida, se recarga la página y la tabla sigue ahí.
- Esfuerzo: **3–4 h**.
- **Hecho** ✅ (12-10-2026) con **IDBFS**, que es lo autocontenido:
  1. `src/game.c`: los highscores pasan de la ruta relativa `highscores.dat` (que caía en `/` del
     sistema de ficheros en memoria) a `HIGHSCORES_PATH`, que es `"/persist/highscores.dat"` en web
     y `"highscores.dat"` en escritorio (`#ifdef PLATFORM_WEB`, para no romper el build de
     escritorio, que no tiene `/persist`).
  2. `SaveHighScores()` pide el volcado con `EM_ASM` → `FS.syncfs(false, …)`: **IDBFS no escribe en
     IndexedDB por su cuenta**, hay que pedírselo después de escribir.
  3. `minshell.html`: `preRun` que hace `FS.mkdir('/persist')`, `FS.mount(IDBFS, {}, '/persist')` y
     `FS.syncfs(true, …)` para traer lo guardado. No hizo falta exportar ninguna función de recarga
     porque la tabla se lee en la **pantalla final** (segundos después de arrancar), no al inicio.
  4. `Makefile`: `-lidbfs.js` en el enlazado; `make web` reconstruido con emcc 5.0.6.
  **Verificado con un sondeo nuevo** (`scripts/audit/probe_wasm_persistencia.js`, Edge headless +
  CDP): monta `/persist`, escribe un fichero, `syncfs`, **recarga la página** y comprueba que el
  contenido sigue ahí → **7/7**, y el juego arranca igual (canvas 1280×720, WebGL, 0 excepciones).
  **Queda como comprobación manual** el «jugar una partida entera y recargar»: la tabla se escribe
  al terminar la partida y automatizar una partida completa del juego de cartas no es viable hoy.
  Lo que sí está verificado es el mecanismo exacto que usa ese guardado.

### 6.2 · Limpiar el código muerto — ✅ hecho
- **Qué**: `game.h` declara tres funciones inexistentes; `game_api.c` no se usa; hay funciones de
  animación sin uso.
- **Hecho cuando**: `grep` de los símbolos no encuentra declaraciones huérfanas y el juego compila
  y arranca igual (WASM reconstruido y probado en navegador).
- Esfuerzo: **1–2 h**.
- **Hecho** ✅ (12-10-2026). Fuera:
  - las tres declaraciones huérfanas de `game.h` (`DealCardsToPlayer`, `SelectCardForPlayer`,
    `DeselectCardForPlayer`: no existía su definición en ningún sitio);
  - `src/game_api.c` y `src/game_api.h` (`GamePause`/`GameIsPaused`/`GameRestart`/`GameSetVolume`,
    definidas y sin usar; entraban en la compilación por el `wildcard` del Makefile);
  - `IsDealAnimationComplete()` (definida en `game.c` y declarada en `game.h`, nunca llamada).
  Los ocho símbolos dan **0 referencias** en `src/` y el **WASM se reconstruyó** con `make web`
  (emcc 5.0.6, `juego/web/index.{html,js,wasm,data}` regenerados).
  **Verificado en navegador de verdad**: `scripts/audit/probe_wasm.js` contra el stack →
  canvas 1280×720, WebGL activo, `glGetError: 0`, raylib 6.0 arranca entero (shaders, texturas,
  fuente, bucle a 16,67 ms/frame) y **0 excepciones** en consola.
  De paso: el probe no aceptaba el certificado autofirmado y se quedaba en el aviso del navegador
  («sin canvas»); añadido `--ignore-certificate-errors` para que sirva contra `https://localhost:8443`.

---

## Cartas con el arte del juego (14-10-2026)

El póker pintaba las cartas como texto (`A♠`, `7♣`) mientras el proyecto tenía un mazo
entero en PNG sin usar en la web. Ahora las cartas son **el arte del propio juego**:

- **Mazo servido por la web**: los PNG de `juego/assets/cards/BASIC/8BitDeckN.png` pasan a
  `front/public/cards/<carta>.png` (52 + dorso, 104 KB en total) al doble de su tamaño
  nativo (146×194) y con `NEAREST`, para que el pixel art siga siendo pixel art. El
  service worker de la PWA ya cachea las imágenes, así que quedan también sin conexión.
- **Componente `app-playing-card`**: recibe el código del motor (`"As"`, `"7c"`, `"Td"`),
  pinta el PNG con `image-rendering: pixelated`, y compone el nombre accesible traducido
  («as de picas»). Un código inválido cae al dorso en vez de pedir un fichero que no existe.
- **El acabado** (que era la petición): las cartas entran repartidas una tras otra (70 ms de
  retardo acumulado), se levantan y giran un poco al pasar por encima, se hunden al pulsarlas,
  brillan en cian cuando le toca hablar a ese jugador y en dorado con un latido cuando ganan;
  las de quien se retira quedan de lado y en gris. Todo con `prefers-reduced-motion` respetado.
- Se usa en la mesa, en el historial y en el replay (donde el reparto se ve aparecer carta a
  carta, que es justo lo que hace agradable seguir una mano).

**Hallazgo**: el mapeo del código del juego C daba por hecho que el mazo va corazones,
diamantes, tréboles, picas. **No es así**: leyendo los símbolos de cada grupo de 13, el orden
real es corazones, **tréboles**, diamantes, picas. Como el juego sí escribe el nombre del palo
en pantalla («Diamantes»), enseñaba un trébol llamado diamante y al revés. Corregido en
`card_textures.c` con una tabla de grupos; recompilado el WASM y verificado que arranca igual
(canvas 1280×720, WebGL, `glGetError: 0`, sin excepciones).

## Juego nuevo: el Culo / Presidente (14-10-2026)

El primer juego que entra por el apartado «Juegos», con las normas que dio el usuario.

- **Motor de reglas puro** (`core/games/culo/culo-engine.ts`): recibe estado y devuelve
  estado, sin tocar nada por dentro. Una jugada son una o varias cartas del mismo valor;
  para responder hay que poner **exactamente la misma cantidad** y de **valor superior**,
  o pasar (pasar es una decisión, no una obligación). La baza se cierra cuando todos los
  demás pasan y la abre el último que jugó.
- **Valores**: 2, 3, 4, 5, 6, 7, Sota, Caballo, Rey, As… y **el 5 de oros por encima de
  todo**. Ese 5 es además una carta aparte: no se puede jugar junto a otros cincos porque
  no comparte valor.
- **Roles y fin de ronda**: primero Presidente, segundo Vicepresidente, penúltimo
  Viceculo, último Culo. Con 3 jugadores no hay vices (el segundo sería a la vez
  vicepresidente y viceculo): quedan Presidente, un neutro y Culo. Se decide así y **se
  dice en el propio panel de reglas**.
- **Intercambio entre rondas**: el Culo da sus 2 mejores al Presidente, que devuelve sus
  2 peores; el Viceculo da su mejor al Vicepresidente, que devuelve su peor.
- **Baraja española dibujada para la web**: 40 cartas en pixel art con
  `scripts/generar_baraja_espanola.py`, mismo tamaño que el mazo del póker (73×97 nativo,
  ×2 al guardar) y con el 5 de oros marcado con marco dorado y estrella, porque es la
  carta más alta y conviene que se vea de un vistazo.
- **Mesa jugable contra bots** (3 a 6 jugadores, 1 o 2 barajas), con los sonidos que ya
  traía el proyecto (repartir, soltar carta, pasar, fin de ronda), y un **panel de «cómo
  se juega»** con el objetivo, el desarrollo de una ronda, los valores, los roles, el
  intercambio y cuatro ideas de estrategia, en los tres idiomas.
- **Pruebas**: 25 del motor —incluida una partida entera con bots que comprueba que
  siempre termina y que no se pierde ni se inventa una carta—, 3 e2e (se explica antes de
  jugar, se juega un turno contra los bots y la mesa pasa la auditoría de accesibilidad) y
  las capturas de revisión.

## Apartado «Juegos» (14-10-2026)

La plataforma tenía los juegos sueltos en el menú (Póker, Jugar) y ninguna forma de
añadir otro sin tocar el menú, las rutas y la portada. Ahora hay un apartado **Juegos**
(`/games`) que reúne todo lo jugable, y —esto es lo importante— **el catálogo manda**:

- `front/src/app/core/games/game-catalog.ts` es **el único sitio donde se declara un
  juego** (id, ruta, modo, jugadores, icono, etiquetas y si ya se puede jugar). El
  apartado solo pinta lo que hay ahí, así que un juego nuevo aparece sin tocarlo.
- Cada tarjeta dice **cómo se juega** (en local / contra bots / online) y cuántos juegan,
  y lleva a su pantalla. Un juego marcado como no disponible se ve apagado y sin botón:
  mejor anunciarlo así que enseñar una pantalla a medias.
- El menú pasa a **Inicio · Juegos · Torneos · Chat · Perfil**: los juegos viven bajo
  «Juegos» (el póker y el arcade siguen accesibles desde la portada y con su ruta directa).
- Guía escrita en **[docs/JUEGOS.md](JUEGOS.md)**: declarar la entrada, la ruta, los textos
  y, si el juego es online, dónde engancha en el servidor (sala genérica `ws/rooms/<id>`,
  emparejamiento `ws/matchmaking`, cola con memoria/Redis, torneos y el patrón de servidor
  autoritativo del póker).
- Tests: el catálogo comprueba que **cada ruta declarada existe de verdad** en
  `app.routes.ts` (un juego mal declarado no pasa), más 4 e2e del apartado y su auditoría
  de accesibilidad.

## Bloque 7 — Extras que suben nota · P3

- **7.1 Logros/insignias** (primera mano ganada, escalera de color, 3 manos seguidas) — ✅ hecho
  (13-10-2026):
  - **Backend**: `apps/poker/achievements.py` calcula los logros sobre el historial que ya se guarda
    (`PokerHandPlayer`), **sin modelo nuevo**: ganar una mano, completar una escalera de color y
    ganar tres seguidas (con el progreso de la racha). Endpoint `GET /api/poker/achievements/`
    (solo para el jugador). **11 tests** (cálculo, racha cortada por una derrota, manos de otro
    jugador que no cuentan, 401 sin sesión y el progreso en la respuesta).
  - **Front**: tarjeta «Logros» en `/poker/history` — icono, nombre, progreso `2/3` y apagada
    mientras está bloqueada. Claves i18n en es/en/fr (319 en total). e2e propio.
  - **Verificado**: 192 tests de backend, 34 e2e, y contra el stack un usuario recién creado
    recibe los tres logros bloqueados (`{"unlocked":0,"total":3}`).
  - **Fallo gordo encontrado de paso**: el `package-lock.json` del front había quedado
    **desincronizado** con `package.json` desde que se instaló ESLint, y el `npm ci` de la imagen
    **fallaba**: el contenedor del front no se podía reconstruir desde entonces y seguía sirviendo
    un build viejo (por eso el e2e nuevo falló la primera vez). Se regeneró el lock con el **mismo
    npm que usa la imagen** (`node:20-alpine`, npm 10) porque el de la máquina (npm 11) resuelve
    distinto. Lección: si se añaden dependencias al front, comprobar que `docker compose build
    frontend` sigue funcionando — el build local no lo detecta.
- **7.2 Replays de manos** — ✅ hecho (13-10-2026). Reproduce una mano paso a paso en la UI:
  - El motor ya emitía el registro de acciones (`hand_start`, `blind`, `action`, `street`,
    `uncalled_return`, `hand_end`), pero **no se guardaba**: el resumen que iba a la base de
    datos lo tiraba. Ahora `PokerHandRecord.actions` (JSON) lo conserva (migración
    `0003_pokerhandrecord_actions`), y las manos antiguas se quedan con la lista vacía.
  - Endpoint propio: `GET /api/poker/history/hand/<id>/` con el registro. Va aparte de la lista
    de manos a propósito: el registro pesa y solo hace falta al abrir una. **Solo devuelve
    manos que jugó quien pregunta** (si no, 403).
  - Componente `hand-replay`: no guarda estado del juego, **reconstruye** tablero, bote,
    retirados y a quién le tocaba actuar recorriendo el registro hasta el paso actual. Controles
    ⏮ ◀ ▶/⏸ ▶ ⏭ y reproducción automática. Todo lo que se ve sale de ahí, así que un replay no
    puede «inventarse» una partida distinta a la que pasó.
  - Botón **«Ver mano»** en cada mano del historial; el registro se pide al pulsarlo.
  - 25 claves nuevas de i18n en los tres idiomas (344 en total), 10 tests unitarios del
    componente, 7 de backend y un e2e que avanza el replay y comprueba bote, tablero y jugadas.
- **7.3 Accesibilidad** (auditoría con axe, foco visible, roles ARIA, contraste del tema neón) —
  ✅ hecho (13-10-2026):
  - Auditoría con **axe** en las seis pantallas principales: `front/e2e/a11y.spec.ts` con
    `@axe-core/playwright` (etiquetas `wcag2a`/`wcag2aa`). Falla solo por lo **grave o crítico** y
    **imprime todo** lo que encuentra, para poder ir mejorándolo sin que el test sea una lista de
    deseos.
  - Lo que salió y se arregló:
    - **`button-name` [crítico]**, en las seis pantallas: el botón de avisos de la cabecera solo
      tenía un SVG, sin nombre accesible → `aria-label` traducido (la clave `common.notifications`
      ya existía).
    - **`color-contrast` [serio]**: el gris atenuado de la paleta (`--color-text-muted`) estaba en
      `#505070`, que da **2,1:1** sobre el fondo de tarjeta (AA pide 4,5:1) → pasa a `#8888aa`
      (**4,8:1** sobre `#1e1e30`, 5,7:1 sobre `#0c0c14`).
    - El mismo problema por otra vía en los logros **bloqueados** (perfil, y mi tarjeta nueva del
      póker): atenuar el bloque entero con `opacity` dejaba el texto en **2,35:1** → ahora se
      atenúa el icono (gris) y el texto usa el gris que ya cumple.
  - Resultado: **6/6 pantallas sin violaciones** (antes, 6/6 con violaciones y 8–14 nodos cada una).
  - `@axe-core/playwright` es la única dependencia nueva; tras instalarla se regeneró el lock con el
    npm de la imagen (la lección del 7.1) y se comprobó que `docker compose build frontend` sigue en
    verde.
  - Nota: quedan fuera de esta pasada Lighthouse (rendimiento/PWA, que va con el 7.4) y una
    revisión manual del **foco visible** en la mesa de póker, que se ve mejor jugando que en un
    informe automático.
- **7.4 PWA** (instalable, offline para el modo local) — ✅ hecho (13-10-2026):
  - `@angular/service-worker` **de la misma versión que `@angular/core`** (20.3.24): el esquema
    `ng add @angular/pwa` falla si pides la última, porque el service worker pide exactamente la
    misma versión que la core instalada.
  - Manifiesto propio (`public/manifest.webmanifest`): nombre, colores del tema, idioma `es` y
    **ocho iconos generados desde el logo del proyecto** (`icon/logo.png`) con margen, para que
    valgan también como *maskable* (Android los recorta en círculo).
  - `ngsw-config.json`: tres grupos de assets (app, **idiomas** e imágenes) y dos grupos de datos:
    **juego-local** (`/game-embed/**`, los ~15 MB del C/WASM: se cachean al usarlo por primera vez,
    no en la instalación) y **api** (red primero, con respaldo en caché).
  - En nginx, dos cosas que había que hacer bien o la app se queda clavada: el service worker y su
    manifiesto de caché se sirven con `Cache-Control: no-cache` (la regla general de `.js` los
    congelaba un año y la app no se habría actualizado nunca), y el `.webmanifest` se sirve como
    `application/manifest+json` (el `mime.types` de nginx no trae esa extensión).
  - El service worker se registra **solo en producción** (`!isDevMode()`): en desarrollo, un worker
    sirviendo código viejo complica el día a día.
  - Verificación real con `scripts/audit/probe_pwa.js` (Edge headless + CDP): **8/8** —
    se registra, tras recargar controla la página, aparecen las cinco cachés (`app`, `idiomas`,
    `assets`, `juego-local`, `api`), el manifiesto se descarga con su nombre, sus 8 iconos y en
    español.
  - Fuera de alcance por ahora: probar la instalación desde la barra del navegador (es manual) y
    Lighthouse, que se puede pasar sobre el stack levantado.
  - **Hallazgo al activar la PWA**: los e2e empezaron a fallar (login simulado que no redirige,
    esperas agotadas). La causa no era el código nuevo sino que los tests corren contra **lo que
    haya en el puerto 4200** — y ahí estaba el **contenedor** con el build de producción, ya con
    service worker: el worker sirve respuestas de su caché y **se salta los mocks de Playwright**.
    Arreglado con `serviceWorkers: 'block'` en `playwright.config.ts` (la PWA se verifica aparte,
    con el sondeo, que sí necesita el worker de verdad). De paso: los e2e pasaron de 2,4 min a 23 s,
    porque el worker también ralentizaba cada carga.
  - Nota para quien lo corra: como el puerto 4200 lo ocupa el contenedor, los e2e de local prueban
    el **build de producción servido por nginx** (si el contenedor está parado, Playwright levanta
    un servidor de desarrollo en su lugar). Conviene reconstruir el contenedor antes de fiarse de
    un resultado verde.
- **7.5 i18n de la API** (mensajes de error traducidos por cabecera `Accept-Language`) — ✅ hecho
  (13-10-2026):
  - `LocaleMiddleware` en el `MIDDLEWARE` y `LANGUAGES` = en/es/fr (los mismos que el front). Es el
    que elige idioma a partir de `Accept-Language`. `/api/health/` devuelve `lang`, así que se
    puede comprobar de un vistazo.
  - Los **27 literales** de error de la API (6 ficheros: `chat`, `public_api`, `users`) envueltos en
    `gettext_lazy`, que son **15 mensajes únicos** (los demás eran repetidos). Catálogos `.po` de
    es/en/fr en `backend/locale/` (`LOCALE_PATHS` en settings).
  - `gettext` (para `msgfmt`) añadido al `Dockerfile.backend` y `manage.py compilemessages` en el
    arranque del contenedor (dev y producción) y como paso del CI. Los `.mo` son artefactos y van
    al `.gitignore`; los `.po` sí se versionan.
  - **Verificado contra el stack**, no solo en tests: `POST /api/auth/login/` con credenciales malas
    devuelve `{"error":"Credenciales incorrectas"}` con `Accept-Language: es`,
    `{"error":"Invalid credentials"}` con `en` y `{"error":"Identifiants incorrects"}` con `fr`; el
    registro duplicado da «Ce nom d'utilisateur existe déjà» en francés. **8 tests** en
    `backend/tests/test_api_i18n.py`.
  - Nota para quien trabaje sin contenedor: hace falta `gettext` instalado y
    `manage.py compilemessages` (el contenedor ya lo hace solo).

## Bloque 8 — Juegos nuevos a integrar · P2 (decidido 14-10-2026)

Cuatro juegos de baraja española elegidos tras la investigación de
**[docs/INVESTIGACION_JUEGOS.md](INVESTIGACION_JUEGOS.md)**: **Mentiroso, Tute, Brisca y Mus**.
Las reglas están ya escritas y listas para programar en **[docs/REGLAS_JUEGOS.md](REGLAS_JUEGOS.md)**
(reglamento, variante elegida, estado del motor, acciones, casos límite y bot de cada uno), así que
empezar un juego es abrir ese documento y seguir.

**Orden de trabajo y por qué:**

| # | Juego | Jugadores | Motor | Esfuerzo | Por qué ahí |
|---|---|---|---|---|---|
| 8.1 | **Mentiroso** | 3–6 | Muy simple | 6–8 h | El motor más pequeño de los cuatro: no hay bazas ni combinaciones, y el farol ya lo resuelve el servidor (sabe las cartas reales). El más rápido de ver online. |
| 8.2 | **Brisca** | 2 (y 4) | Medio | 10–14 h | El juego de bazas más popular y el más fácil de ellos: sin obligación de asistir y sin cantos. |
| 8.3 | **Tute** | 4 (y 2) | Medio-alto | 14–18 h | Mismo motor de bazas que la brisca, más obligaciones (asistir/montar/fallar), baceta, acuses y las diez últimas. |
| 8.4 | **Mus** | 4 (parejas) | Alto | 25–35 h | Cuatro lances con apuestas, jerarquía de pares, orden del tanteo, parejas y las señas. El más vistoso y el más caro. |

**Lo que se escribe una vez y sirve para los dos de bazas:** el **evaluador de bazas** (qué carta
gana, con triunfo y palo de salida) va como módulo aparte (`core/games/bazas.ts`) con sus propios
tests, y lo usan **brisca y tute**. El **mus no lo usa**: no tiene bazas, es de lances y apuestas.

**Ojo con la baraja:** el orden de fuerza **no es el del Culo**. Brisca y tute van
`2 < 4 < 5 < 6 < 7 < Sota < Caballo < Rey < 3 < As` (el **tres** es la segunda más alta), mientras
que el Culo tiene `… < As < 5 de oros`. Cada juego lleva su tabla de orden; los PNG de
`public/cards/es/` se comparten tal cual.

### 8.1 · Mentiroso — ✅ hecho (local, bots y con amigos, verificado por e2e de dos navegadores)
- **Qué**: juego de farol para 3–6: se reparte toda la baraja, cada uno echa cartas boca abajo
  diciendo qué son (puede mentir en el valor, **nunca en la cantidad**) y cualquiera puede gritar
  «¡mentiroso!». Gana quien se queda sin cartas.
- **Hecho** ✅ (15-10-2026) **motor y mesa**, jugable contra bots:
  - **Baraja compartida**: `core/games/baraja.ts` (front) y `apps/baraja.py` (servidor) reúnen lo
    que es igual en todos los juegos —palos, valores, construir, barajar, repartir—. El Culo pasa a
    usarla y se queda solo con **su** orden de fuerza (lo que no es de nadie más). El aviso que
    importa: el orden de brisca/tute **no** es el del Culo (allí el tres es la segunda carta más
    alta), así que cada juego trae su tabla.
  - **Motor puro en TS** (`core/games/mentiroso/mentiroso-engine.ts`) con **24 tests**, incluida
    una partida entera con bots que siempre termina y no pierde ni una carta.
  - **Motor en Python** (`apps/mentiroso/engine.py`), port fiel del anterior, con los **mismos 25
    casos** de test: las reglas están escritas dos veces (local y servidor) y la única forma de que
    no se separen es probarlas igual en los dos sitios.
  - **Bot** (`mentiroso-bots.ts`): echa la verdad cuando la tiene, miente con la carta que menos le
    sirve, retira los cuatro iguales y desconfía cuando las cuentas no le salen.
  - **Mesa** (`features/games/mentiroso/`): menú (3–6 jugadores, a 1/3/5 manos), rivales con sus
    cartas y sus manos ganadas, el montón (solo el número: nunca se revela), el valor que se está
    diciendo, tu mano, los botones de poner/desconfiar/retirar los cuatro, el registro de la mano y
    el panel de reglas. 53 claves de i18n nuevas en los tres idiomas.
  - Declarado en `game-catalog.ts` (`mode: 'bots'`) con su ruta y su pantalla.
- **Hecho** ✅ (15-10-2026) el **modo servidor**, y con él una capa de salas **compartida**:
  - **`apps/salas/`** es la capa común a todos los juegos online: la sala (códigos de 4 letras sin
    las que se confunden al dictar, asientos, anfitrión, reconexión — incluida la carrera de la
    conexión vieja que ya se arregló en el Culo), el WebSocket autoritativo, los endpoints
    (`POST /api/salas/`, `GET /api/salas/<code>/`, `.../join/`, `GET /api/salas/juegos/`) y el
    avance automático de los bots. **No sabe de cartas**: lo que sabe es que detrás hay un juego.
  - **`apps/salas/juegos.py`** es el contrato que cumple cada juego: arrancar, decir qué ve cada
    asiento, aplicar una acción del jugador, a quién le toca si es bot y si sigue en marcha. Seis
    cosas. Añadir un juego online es escribir eso sobre su motor (que ya está probado) y
    registrarlo: **no se copia la sala, ni el WebSocket, ni los endpoints**.
  - **El Mentiroso enchufado** (`apps/mentiroso/juego.py` + `bots.py` + `apps.py`): el envoltorio
    sobre el motor, el bot en Python y el registro automático al arrancar Django. La ruta nueva es
    `ws/salas/mentiroso/<código>`.
  - **Verificado con 23 tests nuevos** (48 en total en la app): lobby, códigos, reconexión, que el
    servidor rechace lo que no vale (fuera de turno, carta ajena, acción que no existe), el bot
    moviendo ficha, la API REST y **cinco tests de WebSocket reales** contra la app ASGI (sin token
    cierra con 4401, sala que no existe con 4404, entrar y ver el lobby, empezar y recibir la
    partida repartida, y una jugada imposible rechazada por el servidor).
  - **Verificado además en el stack levantado**: `GET /api/salas/juegos/` →
    `{"mentiroso":{"minPlayers":3,"maxPlayers":6,"opciones":{"manos":3}}}` y
    `POST /api/salas/` → **201** con código.
- **Falta (lo siguiente)**: **enchufar la mesa al servidor**. El servicio genérico del front ya
  está (`core/services/sala-online.service.ts`: crear, mirar, conectar, acciones y los errores del
  servidor traducidos por código), pero la pantalla del Mentiroso todavía solo ofrece «contra bots»:
  hay que añadir la opción **«con amigos»** con su lobby (código para dictar, enlace directo,
  quién está, repartir) y que la misma mesa pinte la vista del servidor. Después, el e2e de dos
  navegadores y la auditoría de accesibilidad (la ruta ya está en la lista de `a11y.spec.ts`).
- **Hecho cuando**: dos navegadores distintos juegan una mano entera (mentir, desconfiar y acertar)
  contra el servidor real; la mesa pasa la auditoría de accesibilidad.
- Esfuerzo: **6–8 h** (llevadas ~6 h: motor, bot, mesa y servidor).

### 8.2 · Brisca — ✅ hecho (local, bots y con amigos, verificado por e2e de dos navegadores)
- **Qué**: el juego de bazas más popular de España. 3 cartas cada uno, una carta marca el triunfo,
  se juega una carta sin obligación de asistir, gana el triunfo más alto (o la más alta del palo de
  salida) y el que gana roba y sale. As 11, tres 10, rey 4, caballo 3, sota 2. Empate a 60 anula el
  juego.
- **Hecho** ✅ (15-10-2026):
  - **El evaluador de bazas, compartido con el tute** (`core/games/bazas.ts` + `apps/bazas.py`): el
    orden de fuerza —donde está la trampa, porque **el tres es la segunda carta más alta**, no el
    rey—, lo que vale cada carta al contar y quién gana una baza. Se escribe una vez y lo usan los
    dos juegos de bazas.
  - **Motor en TS** (20 tests) y **en Python** (20 tests, los mismos casos), incluida una partida
    entera con bots que termina y no pierde ni una carta.
  - **Bot** que juega como se juega: si puede ganar la baza con una carta que no valga tantos, la
    gana; si no, suelta la que menos le duele; no malgasta un triunfo alto por una baza que no vale
    nada; y cambia el triunfo por el siete cuando le conviene.
  - **Mesa jugable contra bots** (2 o 3 jugadores, a 1, 3 o 5 juegos): el triunfo a la vista, la
    baza en curso, tu mano, los tantos y los juegos de cada uno, el botón de cambiar el triunfo, el
    registro de bazas y el panel de reglas. 35 claves nuevas en los tres idiomas.
  - **Enchufada a la capa de salas** (`apps/brisca/juego.py` + registro automático al arrancar):
    la ruta es `ws/salas/brisca/<código>`, sin escribir ni una línea de sala.
- **Falta**: el **modo online en la pantalla** (la opción «con amigos» y su lobby, lo mismo que le
  falta al Mentiroso) y el **modo de 4 por parejas**, que es como se juega la brisca de cuatro.
  Ahora mismo ofrece 2 y 3, que es lo que se juega sin pareja.
- **Hecho cuando**: se juega una partida entera a 3 juegos contra el servidor, con el cambio del
  siete de triunfo y el empate a 60 cubiertos por test; e2e de dos navegadores y accesibilidad.
- Esfuerzo: **10–14 h** (llevadas ~5 h: evaluador de bazas, motor doble, bot, mesa y servidor).

### 8.3 · Tute — ✅ hecho (local, bots y con amigos, verificado por e2e de dos navegadores)
- **Qué**: bazas con obligaciones y cantos. A 4 por parejas (10 cartas), a 2 (8 cartas con baceta).
  Obligatorio asistir, montar y fallar cuando se acaba la baceta; los acuses (rey + caballo) valen 40
  si son del triunfo («las cuarenta») y 20 si no, y solo se cantan tras ganar una baza; la última
  baza vale 10 («diez últimas»); y el tute (cuatro reyes o cuatro caballos) gana al instante.
- **Hecho** ✅ (15-10-2026):
  - **Motor en TS** (21 tests) y **en Python** (22 tests, los mismos casos). Lo que tiene miga, y
    está cubierto por test, es **la obligación de jugar**, que cambia a mitad de la partida:
    mientras quede baceta solo obliga el **triunfo** y sin montar; cuando se acaba, hay que
    **asistir, montar y fallar**, y si no tienes del palo ni triunfo vale cualquier carta
    (contrafallo). El test que lo fija usa el caso que engaña: **el tres sí monta al siete**.
  - **Acuses**: rey + caballo del mismo palo, 40 si son del triunfo y 20 si no, solo **después de
    ganar una baza** y **uno por baza** (los tres casos, con test).
  - **El tute** (cuatro reyes o cuatro caballos) gana al instante, y las **diez últimas** (la
    última baza vale 10 y decide los empates) están en el tanteo.
  - **Bot** que canta lo que puede (el tute primero, y las cuarenta antes que las veinte) y que
    juega respetando las obligaciones: gana la baza con la carta legal más barata, y si no puede,
    suelta la que menos le duele.
  - **Mesa jugable contra bots** (2 o 3 jugadores, a 101 tantos): las cartas que **no** puedes
    jugar se ven apagadas —el motor dice cuáles son legales y la mesa lo enseña, en vez de dejar
    que te equivoques—, los botones de cantar, la baceta, el triunfo, el registro y las reglas.
    24 claves nuevas.
  - **Enchufada a la capa de salas** (`apps/tute/juego.py` + registro automático), sin escribir
    nada de sala. Al probarlo salió **un bug de verdad**: el envoltorio devolvía el asiento de una
    jugadora humana como «turno de bot», o sea que el servidor habría jugado su mano. Está
    arreglado (solo se mira a los bots) y con test.
- **Falta**: el **modo online en la pantalla** (la opción «con amigos» y su lobby, lo mismo que les
  falta al Mentiroso y a la Brisca) y el **modo de 4 por parejas**.
- **Hecho cuando**: partida entera a 101 tantos con las cuarenta, las diez últimas y un tute
  cantado, todo cubierto por tests; e2e de dos navegadores y accesibilidad.
- Esfuerzo: **14–18 h** (llevadas ~6 h: motor doble, bot, mesa y servidor).

### 8.4 · Mus — ✅ hecho (local, bots y con amigos, verificado por e2e de dos navegadores)
- **Qué**: el juego español por excelencia. Cuatro en parejas, 4 cartas, fase de mus (descartar), y
  cuatro lances con apuestas en orden fijo: grande, chica, pares y juego (o punto). Regla de los 8
  reyes, órdago, piedras hasta 40, juegos y vacas. Las señas entre compañeros.
- **Hecho** ✅ (15-10-2026):
  - **Motor en TS** (29 tests) y **en Python** (30 tests, los mismos casos), con lo que tiene
    miga de verdad: el orden de las cartas con la **regla de los ocho reyes** (el tres vale lo
    mismo que el rey y el dos lo mismo que el as, o sea que empatan), la jerarquía de los pares
    (duples —dos parejas o cuatro iguales— por encima de medias, y estas de pareja), el **orden
    del juego** (31, 32, 40, 37, 36, 35, 34, 33; el 38 y el 39 no existen) y el **punto** cuando
    nadie llega a 31.
  - **Los cuatro lances en orden** con su tanteo: 3 piedras unas duples y 2 unas medias y 1 una
    pareja; 3 un 31 y 2 otro juego; 2 la grande y la chica. Y el **corte del mus una sola vez**:
    en cuanto uno corta, se cierra el descarte para todos.
  - **Los envites** (paso, envido con mínimo de dos, quiero, no quiero, órdago): **quien responde
    es siempre de la pareja contraria** —lo que parece obvio y no lo era: mi primera versión
    dejaba que respondiera un compañero—, no querer le da una piedra a quien envidó, y el órdago
    se juega la vaca.
  - **Bot** que evalúa los cuatro lances: pide mus con mano mala (una sola vez, que si no cuatro
    bots se quedan dando vueltas), descarta lo que no le sirve y aprieta cuando tiene jugada.
  - **Mesa jugable** contra bots: el marcador de piedras y juegos por pareja, **tu jugada y la de
    tu compañero** a la vista (lo que en la mesa real se dicen por señas), los botones de envite
    con la cantidad, el descarte marcando cartas, el registro y las reglas. 60 claves nuevas.
  - **Enchufada a la capa de salas** (`apps/mus/juego.py` + registro automático), sin escribir
    nada de sala.
  - **Una vaca entera de cuatro bots hasta el final**, con test: es el único de los cuatro que
    tenía que demostrar que termina (llegando a 3 juegos).
- **Dos bugs de verdad** que salieron al probarlo, los dos con test:
  1. El motor no comprobaba **a quién le tocaba hablar**, así que el servidor aceptaba un «mus» o
     un envite fuera de turno. Y al arreglarlo apareció el segundo: la fase de descarte no tenía
     turno definido, así que cuatro bots se quedaban dando vueltas entre mus y descarte sin llegar
     nunca a los lances.
  2. Las **40 piedras** solo se comprobaban al resolver un lance, no cuando el `+1` de un envite
     rechazado cruzaba la raya: el debug lo pilló con una pareja en **44 piedras** y la partida
     siguiendo. Ahora se comprueba en los dos sitios.
- **Falta**: el **modo online en la pantalla** (la opción «con amigos» y su lobby, lo mismo que les
  falta al Mentiroso, a la Brisca y al Tute) y las **señas** (fase 2: botones que solo ve el
  compañero y que el servidor verifica, rechazando una seña falsa).
- **Hecho cuando**: una vaca entera jugada por dos parejas contra el servidor, con el orden del
  tanteo (grande → chica → pares → juego) y el corte del mus cubiertos por test; e2e de cuatro
  navegadores; accesibilidad. Las señas, cuando llegue su fase, con test de seña falsa rechazada.
- Esfuerzo: **25–35 h** (llevadas ~8 h: motor doble, bot, mesa y servidor).

---

## Auditoría completa del 16-10-2026 · P0

Tres auditorías en paralelo (backend, frontend, infraestructura), cada hallazgo comprobado
**con peticiones reales** y releído después en el código antes de tocar nada. Los críticos ya
están cerrados.

### Cerrado (con test que lo fija)

| Agujero | Qué pasaba | Arreglo |
| --- | --- | --- |
| IDOR en cuentas | `PATCH`/`DELETE /api/users/<id>/` funcionaba sobre cualquiera (cambiar el email de otro = robarle la cuenta) | `get_queryset` por acción: escribir o borrar, solo lo tuyo (404 al resto) |
| ELO fabricado | `GameSerializer` exponía `rated`; tres peticiones bastaban para declararse ganador (1600 → 1616 medido) o **restarle** ELO a un rival | `rated`, `status` y los marcadores, de solo lectura; cada uno solo ve sus partidas |
| Torneos ajenos | `DELETE /api/tournament/<id>/` borraba el torneo de otro con su bracket | Borrar: solo el creador. Reportar y confirmar: creador **y participantes** |
| API pública | La key se la crea cualquier usuario, y con ella se borraban partidas y torneos de todos | Comprobación de propiedad en los `PUT`/`PATCH`/`DELETE` (403) |
| Avatares | Se aceptaba un `.txt` o un `.html` con JavaScript (servido desde el propio dominio) y de cualquier tamaño | Tope de 2 MB + imagen de verdad (Pillow, no el `content-type`) |
| Login roto a propósito | Registrar el email de la víctima dejaba su login en 500 **para siempre** | `filter().first()` en vez de `get()` |
| Chat | `POST /api/chat/messages/` daba 500 siempre | 405 con la ruta correcta |
| Intercambio del Culo | En local el intercambio **nunca ocurría**: se calculaba sobre la mano vieja y el reparto se lo llevaba por delante | `nextRoundWithSwaps` en el motor (donde se puede probar) + test |
| Mesas que no se desconectaban | Cuatro de las cinco mesas online dejaban el WebSocket abierto al salir: el servidor seguía contando a ese jugador | `desconectar()` en el `ngOnDestroy` de las cuatro |
| Tantos del Tute | Se escribían solo los de este juego, así que los 101 eran **inalcanzables** (el final de partida, código muerto) | Se acumulan entre juegos (TS y Python) |
| `mus.pares` en crudo | Era el nombre de un grupo de claves, no una etiqueta: la plantilla imprimía el literal | Clave `mus.paresLabel` en los tres idiomas |
| Intervalo del replay | Salir a mitad dejaba un `setInterval` vivo | `ngOnDestroy` que lo para |
| **Etiquetas flotantes en las imágenes** | `alpine/openssl:latest`, `owasp/modsecurity-crs:nginx`… un `docker compose pull` podía traer otra versión sin avisar (y en el borde, que es el WAF, eso duele) | Fijadas **al digest de la versión que ya corría**: reproducible y sin cambiar ni una versión. Con la nota de cómo actualizarlas, porque si no, esto se convierte en una trampa |
| **El backend corría como root** | El Dockerfile ya creaba `appuser` y hacía `USER appuser`, pero el compose de desarrollo lo pisaba con `user: root` (hace falta por los montajes de Windows) y **producción heredaba ese root** | Producción corre como `1000:1000`. Y `media/` se crea en la imagen con el dueño correcto: un volumen nuevo hereda ese dueño, así que los avatares se pueden escribir sin privilegios (comprobado con `touch` real dentro del contenedor) |
| **La CSP no se enviaba** | El proyecto definía `SECURE_CONTENT_SECURITY_POLICY`, que **no es un ajuste de Django**: nadie lo lee, así que no salía ninguna cabecera y parecía resuelto. Peor: el fichero `docker/nginx.conf` que **sí** traía una CSP no lo monta nadie (el montaje está comentado); el que corre es `nginx-app.conf`, y la política de aquel era floja de todas formas (le faltaba `wasm-unsafe-eval` y Google Fonts: habría roto el juego y las tipografías) | `django-csp` (middleware) para las respuestas de la API **y** la política en `nginx-app.conf` para el HTML, que es el documento donde el navegador la aplica. Un test compara las dos listas de directivas para que no se separen. Encontrar esto obligó a tirar del hilo: la cabecera aparecía en la API pero **no** en la página |
| **Índices que faltaban** | El ranking ordena **todos** los perfiles por ELO y el historial filtra por estado; sin índice, las dos consultas recorrían la tabla entera | `db_index` en `UserProfile.elo_rating` y un índice compuesto `(status, finished_at)` en `Game`. Comprobado con `EXPLAIN QUERY PLAN` que se usan **como covering index**, no solo que existan |
| **N+1 del historial del póker** | El resumen de cada fila costaba cuatro consultas sueltas (la última mano, sus dos jugadores y el recuento): 80 para una lista de veinte | Manos y jugadores precargados y recuento anotado. Ojo con el detalle: un `.filter()` sobre una relación **precargada** lanza consulta igual, así que los asientos se separan en Python. Fijado con `assertNumQueries(3)`: el número no crece con las filas |
| **Limitador mal contado** | Sin `NUM_PROXIES`, DRF usa `REMOTE_ADDR`, que detrás de nginx es **siempre la de nginx**: todos los anónimos del mundo compartían el cubo de 60/hora (uno lo agotaba y dejaba fuera a los demás). Y el login, que es donde se prueban contraseñas, no tenía límite propio | `NUM_PROXIES: 1` (nginx **añade** la IP real al final de `X-Forwarded-For`, así que un XFF inventado por el cliente no falsea nada) + `10/minute` en el login. Las tasas son configurables por entorno y el compose de desarrollo sube la de anónimos: con la de producción, los e2e se quedaban fuera a mitad de suite |
| **Emparejamiento humano del póker** | `get_match_queue()` devolvía una instancia **nueva por conexión**: con el backend en memoria cada jugador esperaba en su propia lista vacía y dos personas no se encontraban nunca (solo entraban bots, que no pasan por la cola). Ningún test lo veía porque todos inyectan la instancia a mano | La cola en memoria es única para todo el proceso (singleton), con dos tests que lo fijan desde fuera. El backend de Redis ya era correcto: allí el estado vive en Redis |
| **JWT sin revocación** | `BLACKLIST_AFTER_ROTATION` estaba en los ajustes pero faltaba la app `token_blacklist` (SimpleJWT lo ignora en silencio), la vista de refresh era propia y devolvía **el mismo** token, y el logout era un no-op con el comentario admitiéndolo: un refresh robado valía 7 días | App del blacklist + rotación real en la vista de refresh + logout que revoca + el front avisa al servidor antes de borrar los tokens |

Tests nuevos: `backend/tests/test_seguridad_auditoria.py` (17, uno por agujero, con el porqué
escrito) + 1 del motor del Culo.

Frontend (los tres hallazgos de la auditoría que quedaban):

- **El `<html lang>` no seguía al idioma**: se quedaba en el idioma con el que se sirvió el HTML, así
  que en francés un lector de pantalla leía con fonética inglesa (WCAG 3.1.1). Ahora `setLang()` (y la
  carga inicial) lo actualizan, con `DOCUMENT` inyectado para no romper el prerender.
- **Los formularios de acceso y registro avisaban en inglés**: los mensajes de validación y de error
  estaban escritos a mano en el código (`'Required'`, `Min N characters`…). Pasaron a claves de
  traducción en los tres idiomas. Se escapaban porque el comprobador de i18n solo mira las plantillas,
  no el TypeScript.
- **Los diez diálogos de los juegos** (fin de partida y reglas) no llevaban `aria-modal` y varios no
  tenían nombre accesible. Ahora todos lo llevan, y los de fin de partida apuntan con
  `aria-labelledby` a su título visible, que es el único que dice la verdad cuando el diálogo tiene
  dos estados o el título lleva un parámetro.
- **El foco de los diálogos** no se movía al abrirlos: quien navega con teclado se quedaba en el
  botón de detrás y el primer tabulador se iba a la página de fondo. Primera directiva del proyecto
  (`shared/directives/foco-dialogo.directive.ts`): al abrir recuerda dónde estaba el foco y lo lleva
  dentro, mientras está abierto el tabulador da la vuelta dentro, y al cerrar lo devuelve. Con e2e
  que lo comprueba **y comprobado que ese e2e falla si se quita la directiva** (un test que no sabes
  si falla cuando el arreglo no está no vale de nada).

Trampa que apareció al activar la CSP: los tests de accesibilidad fallaron en bloque porque axe se
inyecta como script en la página y `script-src 'self'` lo bloquea. Se arregló con un helper que
quita la cabecera **solo de los documentos** en esos tests (la inyección es la herramienta de
auditoría, no un flujo de usuario), dejando la comprobación de la cabecera en el backend y en `curl`.

Trampa que apareció al activar el blacklist: `RefreshToken.for_user()` **escribe** una fila en la
tabla de tokens emitidos, así que crearlo dentro de un test `async` (los de WebSocket) revienta con
`SynchronousOnlyOperation`. Esos tests ahora crean los tokens en el `setUp` (sync) y el helper solo
los lee. Tres tests que esperaban **403** donde ahora se responde
**404** se actualizaron con su motivo: un 403 confirmaría que el recurso existe.

### Pendiente (priorizado, sin tocar)

- **WAF**: el borde real (`owasp/modsecurity-crs:nginx`) usa la configuración de su imagen; los ajustes que se leen en `docker/nginx.conf` (paranoia level, umbral) **no se aplican** porque ese fichero no se monta. Queda por decidir la configuración buena del WAF y comprobarla con tráfico real. Es lo único que queda de la auditoría, y es una decisión de producto (cuánto apretar) más que un arreglo.
- WebSockets viejos (`/ws/rooms/`, `/ws/matchmaking`) abiertos sin autenticar.

---

## Trazabilidad con la evaluación

| Módulo declarado | Qué lo refuerza |
|---|---|
| Major · Web game multijugador | Ya cumplido con el póker online; **3.3** lo deja escrito; 5.1 y 5.2 lo amplían |
| Major · Public API segura | **D1/2.1** (esquema completo + tests de API key) |
| Major · WAF + Vault | Nada pendiente (verificado 403 y secretos en Vault) |
| Major · Framework front + back | **2.4, 2.5** (linters y tests) |
| Minor · ORM | **5.3** (modelos del póker) |
| Minor · Design system | **5.5** (temas) |
| Minor · Notificaciones | **3.2** (traducirlas) |
| Minor · i18n | **3.2** (hoy incompleto) |
| Minor · Navegadores | **2.2** + (13-10-2026) los e2e corren en **los cuatro motores**: Blink (chromium), Gecko (firefox), WebKit (webkit) y Edge (msedge). El CI ejecuta chromium+firefox+webkit |
| Minor · Torneos | **0.2 + 5.1** (resultados verificables y jugados de verdad) |
| Minor · Game customization | **5.5** |
| Bonus · Google OAuth | Nada pendiente |

---

## Definición de «hecho» (para todo el roadmap)

Un punto está hecho cuando: **(1)** pasa su comprobación, **(2)** está en el CI, **(3)** la
documentación afectada (`README`, `docs/*`) se actualiza en el mismo commit y **(4)** no baja el
número de tests.

## Riesgos y decisiones abiertas

| ID | Decisión | Opciones | Impacto |
|---|---|---|---|
| D1 | ¿Se queda el chat? | (a) arreglar + UI, (b) retirarlo | Bloque 1: 2 h vs 10–14 h |
| D2 | Resultados de torneo | (a) doble confirmación (rápido), (b) mesa de póker autoritativa (5.1) | 3–5 h vs 6–8 h |
| D3 | Base de datos | (a) seguir con SQLite (simple), (b) PostgreSQL | 4.2: 3–4 h; con SQLite, evitar varias réplicas |
| D4 | ¿Cuántas réplicas? | si es 1, Redis (4.1) puede esperar | 6–8 h |
| D5 | ¿Se retira el modo local? | mantenerlo como «modo local» es defendible y ya funciona | 0 h |

## Orden recomendado

**Semana 1 (dejar el proyecto sólido):** 0.1 → 0.3 → 1.2 → 0.2 → 2.2 → 2.1 → 3.1 → 3.3.
**Semana 2 (dejarlo defendible y desplegable):** 2.3 → 2.4 → 3.2 → 3.4 → 4.2 → 4.3 → (4.1 si hay réplicas) → 4.4.
**Después (producto):** 5.1 → 5.3 → 5.2 → 5.4 → 5.5 → Bloque 6 → Bloque 7.
**Juegos nuevos (decidido 14-10-2026):** Bloque 8 — 8.1 Mentiroso → 8.2 Brisca → 8.3 Tute → 8.4 Mus.
