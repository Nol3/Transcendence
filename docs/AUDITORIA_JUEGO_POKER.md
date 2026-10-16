# Auditoría del juego de póker — Transcendence (42 Málaga)

> Fecha: 2026-10-11 · Alcance: motor C/WASM (`juego/`), capa online (`backend/apps/games`),
> lobby Angular (`front/src/app/features/game`).
> Todo lo que sigue está **verificado con ejecución real**; los comandos para reproducirlo
> están al final de cada bloque.

---

## 1. Resumen ejecutivo

| Pregunta | Respuesta verificada |
|---|---|
| ¿El juego es póker? | **No.** Es un juego de puntuación tipo *Balatro*: 8 cartas, eliges 1–5, un descarte, y acumulas puntos hasta un objetivo. No hay apuestas, bote, ciegas, cartas comunitarias, `fold/check/call/raise/all-in` ni showdown. |
| ¿Se detectan bien las manos? | **Sí, al 100%.** Enumeradas las 2.598.960 manos de 5 cartas: las 9 categorías coinciden exactamente con las frecuencias oficiales del póker. |
| ¿Se comparan bien las manos? | **Estaba roto** (ganaba el jugador equivocado). **Arreglado y verificado** en esta auditoría. |
| ¿Hay IA / bot? | **No existe ninguna.** Cero referencias a IA en el motor; es hotseat (todos en el mismo teclado). |
| ¿Se puede jugar online? | **No.** El matchmaking empareja dos navegadores y les manda un `roomId`, pero **no hay partida en el servidor**: cada navegador sigue jugando su hotseat local. |
| ¿El backend conoce el resultado? | Solo lo que **el propio cliente** envía por `postMessage` → `POST /api/games/{id}/finish/`. No hay validación. |
| ¿El lobby del frontend funciona? | **No**: llama a `/api/rooms` y `/api/matchmaking/start`, que **devuelven 404** (no existen). |

**Veredicto:** el motor de evaluación de manos es sólido (y ahora correcto), pero el
producto **no es póker** y **no es online**. El módulo Major *«Web game multijugador»* (2 pts)
es el punto débil de la evaluación: tal como está, un evaluador estricto puede darle 0, y con
15 pts declarados el proyecto caería a **13 < 14 → suspenso**.

---

## 2. Hallazgos — motor C (`juego/src`, 6.777 líneas)

### A1. No es póker (crítico para el objetivo)
`game.c` implementa un juego de puntuación:
- `UpdateStateDealCards` (game.c:421-450) reparte **8 cartas** a cada jugador.
- `UpdateStatePlayerTurn` (game.c:543-569): un **descarte** de hasta 5 cartas por turno y un
  `CONFIRMAR` que **suma `lastResult.score`** al total del jugador.
- `CheckGameEnd` (game.c:695-707): termina cuando alguien llega a `targetScore` o se agotan `maxRounds`.

Grep de `bet|pot|chip|blind|fold|call|raise|dealer|community|flop|turn|river` sobre
`juego/src/*.c` → **0 resultados** (solo coincidencias en el header de `cJSON`).

Falta para ser póker: ciegas y dealer rotatorio, rondas de apuesta (preflop/flop/turn/river),
bote y botes laterales (all-in), `fold/check/call/raise/all-in`, showdown entre manos vivas,
y comparación lexicográfica de manos (A3).

### A2. Detección de manos: correcta (activo a conservar)
Enumeración exhaustiva de las C(52,5) = 2.598.960 manos contra las frecuencias oficiales:

| Categoría | Obtenido | Esperado |
|---|---|---|
| Carta alta | 1.302.540 | 1.302.540 |
| Pareja | 1.098.240 | 1.098.240 |
| Doble pareja | 123.552 | 123.552 |
| Trío | 54.912 | 54.912 |
| Escalera | 10.200 | 10.200 |
| Color | 5.108 | 5.108 |
| Full house | 3.744 | 3.744 |
| Póker | 624 | 624 |
| Escalera de color | 40 | 40 |

Incluye los casos difíciles: **rueda A-2-3-4-5** y escalera de color. `poker_hand.c` está bien escrito.

### A3. Comparación de manos: estaba rota → **ARREGLADO**
`EvaluateHand` produce un `score` **aditivo** (pareja=100+valor, color=500+suma…) y
`CalculateRoundWinner` decidía con `type` y luego `score`. Consecuencia: **gana el jugador equivocado**.

Casos reales medidos antes del arreglo:

