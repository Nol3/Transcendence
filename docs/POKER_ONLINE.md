# Póker online (Texas Hold'em sin límite) — módulo `apps.poker`

Motor de póker **autoritativo en el servidor**: el servidor baraja, reparte, valida
cada acción y decide quién gana. El navegador solo pide y dibuja lo que se le manda,
así que no puede ver cartas ajenas ni mover fichas por su cuenta.

> Estado: **jugable de punta a punta** (Fases 1–5 del plan de auditoría). El usuario
> entra en la web, se mete en cola, le empareja con otro jugador o con un bot, y juega
> una partida real de Texas Hold'em desde el navegador.

---

## 1. Estructura

```
backend/apps/poker/
├── engine/                 # Lógica pura, sin Django ni E/S
│   ├── cards.py            # Card, Deck (barajado con secrets.SystemRandom)
│   ├── hand_eval.py        # mejor 5 de 5/6/7, comparación lexicográfica
│   └── game.py             # Hand: ciegas, calles, all-in, side pots, showdown
├── bots.py                 # Política del bot (fuerza + pot odds)
├── tables.py               # PokerTable: turnos, temporizadores, fin de partida
├── consumers.py            # TableConsumer + PokerMatchmakingConsumer (WebSocket)
└── tests/                  # 46 tests (motor, bots, mesas)
```

Separar el motor (`engine/`) de la capa de red es lo que permite probar las reglas
sin levantar un servidor y sin base de datos: los tests del motor corren en menos de
2 segundos y la verificación exhaustiva de manos en 6.

## 2. Reglas implementadas

- **Texas Hold'em sin límite**, 2–6 asientos (el matchmaking crea mesas heads-up).
- Botón rotatorio; **heads-up**: el botón pone la ciega pequeña y habla primero preflop.
- Cuatro calles: preflop, flop, turn, river. Se quema una carta antes de cada calle.
- Acciones: `fold`, `check`, `call`, `bet`/`raise` (con apuesta mínima = última subida
  completa) y `all_in`.
- **Un all-in corto** (menor que la subida mínima) **no reabre la acción** para quien ya
  actuó: solo puede igualar o retirarse.
- **Botes laterales**: se devuelve la apuesta no igualada y se reparten los botes por
  niveles de aportación. Los jugadores retirados aportan pero no pueden ganar.
- **Showdown** con comparación lexicográfica (categoría + kickers). Botes divididos y la
  ficha impar va al primer asiento a la izquierda del botón.
- Si todos se retiran menos uno: se gana el bote **sin** mostrar cartas.
- **Inactividad**: si un jugador conectado no actúa en `POKER_TURN_TIMEOUT` segundos, el
  servidor pasa o foldea por él.

## 3. Protocolo WebSocket

Autenticación: JWT en el query string, igual que el torneo — `?token=<access>`.
Sin token válido el handshake se rechaza con **4401**.

### Cola de espera — `/ws/poker/matchmaking?token=…&size=N`

`size` es el **tamaño de mesa** (2–6) y viaja en la URL: el servidor lo necesita antes
de meter al jugador en la cola, porque el emparejamiento es por **(nivel de apuesta,
tamaño de mesa)**. Si se cambiara después, dos clientes que quieren mesa de 6 podrían
emparejarse de dos en dos.

| Servidor → cliente | Significado |
|---|---|
| `{"type":"ready","stakes":{…},"table_sizes":[2,3,4,5,6],"table_size":2,"queue_timeout":15}` | Conectado y listo |
| `{"type":"searching","queue_timeout":15,"table_size":3}` | En cola, esperando compañeros |
| `{"type":"match_found","table_id":"…","opponent":"…","seats":6,…}` | Mesa asignada (`seats` = asientos) |
| `{"type":"cancelled"}` / `{"type":"stake_set"}` / `{"type":"table_size_set"}` | Respuestas de control |

| Cliente → servidor | Efecto |
|---|---|
| `{"type":"stake","stake":"micro"\|"low"\|"mid"}` | Elige nivel de apuesta (1/2, 5/10, 25/50) |
| `{"type":"table_size","size":2…6}` | Cambia el tamaño de mesa (rehace la entrada en la cola) |
| `{"type":"cancel"}` | Sale de la cola |
| `{"type":"ping"}` | Latido |

