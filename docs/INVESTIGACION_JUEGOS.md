# Juegos de cartas para añadir a la web — investigación

Fecha: 14-10-2026. Pregunta: **qué otros juegos de cartas populares en España tienen sentido en este
proyecto**, y en qué orden meterlos.

## Cómo he mirado cada juego

No vale solo con que sea popular: tiene que encajar en lo que ya hay. Los criterios, por orden de
importancia para este proyecto:

| Criterio | Por qué importa aquí |
|---|---|
| **Turnos claros** | El servidor es autoritativo y las reglas son funciones puras (como el motor del Culo). Un juego de reflejos o de tiempo real no encaja. |
| **Información oculta manejable** | El servidor decide qué ve cada uno (el Culo ya lo hace: cada conexión recibe solo su mano). Un juego con mucha información compartida secreta (p. ej. mesa con cartas boca abajo de todos) complica la vista por jugador. |
| **2–6 jugadores** | Es lo que ya soportan las salas con código (`MAX_JUGADORES = 6`) y lo que de verdad se juega con amigos. |
| **Baraja española de 40** | Ya están los **40 PNG** generados y el orden de fuerza resuelto (`5 de oros` aparte). La baraja francesa también está (póker, cartas Balatro). |
| **Se puede escribir un bot decente** | Sin bots no se puede jugar solo ni llenar una mesa a medias, y en este proyecto los bots ya son un patrón (`culo-bots.ts`). |
| **Una partida no eterna** | Para una demo web, 5–15 minutos por ronda. El mus con vacas puede irse muy largo si no se acota. |

## Los candidatos

Clasificados por familia. La columna **encaje** es mi valoración para *este* proyecto (🟢 fácil,
🟡 medio, 🔴 mucho trabajo), no una valoración del juego.

### Bazas (el grupo más español: se juega una carta, gana la mejor)

| Juego | Jugadores | Baraja | Equipos | Encaje | Notas |
|---|---|---|---|---|---|
| **Brisca** | 2–6 (lo normal 2 o 4) | 40 | No / sí a 4 | 🟢 | El juego de bazas más popular en España. Hay un triunfo (la carta que se levanta) y se suman puntos: As 11, 3 diez, Rey 4, Caballo 3, Sota 2. Reglas cortas, bot fácil. |
| **Tute** | 2–4 | 40 | No | 🟡 | 8 cartas por jugador; además de ganar bazas hay **cantos** (las cuarenta = rey+caballo del triunfo). Variantes: subastado, cabrero, arrastrao. |
| **Guiñote** | 2–4 | 40 | No | 🟡 | El tute de Aragón. Mismas ideas, otro nombre y detalles locales. |
| **Butifarra** | 4 | 40 | Sí (parejas) | 🟡 | El juego de cartas más popular en Cataluña. Con parejas, hace falta vista por jugador y un compañero que «ve» lo que puede. |
| **Truc / Truco** | 2 o 4 (parejas) | 40 | Sí | 🟡 | Muy de la Comunitat Valenciana. Añade **envites** (apuestas dentro de la mano) y señas al compañero: es medio juego de farol. |
| **Envite canario** | 2–4 | 40 | No | 🟡 | En el catálogo de Fournier. Como el tute/brisca con envites. |
| **Julepe** | 2–5 | 40 | No | 🟡 | Bazas con apuestas y un «julepe» que dobla. Interesante por el sistema de apuestas. |
| **Tresillo** | 3 | 40 | No | 🟢 | Brisca para tres, con palos de triunfo que cambian. Ideal como «modo de 3» de la Brisca. |
| **Mus** | **4 exactos** | 40 | Sí (parejas) | 🔴 | El más identificado con España (País Vasco), y el más rico estratégicamente. Pero es el más caro de hacer: cuatro lances de apuestas (grande, chica, pares, juego), jerarquía de pares/duples, y las **señas**, que son gestos de cara que habría que convertir en una UI. Además son 4 jugadores exactos. |
| **Belote** | 4 | 32 (francesa) | Sí | 🟡 | En el catálogo de Fournier. Requiere baraja francesa de 32 (sí tenemos francesa, pero no de 32). |

