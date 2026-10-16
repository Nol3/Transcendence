# Añadir un juego

Todo lo que se juega vive bajo el apartado **Juegos** (`/games`). Lo que se ve ahí no
está escrito en la pantalla: sale del catálogo, así que añadir un juego no se hace
tocando el apartado, sino declarándolo.

## 1. Declararlo en el catálogo

`front/src/app/core/games/game-catalog.ts` — una entrada más en `GAME_CATALOG`:

```ts
{
  id: 'damas',                    // da las claves de traducción game.damas.*
  route: '/damas',
  mode: 'bots',                   // local | bots | online
  playersKey: 'games.players.two',
  icon: '⚪',                     // presentación: emoji, como en los logros del póker
  accent: 'green',                // cyan | pink | yellow | green
  tags: ['games.tag.board'],
  available: true,                // false = aparece como «próximamente», sin botón
}
```

## 2. Su ruta y su pantalla

En `front/src/app/app.routes.ts`, una ruta que apunte a un componente *standalone* en
`front/src/app/features/<juego>/`. Con `canActivate: [authGuard]` si necesita sesión.

## 3. Los textos

En `front/public/i18n/{es,en,fr}.json`: `game.<id>.name`, `game.<id>.desc` y
`game.<id>.how` (una línea de cómo se juega). `npm run i18n:check` falla si falta alguno
en algún idioma o si los `{{parámetros}}` no cuadran.

## 4. Si el juego es online

El servidor ya tiene las piezas; lo que hay que decidir es cuánta autoridad se le da:

- **Servidor autoritativo**: el patrón está en `backend/apps/poker/` (motor en
  `engine/`, la mesa en `tables.py`, el consumidor en `consumers.py`). El cliente manda
  intenciones y el servidor decide: es lo que evita que se pueda hacer trampa desde la
  consola del navegador.
- **Salas genéricas**: `ws/rooms/<room_id>` (`RoomConsumer`) y `ws/matchmaking`
  (`MatchmakingConsumer`) ya existen y no saben de póker.
- **Cola de emparejamiento**: `backend/apps/poker/queue.py` funciona con memoria o Redis
  (`MATCH_QUEUE_BACKEND`), que es lo que permite escalar a varias réplicas.
- **Torneos**: `backend/apps/tournament/` (llaves, mesas, confirmación de resultados).
- **Persistencia del historial**: `apps/poker/models.py` + `services._save_hands` es el
  modelo a copiar si el juego nuevo tiene que guardar partidas.

## Ejemplo hecho: el Culo (Presidente)

El **Culo** entró siguiendo exactamente estos pasos, así que sirve de referencia de cómo
queda un juego de verdad:

| Pieza | Dónde está |
|---|---|
| Catálogo | entrada `culo` en `core/games/game-catalog.ts` (`mode: 'bots'`) |
| Reglas | `core/games/culo/culo-engine.ts` — puro: recibe estado, devuelve estado |
| Baraja | `core/games/culo/culo-deck.ts` (40 cartas, 1 o 2 barajas, y el 5 de oros aparte) |
| Bots | `core/games/culo/culo-bots.ts` |
| Pantalla | `features/games/culo/` (ajustes, mesa, fin de ronda y el panel de reglas) |
| Arte | `public/cards/es/` — 40 PNG dibujados con `scripts/generar_baraja_espanola.py` |
| Pruebas | `culo-engine.spec.ts` (25, incluida una partida entera con bots) y `e2e/culo.spec.ts` |

Dos decisiones que merece la pena copiar:

- **El motor no sabe de la interfaz.** Las reglas son funciones puras, así que se prueban
  sin navegador y la mesa solo pinta el estado que le devuelven. Es lo que permitió
  detectar que «con una carta en la mesa solo se puede responder con una carta».
- **Lo que las normas dejan abierto, se decide y se dice.** Con 3 jugadores no hay
  Vicepresidente ni Viceculo (el segundo sería las dos cosas a la vez): se juega con
  Presidente, un neutro y Culo, y así aparece escrito en el propio panel de reglas.

## 5. Comprobaciones antes de darlo por hecho

```bash
cd front
npm test                                   # el catálogo se prueba solo (ids, rutas que existen)
npx playwright test e2e/games.spec.ts      # el apartado lista el juego y su botón lleva bien
npx playwright test e2e/a11y.spec.ts       # añade la ruta nueva a la lista de RUTAS
```

## Cómo está montado (para no romperlo)

- El **catálogo** (`core/games/game-catalog.ts`) es la única declaración. El apartado
  (`features/games/games-hub/`) solo pinta lo que hay ahí: un juego nuevo aparece sin
  tocar esa pantalla.
- `available: false` sirve para anunciar algo que todavía no se puede jugar: se ve
  apagado y sin botón. Es mejor que enseñar una pantalla a medias.
- Los tests del catálogo comprueban que cada `route` existe de verdad en
  `app.routes.ts`, así que un juego mal declarado no pasa el CI.