Hacen falta `size - 1` humanos; si no aparecen en `QUEUE_TIMEOUT` segundos
(`POKER_QUEUE_TIMEOUT`, por defecto 15 s), los huecos que queden se cubren con **bots**
(una mesa de 6 con un solo humano se llena con 5).

### Mesa — `/ws/poker/table/<table_id>`

| Servidor → cliente | Significado |
|---|---|
| `{"type":"table_state","you":0,"table":{…},"game":{…},"log":[…]}` | Estado **personalizado**: `game.seats[i].hole` solo trae cartas del asiento `you` (y de todos en el showdown) |
| `{"type":"error","error":"no es tu turno"}` | Acción rechazada |

Dentro de `game`: `street`, `board`, `pot`, `actor`, `current_bet`, `min_raise_to`,
`seats[]`, `legal_actions[]`, `complete`, `result`, `history[]`.
`legal_actions` solo viaja al jugador que tiene el turno.

| Cliente → servidor | Efecto |
|---|---|
| `{"action":"fold"}` · `{"action":"check"}` · `{"action":"call"}` | Acciones simples |
| `{"action":"raise","amount":120}` | `amount` es el **total en la calle**, no el incremento |
| `{"action":"all_in"}` | Todo el stack |
| `{"type":"ping"}` | Latido |

Todo se valida en el servidor: turno, acción permitida y rango del importe. Una acción
ilegal devuelve `error` y **no** cambia el estado.

## 4. Cómo ejecutar y probar

```bash
# Tests del motor, bots y mesas (rápido, sin base de datos)
cd backend && python manage.py test apps.poker

# Verificación exhaustiva: las 2.598.960 manos de 5 cartas deben dar las
# frecuencias oficiales del póker (tarda ~6 s)
POKER_EXHAUSTIVE=1 python manage.py test \
  apps.poker.tests.test_hand_eval.EvaluateTests.test_frecuencias_exhaustivas

# Partida real por WebSocket (matchmaking + mesa + bot + inactividad)
POKER_QUEUE_TIMEOUT=3 POKER_TURN_TIMEOUT=6 python manage.py runserver 127.0.0.1:8011
python scripts/audit/probe_poker_ws2.py
```

Variables de entorno útiles: `POKER_QUEUE_TIMEOUT` (espera antes del bot) y
`POKER_TURN_TIMEOUT` (tiempo por turno).

## 5. Interfaz web

| Fichero | Qué hace |
|---|---|
| `front/src/app/core/services/poker.service.ts` | Dos WebSockets (cola y mesa), estado en signals, temporizadores de espera y de turno |
| `front/src/app/features/poker/poker.ts|html|scss` | La página `/poker`: lobby con niveles de apuesta y mesa con asientos, comunitarias, bote, acciones y resultado |
| `front/public/i18n/{es,en,fr}.json` | Textos del póker en los tres idiomas |
| `front/src/app/shared/components/header/header.html`, `features/home/home.html` | Enlaces en la navegación y en la portada |

Flujo del jugador: **/poker** → elegir ciegas → *Buscar partida* → (rival humano o, tras
el tiempo de espera, un bot) → mesa con tus cartas, las del rival boca abajo, las
comunitarias, el bote y los botones `Retirarse / Pasar / Igualar / Subir / All-in` →
resultado de la mano → siguiente mano automática → fin de partida cuando alguien se
queda sin fichas.

## 6. Integración con el resto del proyecto

Cuando termina una partida, el **servidor** escribe el resultado (`apps/poker/services.py`):

- humano contra humano → queda en el historial (`Game`) y **actualiza ELO y balance**;
- humano contra bot → queda en el historial pero **no puntúa**: ganar a bots no debe
  inflar el ranking.

### 6.1 Mesas de torneo

Un match del bracket se juega en una mesa real de este motor, no en el juego local:

1. `POST /api/tournament/<id>/matches/<match_id>/table/` (solo los dos participantes)
   crea la mesa con los dos jugadores del match —`apps/poker/tournament_tables.py`— y
   devuelve su id y la ruta del WebSocket. Es **idempotente**: los dos acaban en la
   misma mesa.
2. La mesa lleva `context={'tournament_id': …, 'match_id': …}` y **no reparte** hasta
   que los dos están sentados (así nadie pierde la ciega mientras el rival carga).
3. Cuando la partida termina, `_close_tournament_match` cierra el match **desde el
   servidor**: mapea el ganador por usuario (no por asiento), escribe los marcadores,
   elimina al perdedor del torneo y el bracket avanza. Nadie declara su propia
   victoria, así que no hay nada que confirmar ni que amañar.