### Recogida / pesca (se cogen cartas de la mesa)

| Juego | Jugadores | Baraja | Encaje | Notas |
|---|---|---|---|---|
| **Escoba** | 2–4 | 40 | 🟢 | Se cogen cartas de la mesa que sumen **15**; el 7 de oros y la escoba (dejar la mesa vacía) dan puntos. Reglas muy cortas y bot sencillo. |
| **Chinchón** | 2–8 | 40 | 🟡 | El «juego de familia». 7 cartas, se hacen grupos de 3+ (mismo valor o escalera); el chinchón (7 seguidas) cierra la ronda. Más estado que la escoba (las combinaciones). |
| **Pocha / Remigio** | 2–8 | 40 | 🟡 | Familia del rummy (combinar 10 cartas en grupos de 3+). Fournier tiene reglamento de los dos. |
| **Canasta / Continental / Samba / Gin Rummy** | 2–6 (canasta, por parejas) | 40 / francesa | 🟡 | Misma familia; la Canasta se juega mucho por parejas. |
| **Los seises** | 4–8 | 40 | 🟢 | Muy sencillo: deshacerse de las cartas formando escalera desde el 6. Mucho azar, poco motor. |
| **Cinquillo** | 2–6 | 40 | 🟢 | Empezar por el **5 de oros** y encadenar los valores contiguos de cada palo. Es el más fácil de todos y engancha. |

### Descarte y farol

| Juego | Jugadores | Baraja | Encaje | Notas |
|---|---|---|---|---|
| **Mentiroso** | 2–10 | 40 | 🟢 | Se descartan cartas boca abajo diciendo qué son, y se puede gritar «¡mentiroso!». Muy poco motor, mucha diversión, y el servidor ya sabe ocultar manos. |
| **Burro / Cuadrado** | 3+ / 4 (parejas) | 40 | 🟢 | Reunir cuatro cartas iguales. El cuadrado añade señas a la pareja. Para jugar con niños. |
| **Chúpate dos** | 2–4 | 40 | 🟢 | Tipo UNO con baraja española (el 2 hace robar dos, la sota salta, el rey cambia de palo). |
| **El Tomate / El Pumba** | — | 40 | 🟡 | Ambos en el catálogo de Fournier; no los he mirado a fondo. |
| **Culo / Presidente** | 3–6 | 40 | ✅ | **Ya está hecho**, local y online. |

### Banco y apuestas

| Juego | Jugadores | Baraja | Encaje | Notas |
|---|---|---|---|---|
| **Siete y media** | 2–6 | 40 | 🟢 | Sota, caballo y rey valen medio punto; el resto su número; gana quien más se acerque a **7,5** sin pasarse. Una sola decisión por turno (pedir o plantarse): es el más rápido de programar de toda la lista. |
| **Punto banca** | 2+ | 40 | 🟢 | Está en Fournier; versión española del bacarrá. |
| **Póker / Texas Hold'em** | 2–9 | 52 | ✅ | **Ya está hecho**, con ELO y torneos. |

## Qué recomiendo, y en qué orden

**Tanda 1 — los baratos que enganchan (cada uno, un motor pequeño y una mesa nueva):**

1. **Cinquillo** — reglas de 10 líneas, usa el 5 de oros que ya tenemos resuelto, hasta 6 jugadores.
   Es el más rápido de tener funcionando y online.
2. **Siete y media** — una decisión por turno; sirve para lucir el sistema de rondas y el banco que
   rota. También es el más fácil de cubrir con tests.
3. **Brisca** — el juego de bazas más popular de España; con el **Tresillo** como modo de 3 y las
   parejas como modo de 4, cubre mucha gente con un solo motor.
4. **Mentiroso** — motor casi nulo y mucho pico; el farol ya lo resuelve el servidor (cada uno ve
   solo su mano).

**Tanda 2 — los clásicos de mesa:**

5. **Escoba** — reglas cortas, bot fácil, y es de los que más se juegan en familia.
6. **Chinchón** — el rey de las sobremesas; más trabajo por las combinaciones, pero vale la pena.
7. **Tute** (con el **Guiñote** como variante de nombre y las cuarenta como canto).

