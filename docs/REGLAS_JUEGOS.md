# Reglas de los juegos a integrar — Mentiroso, Tute, Brisca y Mus

Escrito el 14-10-2026 para poder **programarlos mañana sin volver a buscar nada**. Cada juego lleva:
las reglas tal y como las dice la fuente, **la variante que vamos a implementar** (porque estos
juegos cambian de pueblo a pueblo), y las notas de motor: estado, acciones, casos límite y qué
reutiliza del Culo.

Fuente principal: **Fournier**, el fabricante de la baraja española, que publica los reglamentos
(<https://www.nhfournier.es/como-jugar/>). Para el mentiroso, Wikipedia en español y las reglas de
Zacatrus. Todo lo que va entre corchetes con `[F]`/`[W]`/`[Z]` está tomado de esas fuentes.

> **El orden de las secciones NO es el orden de trabajo.** Aquí van por familias (primero los de
> bazas), pero se programan en otro orden: **Mentiroso → Brisca → Tute → Mus**. La tabla con el
> orden y los esfuerzos está al final del documento.

## Lo que comparten los cuatro (y ya está hecho)

Antes de las reglas, lo que **no** hay que volver a escribir, porque salió con el Culo:

| Pieza | Dónde vive | Se reutiliza tal cual |
|---|---|---|
| Salas con código de 4 caracteres | `backend/apps/culo/rooms.py` | Sí |
| WebSocket autoritativo (el servidor decide) | `backend/apps/culo/consumers.py` | Sí |
| Vista por jugador (solo tu mano) | `engine.state_for(state, seat)` | Sí |
| Reconexión (código en la URL, asiento guardado) | `culo-online.service.ts` + `Room.join` | Sí |
| Baraja española de 40 con PNG y orden de fuerza | `core/games/culo/culo-deck.ts` + `public/cards/es/` | Sí (ver aviso abajo) |
| Motor puro + bots + tests sin navegador | `culo-engine.ts`, `culo-bots.ts` | Sí, como patrón |
| Catálogo, i18n, accesibilidad, e2e | `game-catalog.ts`, `docs/JUEGOS.md` | Sí |

**Aviso sobre la baraja:** el orden de fuerza **cambia entre juegos**, así que no se toca el del
Culo. El Culo tiene `2<3<4<5<6<7<Sota<Caballo<Rey<As<5 de oros`; la brisca y el tute tienen
`2<4<5<6<7<Sota<Caballo<Rey<3<As` (¡el 3 va segundo!); y el mus no tiene orden de palos, solo valor
de puntos. Lo limpio es que cada juego tenga su propia tabla de orden, aunque compartan los PNG.

---

# 1. Brisca

**Fuente:** Fournier, <https://www.nhfournier.es/como-jugar/brisca/>

## Reglas [F]

- **Jugadores:** 2 o más; lo normal 2 o 4. A 4 se juega **por parejas** (cada uno frente a su
  compañero).
- **Baraja:** española de 40.
- **Orden de las cartas**, de mayor a menor: **as, tres, rey, caballo, sota, siete, seis, cinco,
  cuatro, dos**. Ojo: el tres es la segunda carta más alta, no la tercera.
- **Valor en puntos:** as 11 · tres 10 · rey 4 · caballo 3 · sota 2. El resto (7, 6, 5, 4, 2) vale 0.
- **Reparto:** 3 cartas a cada jugador y **se descubre la siguiente**, que marca el **triunfo**; esa
  carta queda a la vista junto al mazo en el centro.
- **Cómo se juega:** sale el jugador a la derecha del que reparte (el «mano») con una carta
  cualquiera. Los demás juegan una carta cualquiera: **no hay obligación de asistir al palo ni de
  jugar triunfo**.
- **Gana la baza** la carta más alta del palo de triunfo; si no hay triunfo, la más alta del palo de
  salida.
- El que gana la baza **roba primero** (una carta del mazo) y **sale** en la siguiente.
- **Cambio del triunfo:** quien gana una baza, antes de robar, puede cambiar la carta que marca el
  triunfo por el **siete** del mismo palo (y el siete por el **dos** de triunfo). No se puede hacer
  después de jugar la penúltima baza.
- **Final:** cuando no quedan cartas que robar y se han jugado las de la mano.
- **Tanteo:** cada jugador o pareja suma el valor de las cartas de sus bazas. **Si hay empate a 60
  tantos, ese juego se anula.**
- **Señas** (solo a 4, entre compañeros): as de triunfo = alzar los ojos; tres de triunfo = guiñar un
  ojo; rey = extender los labios; caballo = torcer los labios a la derecha; sota = sacar la lengua;
  briscas (ases y treses de otro palo) = torcer la cabeza; sin triunfo = cerrar los ojos un momento.

## Variante que vamos a implementar

- **Fase 1: 2 jugadores**, individual. Es la que más se juega y la más simple (sin parejas ni señas).
- **Fase 2: 4 jugadores por parejas**, con el tanteo común y **sin señas** (en la web las señas no
  tienen sentido; se documenta y se juega «limpio»). Se elige pareja por sorteo o por orden.
- Partida a **un número pactado de juegos** (por defecto 3, que es lo normal para una partida corta).

## Notas de motor

- **Estado:** `deck` (mazo restante), `trumpCard` (la que pinta), `trumpSuit`, `hands[4]`,
  `trick` (cartas jugadas + quién), `turn`, `tricksWon[4]` (cartas capturadas), `dealer`,
  `phase: 'playing' | 'game-end' | 'match-end'`, `scores[4]`, `gamesWon[4]`.
- **Acciones del jugador:** `play(cardId)`, y `swap_trump` (el cambio del siete) antes de robar.
- **Casos límite a cubrir con test:**
  1. No hay obligación de asistir: jugar un palo distinto es legal siempre.
  2. La baza la gana el triunfo más alto, aunque haya salido otro palo.
  3. Empate a 60 → juego anulado (no cuenta para nadie).
  4. El cambio del triunfo: solo tras ganar baza, antes de robar, y nunca tras la penúltima baza.
  5. El que gana la baza roba primero (importa: se queda con la mejor carta).
- **Bot:** heurística sencilla y creíble — si puedo ganar la baza con una carta que no valga puntos,
  la gano; si no, suelto la carta de menos valor; guarda ases y treses para bazas ganables.

---

# 2. Tute

**Fuente:** Fournier, <https://www.nhfournier.es/como-jugar/tute/>

## Reglas [F]

- **Jugadores:** de 2 a 4 según la modalidad.
- **Baraja:** española de 40.
- **Orden y valor:** los mismos que la brisca (as, tres, rey, caballo, sota, siete…; as 11, tres 10,
  rey 4, caballo 3, sota 2; las demás, «cartas blancas», 0 tantos).
- **Objetivo:** llegar a **101 tantos** sumando las bazas ganadas, **o** hacer un **tute** (reunir
  los cuatro reyes o los cuatro caballos), que gana el juego al instante.
- **Reparto (2 jugadores):** 8 cartas cada uno y se descubre la siguiente, que marca el triunfo; el
  resto queda debajo («baceta»).
- **Obligaciones, y aquí está la gracia del tute:**
  - Mientras queden cartas en la baceta: **solo es obligatorio asistir al palo de triunfo**, sin
    necesidad de montar.
  - Terminada la baceta: **obligatorio asistir, montar y fallar** (si no puedes asistir, juegas
    triunfo).
- El que gana la baza roba primero y sale en la siguiente.
- **Cambio del triunfo:** la carta que pinta se puede cambiar por el **siete** del mismo palo (si es
  as, tres o figura) o por el **dos** (si es carta blanca). Se deja debajo y **no se puede tomar
  hasta ganar una baza**.
- **Acuses (cantos):** rey + caballo del mismo palo en la mano. Vale **40 tantos** si son del palo de
  triunfo («las cuarenta») y **20** si son de otro («las veinte»). **Solo se pueden cantar después de
  ganar una baza, y uno por baza.**
- **Diez últimas:** ganar la **última baza** vale 10 tantos (y decide los empates).
- **Capote** (a 2): ganar las ocho bazas que quedan tras terminar la baceta, cantándolo antes; si el
  rival gana alguna de esas 8, gana el rival.
- **Tute a 3 jugadores** («tute arrastrado»): reparte uno que no juega, 13 cartas a cada uno.
  Obligatorio asistir, montar, fallar y **pisar**; se permite el contrafallo cuando no se puede
  pisar; hay que cantar las cuarenta antes que las veinte.
- **Tute a 4 jugadores:** dos parejas frente a frente, 10 cartas a cada uno. En cada baza pueden
  cantar los dos compañeros, un acuse cada uno.

## Variante que vamos a implementar

- **Tute de 4 por parejas** (10 cartas, parejas, un acuse por compañero y baza) — es el más vistoso
  para una mesa de amigos y reutiliza la vista por jugador.
- Como segunda opción, **tute a 2** (8 cartas, con baceta y capote), que es el que más se juega de
  verdad.
- **Se implementa con cantos** (las cuarenta / las veinte) porque son parte de la estrategia; los
  empates se resuelven con las diez últimas.

## Notas de motor

- **Estado:** como la brisca + `melds` (acuses cantados por jugador), `pendingAcuse` (acuses en mano
  sin cantar), `baceta` (cartas restantes), `mustFollow` (bool: si ya se acabó la baceta),
  `tantos[4]`, `capoteCantado`.
- **Acciones:** `play(cardId)`, `cantar_acuse(suit)`, `cantar_capote`, `swap_trump`.
- **Casos límite:**
  1. La obligación de asistir **solo aplica al triunfo** mientras hay baceta; después, asistir/montar/fallar.
  2. No se puede cantar un acuse antes de ganar una baza, ni dos en la misma baza (a 4, uno por
     compañero).
  3. Tute de reyes/caballos: gana al instante, sin sumar.
  4. Las diez últimas deciden el empate a tantos.
  5. «Pisar» y contrafallo en el modo de 3.
- **Bot:** valora si la baza es «de puntos» (con ases/treses) y la pelea; canta los acuses en cuanto
  gana una baza; guarda triunfos para fallar.

---

# 3. Mus

**Fuente:** Fournier, <https://www.nhfournier.es/como-jugar/mus/>, contrastado con
<https://cccj.es/reglaments/mus.htm>, <https://mus.las40.es/rules/> y
<https://www.usujuegos.com/juego_usumus1.aspx>.

## Reglas [F]

- **Jugadores:** lo canónico es **4, en dos parejas**, cada uno frente a su compañero. Hay variantes
  de 2, 3 y 6 (en 6, dos campos de tres), pero la que se juega es la de 4.
- **Baraja:** española de 40. **Sin triunfo y sin distinción de palos.**
- **Orden de las cartas**, de mayor a menor: **rey o tres, caballo, sota, siete, seis, cinco,
  cuatro, dos o as.** Es decir: el **3 vale lo mismo que el rey** y el **2 lo mismo que el as** (se
  juega «con 8 reyes y 8 ases»).
- **Valor en puntos:** rey, tres, caballo y sota valen **10**; las demás, su número; **2 y as valen 1**.
- **Reparto:** 4 cartas a cada jugador.
- **Fase de mus:** empezando por el «mano», cada uno dice **«mus»** (quiere descartar y robar) o
  **«no hay mus»** (corta). En cuanto uno corta, **nadie más descarta** y se pasa a las apuestas. En
  la primera mano de cada juego, para pedir mus se coge la baraja y se pone a un lado.
- **Los cuatro lances**, en este orden fijo:
  1. **Grande**: la carta más alta (bajo la regla de los 8 reyes).
  2. **Chica**: la más baja.
  3. **Pares**: duples (dos parejas o cuatro iguales) > medias (tres iguales) > pareja. A igualdad,
     gana la carta más alta.
  4. **Juego**: sumar 31 o más. El orden de mejor a peor: **31** (la una), 32, 40, 37, 36, 35, 34, 33.
     Si **nadie** tiene juego, se juega al **punto** (gana el que más se acerque a 30).
- **Apuestas** en cada lance: `paso`, `envido` (mínimo 2 piedras), `quiero`, `no quiero`, `envido
  más` (subir) y **`órdago`** (la partida entera). Si se rechaza un envite, quien lo hizo se lleva 1
  piedra. En las parejas, prevalece la apuesta más alta de los dos miembros.
- **Tanteo** (en el orden grande → chica → pares → juego): piedras envidados + lo que valga la
  jugada: en pares, 1 por pareja / 2 por medias / 3 por duples; en juego, 2 si es distinto de 31 y 3
  si es 31; en punto, 1 extra.
- **Final:** gana el **juego** la pareja que llega a **40 piedras** (o 30, según se pacte). Una
  **vaca** es al mejor de 3 juegos y la partida al mejor de 3 vacas (o una sola, para que no se haga
  eterno).
- **Señas:** gestos permitidos entre compañeros, con significado fijo y obligación de decir la
  verdad: dos reyes = morder el labio; dos ases = sacar la lengua; medias = torcer los labios;
  duples = levantar las cejas; 31 = guiñar un ojo; 30 al punto = levantar los hombros; ciego (ni
  pares ni juego) = cerrar los ojos; juego distinto de 31 = beso. **Está prohibido preguntar por
  señas.**

## Variante que vamos a implementar

- **Mus de 4 por parejas**, con la regla de los **8 reyes** (la estándar) y **partida corta**: una
  vaca al mejor de 3 juegos, a 40 piedras.
- **Las señas: fase 2.** Es lo único que no se puede copiar de la mesa real. Dos opciones, y hay que
  elegir una antes de programarlas:
  - (a) **Botones de seña** en la UI: cada jugador tiene la fila de señas y pulsa la que le toca;
    solo su compañero la ve. Es lo más fiel y lo más fácil de implementar y de testear.
  - (b) **Sin señas** (mus «corrido y sin señas»): más simple, pero pierde la esencia del juego.
  - Mi recomendación: (a), y que el servidor **verifique** que la seña es verdad (el servidor sabe
    las cartas, así que puede rechazar una seña falsa; es justo el tipo de regla que el servidor
    autoritativo hace bien).

## Notas de motor

- **Estado:** `hands[4]`, `mano` (quién habla primero), `postre`, `phase: 'mus' | 'lances' | 'reveal'
  | 'tanteo' | 'game-end'`, `discards` (lo descartado en el mus), `lance` (cuál de los cuatro),
  `bets` (apuesta viva, quién la hizo, cuánto), `piedras[2]`, `juegos[2]`, `vacas[2]`,
  `senasPasadas` (por jugador).
- **Acciones:** `mus`, `cortar_mus`, `descartar(cardIds)`, `envidar(n)`, `quiero`, `no_quiero`,
  `envido_mas(n)`, `ordago`, `pasar`, `pasar_sena(tipo)`.
- **Casos límite (los que dan miedo y hay que testear uno a uno):**
  1. **El mus solo se corta una vez**: en cuanto alguien dice «no hay mus», se cierra el descarte
     para todos, incluso para los que aún no habían hablado.
  2. **Orden de las apuestas por parejas**: habla el mano, luego su compañero puede decir «hasta mi
     compañero»; prevalece la apuesta más alta.
  3. **Pares y juego: primero se declara** (tengo / no tengo) y no se puede mentir; si nadie tiene,
     no hay envites.
  4. **Orden del tanteo**: grande → chica → pares → juego. Importa, porque una pareja puede llegar a
     las 40 piedras a mitad del recuento y ahí se acaba.
  5. **La regla de los 8 reyes** solo aplica a grande, chica y pares; en juego/punto el 3 y el 2
     valen su valor natural.
  6. **El 38 y el 39 son imposibles** sin ochos ni nueves: el orden es 31, 32, 40, 37, 36, 35, 34, 33.
  7. **Órdago aceptado** resuelve la vaca al instante.
  8. **Seña falsa**: el servidor la rechaza (si se implementan señas).
- **Bot:** el mus es el que pide un bot más listo de los cuatro. Con evaluar los cuatro lances y
  apostar solo cuando la jugada es buena basta para que no desentone; las señas no las necesita.

---

# 4. Mentiroso

**Fuentes:** Wikipedia en español (<https://es.wikipedia.org/wiki/Mentiroso_(juego_de_naipes)>),
reglas de Zacatrus (<https://zacatrus.es/juego-cartas-mentiroso.html>) y Barrilito.

## Reglas [W][Z]

- **Jugadores:** de 2 a 5 según Wikipedia, hasta 10 en otras versiones. Con 3–5 es donde mejor
  funciona.
- **Baraja:** española de 40. **Se reparten todas las cartas** entre los jugadores.
- **Objetivo:** **quedarse sin cartas** el primero.
- **Cómo se juega:**
  1. El jugador inicial pone **boca abajo** una o varias cartas en el centro y **anuncia qué son**.
     Puede decir la verdad o mentir sobre el valor, pero **no sobre la cantidad** [Z].
  2. El siguiente, a su derecha, **cree** y sigue depositando cartas diciendo cuántas pone (mismo
     número, no necesariamente la misma cantidad de cartas) [W], o **desconfía**.
  3. **Cualquier jugador**, no solo el siguiente, puede decir **«¡mentiroso!»** y levantar las cartas.
     - Si era **cierto** (no mintió): el que desconfió se lleva **todas** las cartas del montón.
     - Si era **mentira**: el que las puso se las lleva todas.
  4. El que se lleva el montón **empieza la ronda siguiente**, y **no se puede repetir el palo** de la
     jugada anterior [W].
- **Variante española preferida:** cuando alguien reúne **las cuatro cartas de un mismo número**,
  puede **retirarlas** del juego mostrándolas a los demás.
- Una vez que un jugador se queda sin cartas, **no se le puede desconfiar**; debe enseñar las
  restantes si se lo piden.
- Gana quien se queda sin cartas antes. La última persona con cartas pierde.

## Variante que vamos a implementar

- **De 3 a 6 jugadores**, con la regla de retirar los cuatro iguales (es la variante española y da
  una salida clara a las manos imposibles).
- **Se juega por número, no por palo** (la versión de Zacatrus), que es la más simple de explicar.
- **Partida a manos ganadoras** pactadas (por defecto, 3), para que la mesa no dure eterna.

## Notas de motor

- **Estado:** `hands[6]`, `pile` (cartas del centro, boca abajo), `claimedRank` (lo último anunciado),
  `turn`, `lastPlayer`, `lastCount`, `mustChangeSuit` (bool), `scores[6]`, `phase`.
- **Acciones:** `play(cardIds, claimedRank)`, `desconfiar()`.
- **Particularidad (y ventaja de este juego):** el servidor **sí sabe** las cartas reales, así que
  puede resolver la desconfianza sin trampa posible. La vista por jugador solo manda tu mano, así que
  el farol funciona igual que en la mesa.
- **Casos límite:**
  1. **No se puede mentir en la cantidad**, solo en el valor: validarlo en el servidor.
  2. Desconfiar es cosa de **cualquiera**, no solo del siguiente, y **para la ronda** hasta que se
     resuelve.
  3. El que se lleva el montón empieza y **cambia de palo**.
  4. **Retirar los cuatro iguales** (mostrándolos) antes de seguir jugando.
  5. A quien se queda sin cartas **no se le puede desconfiar**.
  6. Si alguien se queda sin cartas, gana la mano al instante (no sigue la ronda).
- **Bot:** casi trivial y muy divertido — juega la verdad cuando tiene cartas del número anunciado y
  miente con la carta que menos le sirva; desconfía cuando el anuncio es imposible por lo que ya se
  jugó o cuando el jugador lleva muchas cartas del mismo número.

---

# Orden de trabajo y esfuerzo

| # | Juego | Jugadores | Motor | Esfuerzo | Por qué en este orden |
|---|---|---|---|---|---|
| 1 | **Mentiroso** | 3–6 | Muy simple | **6–8 h** | Motor casi nulo, no hay que evaluar bazas ni combinaciones, y el farol ya lo resuelve el servidor. El más rápido de ver funcionando online. |
| 2 | **Brisca** | 2 (y 4) | Medio | **10–14 h** | El juego de bazas más popular y el más fácil de los tres de bazas: sin obligación de asistir y sin cantos. Con el modo de 2 ya se juega. |
| 3 | **Tute** | 4 (y 2) | Medio-alto | **14–18 h** | Comparte motor de bazas con la brisca, pero añade obligaciones (asistir/montar/fallar), baceta, acuses y las diez últimas. |
| 4 | **Mus** | 4 (parejas) | Alto | **25–35 h** | Cuatro lances con apuestas, jerarquía de pares, orden de tanteo, parejas y (fase 2) las señas. Es el que más se ve, pero el que más trabajo tiene. |

**Sugerencia de orden:** Mentiroso → Brisca → Tute → Mus. Los dos de bazas se programan uno detrás
del otro aprovechando el mismo evaluador de bazas, y el mus se deja para el final, cuando el patrón
de sala y mesa ya esté rodado con tres juegos más.

**Un detalle que ahorra tiempo:** el **evaluador de bazas** (qué carta gana, con triunfo y palo de
salida) se escribe una vez y lo comparten **brisca y tute**. El mus **no lo usa**: no tiene bazas, es
de lances y apuestas. Va como módulo aparte (`core/games/bazas.ts`), probado por su cuenta.

## Fuentes

- Fournier, reglamentos oficiales: **brisca** <https://www.nhfournier.es/como-jugar/brisca/> ·
  **tute** <https://www.nhfournier.es/como-jugar/tute/> · **mus**
  <https://www.nhfournier.es/como-jugar/mus/> · índice completo
  <https://www.nhfournier.es/como-jugar/>
- Mus, reglas detalladas: <https://cccj.es/reglaments/mus.htm> · <https://mus.las40.es/rules/> ·
  <https://www.usujuegos.com/juego_usumus1.aspx> · reglamento de colectividades vascas
  <https://euskadimus.eus/wp-content/uploads/2026/04/REGLAMENTO.docx.pdf>
- Mentiroso: <https://es.wikipedia.org/wiki/Mentiroso_(juego_de_naipes)> ·
  <https://zacatrus.es/juego-cartas-mentiroso.html> · <https://barrilito.com.mx/baraja>
- Catálogo general (de dónde salieron estos cuatro): `docs/INVESTIGACION_JUEGOS.md`