En la web, el botón «Jugar» del bracket navega a `/poker?tournament=…&match=…` y esa
página entra directo a la mesa (sin cola ni bots) y muestra el panel de partida de
torneo mientras llega el rival.

## 6.2 Espectadores y chat de mesa

Cualquier usuario autenticado puede **mirar** una mesa: si no tiene asiento, la conexión a
`/ws/poker/table/<id>` se acepta en modo **espectador**.

- Recibe siempre la vista **sin asiento** (`you: null`): no ve ninguna carta ajena hasta el
  showdown, donde sí se revelan las de los jugadores que llegan al final.
- No puede actuar: el servidor rechaza cualquier acción con «no estás sentado en esta mesa».
- Las mesas vivas se listan en `GET /api/poker/tables/` y en el lobby hay un botón «Ver» que lleva
  a `/poker?table=<id>` (URL compartible).

**Chat de mesa**: mensajes efímeros por el mismo WebSocket, **sin base de datos**.

| Cliente → servidor | Servidor → clientes |
|---|---|
| `{"type":"chat","text":"…"}` | `{"type":"chat","from":"ana","text":"…","at":"17:55","spectator":false}` |

Lo ven jugadores y espectadores de esa mesa. Se recorta a 200 caracteres y hay un límite de
frecuencia por conexión (0,5 s) para que nadie inunde la mesa.

## 6.3 Historial de manos

Al terminar una partida se guardan sus manos (`apps/poker/models.py`):

- `PokerHandRecord`: nº de mano, tablero, bote, si hubo showdown y quién ganó;
- `PokerHandPlayer`: asiento, usuario (o bot), cartas **solo si se mostraron**, nombre de la jugada,
  fichas al acabar, cuánto ganó y si se retiró.

La mesa acumula el resumen que ya produce el motor (`PokerTable._hand_summary`) y se persiste junto
al resultado en `services._save_hands`, así que el motor sigue sin tocar la base de datos.

Se consulta por API —**solo el dueño de la partida**— y en la web:

| Endpoint | Devuelve |
|---|---|
| `GET /api/poker/history/` | Mis últimas 20 partidas (rival, resultado, fichas, nº de manos) |
| `GET /api/poker/history/<game_id>/` | Las manos de esa partida (403 si no es tuya) |
| `GET /api/poker/stats/` | Manos jugadas/ganadas, showdowns, bote mayor, retiradas y % de victoria |

Página web: **`/poker/history`** (enlazada desde el lobby del póker).

## 7. Despliegue

```bash
cp .env.example .env      # y rellena DJANGO_SECRET_KEY, JWT_SECRET_KEY, CORS...
docker compose up --build
# App en https://localhost:8443  (TLS autofirmado + WAF)
```

No hace falta tocar nginx: `docker/nginx-app.conf` ya reenvía `/api/` y `/ws/` al backend
con el handshake de `Upgrade`, y el WebSocket del póker viaja por ahí. En un servidor real
hay que ajustar en `.env`: `DJANGO_ALLOWED_HOSTS`, `CORS_ALLOWED_ORIGINS` y los puertos.
El frontend compila con `npm run build -- --configuration production` dentro del
`Dockerfile.frontend`, así que cualquier cambio en `front/` entra solo en la imagen.

## 8. Lo que falta

| Pendiente | Nota |
|---|---|
| Redis para la cola y el registro de mesas | Hoy viven en memoria del proceso, igual que el `InMemoryChannelLayer`: con una sola instancia de Daphne es correcto, con varias no |
| Reconexión con estado | El asiento se marca desconectado y la mesa le espera, pero conviene un mensaje `resume` explícito |
| Mesas de más de 2 jugadores | ✅ Hecho: cola por tamaño (`?size=N`), relleno con bots y UI con selector 2–6 |
| Inasistencia en un match de torneo | Si un jugador no entra, la mesa le espera sin límite; el creador puede cerrar el match a mano. Falta un tiempo máximo de espera |
| ELO en mesas de 3–6 | Una mesa con 3+ humanos no puntúa (el ELO del proyecto es 1v1); el resultado sí queda en el historial |
| Mesas de torneo en memoria | Igual que la cola: el registro de mesas vive en el proceso (una instancia de Daphne) |