| Enfrentamiento | Debe ganar | Decía el juego |
|---|---|---|
| Color A-K-9-5-2 vs A-K-8-6-4 | A (9 > 8) | **B** (545 > 543) |
| Doble par A-A-2-2 vs K-K-Q-Q | A (los ases mandan) | **B** (225 > 216) |
| Trío 9-9-9-A-K vs 9-9-9-K-Q | A (kicker A) | empate 309 → gana el primero |
| Pareja 2-2-A-K-Q vs 2-2-K-Q-J | A (kickers A,K) | empate 102 → gana el primero |
| Carta alta A-6-5-4-3 vs A-5-4-3-2 | A | empate por top-card |

**Arreglo aplicado** (`poker_hand.h/.c`, `game.c`):
- `HandResult` gana `int tiebreak[5]` con el desempate lexicográfico estándar (normalizado:
  en la rueda el As vale 1 → `{5,4,3,2,1}`).
- Nueva función pública **`CompareHands(a,b)`**: categoría y, a igual categoría, kickers.
- `CalculateRoundWinner` usa `CompareHands` en vez del score.
- El `score` aditivo se conserva intacto: sigue siendo la carrera de puntos del juego.

**Verificación posterior** (todo en verde):
- Frecuencias: 9/9 exactas (regresión sin cambios).
- **Invariantes del desempate sobre las 2.598.960 manos**: 0 violaciones (el desempate se
  contrasta contra el multiconjunto real de rangos, no contra sí mismo).
- Los 5 casos de la tabla: ahora gana el correcto.
- 7 enfrentamientos clásicos (escalera de color > póker > full > color/escalera > …): correctos.
- Propiedades: antisimetría y transitividad de `CompareHands` sin violaciones.

### A4. No hay IA (el comentario del código miente)
Grep de `bot|ai|cpu|automat|computer` en `juego/src` → **0 resultados**.
`game.c:612` decía «el rival es la mejor IA» → **corregido** en esta auditoría.
El juego es 100% hotseat: cada jugador actúa en el mismo dispositivo («Pasa el dispositivo a X»).

### A5. High scores que no persisten
`LoadHighScores`/`SaveHighScores` (game.c:920-944) usan `fopen("highscores.dat")`. En WASM eso
es el sistema de ficheros **en memoria** de Emscripten (MEMFS): la tabla de «MEJORES
PUNTUACIONES» **se pierde al recargar** y nunca llega al leaderboard del backend (que es ELO,
un sistema aparte). Hay un `juego/highscores.dat` de 124 bytes versionado en git.

### A6. Código muerto y baraja
- `game.h` declara `DealCardsToPlayer`, `SelectCardForPlayer`, `DeselectCardForPlayer`:
  **no existen** en ningún `.c` (si alguien las llama, no compila).
- `game_api.c` (`GamePause`/`GameIsPaused`/`GameRestart`/`GameSetVolume`): definidas y nunca
  usadas desde `main.c` ni desde la web. `IsDealAnimationComplete` tampoco se usa.
- Baraja: Fisher-Yates correcto, pero sobre `rand()` sembrado con `time(NULL)`
  (`game.c:147`). En local da igual; **si el servidor barajara así, las cartas serían predecibles**.

---

## 3. Hallazgos — capa online (lo que pide el encargo)

### B1. Los endpoints del lobby no existen
`RoomService` (`front/src/app/core/services/room.service.ts`) llama a `/api/rooms`,
`/api/rooms/{id}/join|leave|start`, `/api/matchmaking/start`, `/api/matchmaking/cancel`.
Verificado con el servidor en marcha (daphne, Django 4.2.13):

```
GET  /api/rooms/               -> HTTP 404
POST /api/matchmaking/start/   -> HTTP 404
POST /api/matchmaking/cancel/  -> HTTP 404
```

No hay app `rooms` en `backend/apps/` (solo `users`, `games`, `chat`, `tournament`, `public_api`).
El estado `searching`/`matched` del lobby es **puramente cosmético**.

### B2. El matchmaking empareja… y nada más
`MatchmakingConsumer` (`backend/apps/games/consumers.py`) mantiene una cola en memoria de
proceso y empareja los dos primeros canales. Verificado con dos clientes WebSocket reales:

```
cliente A: {"type":"searching"}
cliente B: (conecta) -> A y B reciben {"type":"match_found","roomId":"28a1b253a073"}
```