**Tanda 3 — los ambiciosos:**

8. **Mus** — es *el* juego español y quedaría espectacular, pero es el más caro: apuestas en cuatro
   lances, jerarquía de pares/duples/medias y las señas (que en la web habría que resolver con
   botones de «seña» o con una fila de gestos, y decidir si se permiten). Son 4 jugadores exactos,
   así que siempre serían parejas. Lo dejaría para el final, cuando el resto esté rodado.
9. **Truc / Butifarra / Julepe** — bazas con envites y parejas; interesantes, pero cada uno es casi
   un juego nuevo.

## Lo que ya está resuelto y se reutiliza

Meter un juego nuevo hoy es: **una entrada en `game-catalog.ts` + una ruta + un motor puro + una
mesa**. Lo demás ya está:

- **Salas con código y WebSocket autoritativo** (el del Culo): entrar, lobby, repartir, reaccionar
  sin recargar. La capa de sala es genérica; solo hay que darle un motor por juego.
- **Vista por jugador**: el servidor manda a cada conexión **solo su mano** (y el número de cartas de
  los demás). Cualquier juego con información oculta lo hereda.
- **Baraja española completa**: 40 PNG, orden de fuerza, y el detalle del 5 de oros.
- **Bots**: patrón ya probado, para poder jugar solo o completar mesa.
- **Reconexión**: el código queda en la URL, así que recargar no te saca de la partida.
- **i18n, accesibilidad, PWA y e2e**: cada juego entra en el mismo molde (y en la auditoría de axe).

## Fuentes

- **Fournier** (fabricante de la baraja española), índice de reglamentos de más de 35 juegos — la
  referencia de primera mano: <https://www.nhfournier.es/como-jugar/> (mus, tute, brisca, chinchón,
  escoba, pocha, remigio, julepe, truc, truco, guiñote, butifarra, envite canario, tresillo, manilla,
  canasta, continental, samba, gin rummy, seises, tomate, pumba, punto banca, belote, pináculo…).
- **Reglas del mus** (juego, pares, señas, vacas): <https://cccj.es/reglaments/mus.htm>,
  <https://mus.las40.es/rules/>, <https://www.usujuegos.com/juego_usumus1.aspx> y el reglamento de
  colectividades vascas: <https://euskadimus.eus/wp-content/uploads/2026/04/REGLAMENTO.docx.pdf>.
- **Cómo jugar al mus** (resumen de jugadores y baraja): <https://www.elespanol.com/como/jugar-mus-reglas-senas/424958271_0.html>
- **12 juegos de cartas españolas fáciles** (mentiroso, burro, cinquillo, cuadrado, seises, siete y
  media, chúpate dos, tute, escoba, brisca, chinchón, solitario): <https://www.uncomo.com/ocio/articulo/juegos-de-cartas-espanolas-faciles-50935.html>
- **Brisca en Fournier** (2–6 jugadores, individual o parejas): <https://www.nhfournier.es/como-jugar/brisca/>
- **Ludoteka** (remigio, butifarra, comemierda/Presidente): <https://ludoteka.com>
- **Juegos tradicionales en familia** (relojito, las parejas, el burro): <https://www.sortirambnens.com/es/actividades/que-hacemos-en-casa/juegos-para-ninos/juegos-de-mesa-familiares/los-mejores-juegos-de-cartas-tradicionales-para-jugar-en-familia/>
- **Juegos de cartas para niños** (va de farol, las parejas, el cuadrado): <https://guiainfantil.com/articulos/ocio/juegos/juegos-con-cartas-para-los-ninos>

> Nota de honestidad: el número de jugadores de **Guiñote**, **Butifarra**, **Truc**, **Envite
> canario**, **Julepe** y **Tresillo** lo he puesto por lo que dicen los reglamentos de Fournier y las
> fuentes de bazas, no comprobando cada uno de ellos uno a uno. Antes de programar uno, se lee su
> reglamento entero y se acota la variante (que en los juegos de bazas españoles cambia de pueblo a
> pueblo).