- **No hay timeout ni bot**: no existe código de espera máxima; si nadie más está en cola, el
  cliente se queda en `searching` indefinidamente (y `cancel` da 404).
- **No hay partida**: el `roomId` no se usa para nada. Tras el match, la sala no emite **ningún**
  estado de juego (verificado: 1,5 s de espera sin mensajes). Cada navegador sigue con su
  hotseat local dentro del iframe.

### B3. El resultado lo decide el cliente (integridad)
`game-board.ts` escucha `postMessage` del iframe y hace
`POST /api/games/{id}/finish/` con `winner` y los marcadores que vengan del navegador. Además
`POST /api/games/create_game/` **siempre** crea la partida contra el usuario fantasma
`AI_Opponent` (verificado: `player2=AI_Opponent`). Cualquiera puede reportar el resultado que
quiera: el ELO, las victorias y los torneos se alimentan de un dato no verificado.

### B4. `RoomConsumer` no autentica y acepta estado del cliente (seguridad)
Verificado en vivo:

```
WS /ws/rooms/<id> SIN token            -> conecta y recibe room_update
cliente envía {"room":{"status":"INYECTADO"}} -> se difunde al grupo sin validación
```

El consumer de salas **no comprueba el JWT** (a diferencia de `TournamentConsumer`, que sí lo
hace y además ignora todo lo que envíe el cliente) y hace `group_name = f'room_{room_id}'` con
un `room_id` sin validar → se puede escuchar cualquier grupo `room_*`.

### B5. No escala más de un proceso
`CHANNEL_LAYERS` usa `InMemoryChannelLayer` (`config/settings.py`). Con más de un worker de
Daphne, dos jugadores pueden caer en procesos distintos y **no verse**. Para «online real» hace
falta `channels-redis`.

---

## 4. Hallazgos — documentación e incoherencias (arregladas)

| Documento | Afirmaba | Realidad |
|---|---|---|
| `juego/TODO.md` | «Fase 5: Comodines» **completada** (tienda, 4 comodines, reroll, `joker.h/c`) | No existe `joker.c/h` ni tienda: **0 referencias** en el código |
| `juego/TODO.md`, `DEPLOY.md` | «API de embedding `window.PokerRaceAPI` + `PokerRaceGame`» | No existe: verificado en runtime (`pokerAPI:false`) |
| `DEPLOY.md` | Eventos `player-turn`, `round-end`, `gameover`, `pause/resume/setVolume/restart` | `NOTIFY()` es **no-op** en `game.c`; el único evento real es `game-finished` |
| `front/public/i18n/*.json` | Reglas del lobby: «5 cartas», «roba 1 por turno», «reduce los PV del rival a 0» | Describían **otro juego** (cartas con HP); no el que hay |
| `README.md` | «Angular 21» | `package.json`: Angular **^20.2.1** |

Todo lo anterior está corregido en esta auditoría (i18n en ES/EN/FR, `TODO.md`, `DEPLOY.md`,
comentario de `game.c`).

---

## 5. Lo que está bien y no hay que tocar

- **Autenticación**: JWT con rotación/blacklist, Google OAuth2 con verificación server-side,
  validación de formularios en front y back, contraseñas PBKDF2. Registro/login probados
  end-to-end en esta auditoría (`201` + tokens).
- **Backend**: `manage.py check` limpio, migraciones OK, **8/8 tests del torneo en verde**.
- **Torneos**: brackets single-elimination con byes, progresión, eliminación, idempotencia, y
  WebSocket **autenticado** que no acepta estado del cliente.
- **ELO + leaderboard**: cálculo correcto y consistente (`finish` → `200`, stats reflejan la partida).
- **Infra**: Docker Compose con WAF (ModSecurity/CRS), Vault, TLS generado en caliente, nginx.
- **Frontend**: `npm ci && ng build` compila limpio (7,35 s); design system, i18n, notificaciones.
- **Motor de manos C**: detección exacta (A2) y, desde hoy, comparación correcta (A3).

---

## 6. Riesgo de evaluación (42)

1. **Major «Web game multijugador» (2 pts)** — el subject exige jugar **contra otros usuarios**.
   Hoy: hotseat local + matchmaking decorativo. Riesgo real de 0 pts.
   15 − 2 = 13 < 14 → **el proyecto suspende**. Es el motivo principal para cambiar el scope.
2. **«Multi-user support works (multiple users can use the app simultaneously)»** en
   *Functionality*: hoy dos usuarios no pueden jugar entre sí.
3. **Integridad del resultado** (B3): un evaluador puede señalarlo como agujero de seguridad.
4. Menores: high scores que no persisten (A5), `RoomConsumer` sin auth (B4), docs que
   sobrevendían funcionalidad (ya corregido).

---

## 7. Opciones de scope

### Opción A — Motor de póker autoritativo en el servidor (Python) + UI Angular  ← **recomendada**
Reescribir el juego como **Texas Hold'em** con la lógica en el servidor (Django Channels) y la
UI en Angular. El WASM actual queda como **«modo local / mismo dispositivo»** (feature legítima
y ya funciona).
- El servidor decide baraja, cartas ocultas, apuestas, bote y showdown → **no se puede hacer trampa**
  y las cartas privadas son privadas de verdad.
- Los **bots son triviales** (jugadores del lado servidor) y el **timeout → bot** cae en el mismo sitio.
- El motor C **no se puede reutilizar** para esto (no tiene apuestas ni estado de red) y mantener
  dos motores duplica el trabajo: el C se queda como está (ya arreglado) para el modo local.
- Conserva los 15 pts actuales y convierte el Major del juego en defendible.

### Opción B — Implementar el póker dentro del motor C y añadir red encima
Mantiene el atractivo «juego en C/WASM», pero exige reescribir `game.c`/`renderer.c` (apuestas,
bote, estados de calle) **y** hacer el motor autoritativo en red (o convertirlo en cliente tonto
del servidor). Coste muy superior y sin ventaja evaluativa real. **No recomendada.**

### Opción C — Quedarse con el hotseat y solo limpiar
Barato (ya está casi hecho), pero **deja el riesgo del Major** y no cumple el encargo («online real»).

---

## 8. Plan por fases (Opción A)

| Fase | Entregable | Verificación |
|---|---|---|
| **0. Honestidad + motor actual** ✅ *hecho* | Comparación de manos correcta; docs e i18n sin afirmaciones falsas; WASM recompilado y probado en navegador | Tests de invariantes + frecuencias + arranque en Chrome/Edge headless |
| **1. Dominio del póker (servidor)** ✅ *hecho* | `apps/poker/engine`: baraja (`secrets`), mejor 5 de 7, comparación lexicográfica, ciegas y dealer, 4 calles, all-in, **side pots**, showdown, reparto de botes y ficha impar | 46 tests en verde + exhaustivo de 2.598.960 manos exacto (6 s) |
| **2. Partida autoritativa por WebSocket** ✅ *hecho* | `TableConsumer` (`/ws/poker/table/<id>`): JWT, **vista por jugador** (cada uno ve solo sus cartas), acciones validadas en servidor, timeout de turno, expulsión por inactividad | Prueba e2e con clientes WS reales: 21/21 comprobaciones (mano completa, privacidad en 18 estados, acciones ilegales rechazadas) |
| **3. Matchmaking con cola y bot** ✅ *hecho* | `PokerMatchmakingConsumer` (`/ws/poker/matchmaking`): cola, niveles de apuesta, `cancel`, **timeout → mesa con bot** y bot que juega solo | Prueba e2e: emparejamiento humano-humano y bot tras 3 s de espera |
| **4. UI de póker en Angular** ✅ *hecho* | Página `/poker` (`features/poker`): lobby con niveles de apuesta, cola con contador, mesa con asientos, cartas, bote, acciones (slider de subida + atajos), temporizador de turno, resultado y siguiente mano; i18n ES/EN/FR; enlaces en navegación y portada | Navegador real (Edge headless + CDP): **15/15** comprobaciones, jugada una mano completa pulsando botones, sin errores de consola |
| **5. Integración** ✅ *hecho (ELO)* | `apps/poker/services.py`: al terminar la partida el **servidor** escribe el resultado. Humano vs humano → ELO y balance; vs bot → solo historial (no puntúa) | Tests con base de datos: puntuable, no puntuable y empate |
| *Pendiente* | Torneos jugando en mesas de póker online (hoy el bracket lanza el modo local) y Redis para la cola | — |
| **6. Extra (opcional)** | Chat de mesa, espectadores, estadísticas por mano, ciegas de torneo | — |

Estimación: **2–3 semanas** de una persona, con cada fase entregable y verificable por separado.

---

## 9. Cambios aplicados en esta auditoría (y cómo se verificaron)

| Fichero | Cambio |
|---|---|
| `juego/src/poker_hand.h` | `tiebreak[5]` en `HandResult` + declaración de `CompareHands` |
| `juego/src/poker_hand.c` | `FillTiebreak()` (desempate de póker) + `CompareHands()`; `rank1/rank2` inicializados |
| `juego/src/game.c` | `CalculateRoundWinner` usa `CompareHands`; comentario falso sobre la IA corregido |
| `juego/web/*` | **WASM recompilado** (emcc 5.0.6): `index.wasm` 479.295 → 481.066 bytes |
| `front/public/i18n/{es,en,fr}.json` | Reglas del lobby reescritas para el juego real |
| `juego/TODO.md`, `juego/DEPLOY.md` | Retiradas las afirmaciones falsas (comodines, `PokerRaceAPI`, eventos) |
| `backend/apps/poker/**` | **Módulo de póker online**: motor autoritativo, mesas con turnos y bots, WebSockets de mesa y matchmaking, 46 tests |
| `backend/config/asgi.py`, `backend/config/settings.py` | Rutas `/ws/poker/...` y app `apps.poker` registrada |
| `backend/apps/__init__.py` | Faltaba: sin él, `manage.py test apps.poker` no descubre los tests |
| `docs/POKER_ONLINE.md` | Documentación del módulo: reglas, protocolo WS, UI y despliegue |
| `front/src/app/features/poker/**`, `core/services/poker.service.ts` | **Interfaz web**: lobby, cola, mesa, acciones y resultado |
| `front/src/app/{app.routes.ts,shared/components/header/header.html,features/home/home.html}`, `public/i18n/*.json` | Ruta `/poker`, enlaces de navegación y textos ES/EN/FR |
| `front/src/environments/environment.ts` | En desarrollo el WebSocket apunta al backend (el dev-server no proxya `/ws`) |
| `backend/apps/games/services.py` | `finish_game(..., rated=False)`: registrar una partida sin tocar ELO ni balance |
| `.env` (no versionado) | Configuración para `docker compose up` |

Verificación del build web: Edge headless + CDP → `moduleCalledRun: true`, `errs: []`,
canvas 1280×720, `glGetError: 0`, raylib 6.0 inicializado, y la captura de pantalla muestra la
mesa verde del tapete con el texto del menú (98% de píxeles no negros).

---

## 10. Cómo reproducir todo

Los harnesses usados están versionados en **`scripts/audit/`**.

```bash
# ── Motor: invariantes, frecuencias y casos de comparación (WSL + gcc) ──
wsl -d Ubuntu -- bash scripts/audit/run2.sh
#   -> 9/9 frecuencias exactas · 0 violaciones de invariantes · casos OK

# ── Recompilar el juego a WASM (WSL + emsdk) ─────────────────────────
wsl -d Ubuntu -- bash -lc 'source ~/emsdk/emsdk_env.sh; cd juego && make web'

# ── Backend: check, migraciones y tests del torneo ───────────────────
wsl -d Ubuntu -- bash scripts/audit/run_backend.sh
#   -> check limpio · migrate OK · 8/8 tests de torneo

# ── Sonda REST + WebSocket (matchmaking y salas) ─────────────────────
wsl -d Ubuntu -- bash scripts/audit/run_e2e.sh

# ── Juego en navegador real (headless + CDP) ─────────────────────────
wsl -d Ubuntu -- bash scripts/audit/start_server.sh   # sirve juego/web en :8099
node scripts/audit/probe_wasm.js http://localhost:8099/index.html

# ── Póker online: tests y partida real por WebSocket ─────────────────
wsl -d Ubuntu -- bash scripts/audit/run_poker_tests.sh      # 46 tests
wsl -d Ubuntu -- bash scripts/audit/run_poker_e2e.sh        # 21 comprobaciones e2e

# ── UI de póker en navegador real (con backend y ng serve levantados) ─
node scripts/audit/probe_poker_ui.js

# ── Frontend ─────────────────────────────────────────────────────────
cd front && npm ci && npm run build

# ── Despliegue completo (TLS + WAF + Vault) ──────────────────────────
cp .env.example .env && docker compose up --build   # https://localhost:8443
```

> Los scripts tienen rutas absolutas (`/mnt/c/Users/aleja/...`) apuntando a esta máquina y
> requieren `gcc`, `emsdk` (`~/emsdk`) y el venv de Python en WSL. Ajusta las rutas si los mueves.

Captura de la verificación en navegador: `docs/auditoria/juego_menu.png`.
