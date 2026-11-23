# Inspiración para el póker: qué copiar de las mejores mesas (y qué no)

Fecha: 23-11-2026. Documento de producto, no de código. Recoge una investigación sobre
plataformas de póker reales y free-to-play (PokerStars, GGPoker, 888poker, WPT Global, WSOP.com,
ClubGG, PokerBros) y sobre juegos de cartas/mesa web (Board Game Arena, Colonist.io, Chess.com,
Zynga Poker, Governor of Poker 3, Balatro, Marvel Snap, Duolingo, Discord).

**Método y honestidad**: lo que va con URL son prácticas descritas en fuentes públicas de cada
producto; lo que no la lleva es una recomendación propia para este proyecto. Los enlaces están al
final y se comprobaron el 23-11-2026. Las cifras de negocio (usuarios, retención) se omiten porque
no son verificables y no cambian la decisión.

---

## 1. Punto de partida: qué tiene ya el proyecto

Antes de proponer nada, esto **ya está hecho** y no hace falta copiarlo:

- Lobby con cola, ciegas (micro/low/mid), tamaño de mesa y temas de tapete.
- Mesa con reloj de turno, slider de subida, presets de bote, all-in, chat efímero y espectadores.
- Historial de manos con **replay** calle a calle, logros y ELO/leaderboard.
- Torneos con bracket, PWA, tres idiomas (ES/EN/FR), bots y tests de accesibilidad/móvil.

La investigación se centra, por tanto, en lo que **no** está: primera partida sin fricción,
aviso de turno, retención diaria, juego entre amigos y lectura de la decisión (cuota, análisis).

---

## 2. Los diez patrones que merecen la pena

| Patrón | Quién lo hace bien | Por qué funciona | ¿Aplicable aquí? |
|---|---|---|---|
| **Quick Seat**: elegir juego y nivel, y sentarte sin configurar nada | PokerStars | Elimina la parálisis de filtros; la primera carta llega en segundos | Sí, alto: la cola ya existe |
| **Aviso de turno**: sonido + ventana que emerge | 888poker, GGPoker | En una mesa con reloj, si no miras, pierdes la mano | Sí, barato |
| **Presets de apuesta**: ⅓, ½, ¾, bote, all-in | GGPoker, PokerStars | Decidir el tamaño es la mitad del póker; el slider solo es lento en móvil | Sí, ya aplicado |
| **Cuota del bote visible al igualar** | Estándar en clientes modernos; GG lo lleva al extremo con Smart Betting | Convierte «igualar 40» en «necesito 25 % de equity» | Sí, ya aplicado |
| **Time bank / reloj claro** | GGPoker | El tiempo es información: saber cuánto queda cambia la decisión | Parcial: hay cuenta atrás, falta barra visual |
| **Rabbit hunt**: ver la carta que no llegó | GGPoker, WPT Global | Cero impacto en la partida y mucha conversación después | Sí, medio |
| **Misiones diarias y racha de login** | PokerStars (misiones), PokerBros (racha) | Dan una razón para volver mañana sin dinero real | Sí, medio |
| **Escuela con quiz** | PokerStars Learn | El jugador nuevo no se va por perder, se va por no entender | Sí, medio |
| **Clubs privados con código** | ClubGG, PokerStars Home Games | Jugar con amigos es el modo natural de estas cartas | Sí, alto |
| **Revisión post-mano** | Chess.com (Game Review), WPT (QuintAce) | Convierte cada mano en una lección; es el mayor diferenciador posible | Sí, alto esfuerzo |

---

## 3. Prioridades para este proyecto

Ordenadas por impacto/esfuerzo. «Hecho» significa que ya va en esta tanda; el resto es backlog
para el `ROADMAP.md`, no una promesa.

### P1 · Esta semana (barato y muy visible)

| # | Idea | Inspiración | Estado |
|---|---|---|---|
| 1 | Presets de subida **⅓ y ¾ del bote** junto a ½, bote y 2× | GGPoker | **Hecho** |
| 2 | **Cuota del bote** junto al botón de igualar (40 → 25 %) | Clientes modernos / GG Smart Betting | **Hecho** |
| 3 | **Sonido de fichas cuando pasa el turno a tu asiento** | 888poker / GGPoker | **Hecho** |
| 4 | **Quick Seat real**: botón «Jugar ahora» que usa la última configuración y entra a la cola sin pasar por ajustes | PokerStars | Propuesto |
| 5 | **Revancha** en el popup de fin de partida (misma mesa, mismos ajustes) | Chess.com | Propuesto |
| 6 | **Barra visual de tiempo** además del número (se agota en color) | GGPoker time bank | Propuesto |
| 7 | **Emotes predefinidos** (sin chat libre) para mesa rápida y menos moderación | Governor of Poker 3 | Propuesto |
| 8 | **Compartir resultado** como tarjeta arcade (mano, bote, ganancia) | Zynga / Discord | Propuesto |
| 9 | **«Escapaste»** al retirarse, en vez de «te retiras» en rojo | Marvel Snap | Propuesto |
| 10 | **Ajuste de velocidad/reducir movimiento** en la mesa | Balatro | Propuesto |

### P2 · Este mes (estructura de retención)

| # | Idea | Inspiración |
|---|---|---|
| 11 | **Racha de login** con bonus creciente de fichas virtuales (100 → …), sin cofres que caduquen | PokerBros |
| 12 | **Misión diaria opt-in** («gana 2 manos», «juega una mano con escalera») → fichas/cosméticos | PokerStars |
| 13 | **Rueda diaria** de cosméticos (tapete, dorso, avatar) | PokerStars / PokerBros |
| 14 | **Temporadas ranked de 3 meses** con 10 partidas de colocación y soft reset | Colonist.io |
| 15 | **Clubs privados con código de 6 cifras** y reglas por sala | ClubGG / Home Games |
| 16 | **«Fold & watch»**: retirarse y seguir viendo la mano mientras se busca otra mesa | 888poker SNAP |
| 17 | **Ficha de torneo completa** (estructura, late reg, inscritos) en el lobby | WSOP.com |
| 18 | **Estadísticas propias** (manos, winrate, retiradas) en el perfil | PokerCraft / ClubGG |

### P3 · La apuesta grande

| # | Idea | Inspiración | Nota |
|---|---|---|---|
| 19 | **Revisión post-mano** («has igualado 40 con 18 % de equity»; gráfica de pila; repetir la decisión) | Chess.com / WPT QuintAce | El mayor diferenciador, y encaja con la vocación didáctica del proyecto |
| 20 | **Modo asíncrono por turnos** para brisca/tute/mus (24 h por jugada, varias partidas a la vez) | Board Game Arena | Cambia el modelo de sala: WebSocket + persistencia + notificaciones |
| 21 | **Fast-fold interno** (al retirarte te reencola en otra mesa al instante) | 888 SNAP / GG Rush & Cash | Exige mesas compartidas en servidor, no solo pares |

---

## 4. Lo que se ha aplicado en esta tanda

- **Presets ⅓ y ¾** en la mesa de póker. La lógica existente (`quickRaise`) ya acotaba al rango
  legal (min/max), así que solo se añadieron los dos botones.
- **Cuota del bote** al lado del botón de igualar: `amount / (bote + amount)`, redondeada. Se
  muestra como píldora con tooltip traducido en ES/EN/FR. Si no hay bote o no hay nada que
  igualar, no se pinta.
- **Aviso sonoro de turno**: al recibir un `table_state` en el que la acción pasa a tu asiento, se
  reproduce `chip.wav` (el mismo sonido de fichas de las otras mesas). Respeta el silencio
  guardado por `GameSound` y no suena a espectadores.
- **Tapete del `game-board`**: pasa de `http://localhost:8000/...` a `/game-assets/...`. En
  producción HTTPS el navegador bloqueaba la imagen por contenido mixto; era un fondo roto que no
  se veía en local.

Verificado con `ng build`, `eslint`, 184 unitarios y la suite e2e de Chromium (el único fallo,
`gestos.spec.ts`, pasa al repetirlo: es una carrera con el turno de los bots, no una regresión).

---

## 5. Lo que NO hay que copiar

- **Cualquier cosa que dependa de dinero real**: rakeback, staking, seguros de bad beat, cashier,
  bonos por depósito. Sin depósito no significan nada y añaden superficie de fraude.
- **KYC, geolocalización y regulación multi-estado** (WSOP.com): complejidad enorme para fichas
  virtuales.
- **Dark patterns**: cofres que caducan en 48 h, FOMO con temporizador, compra de fichas. La
  retención debe venir de jugar con amigos y de mejorar, no de la ansiedad.
- **HUDs de terceros**: en GGPoker están prohibidos y su sustituto es un HUD propio. Aquí lo
  coherente es estadísticas propias y nada que dé ventaja en tiempo real.
- **SnapCam / streaming WebRTC en mesa**: coste alto, poca gente lo usa entre amigos.

---

## 6. Fuentes

Póker:

- PokerStars — Quick Seat, filtros y favoritos: <https://www.pokerstars.com/poker/room/features/software-news/> · <https://www.pokerstars.com/help/articles/client-feature-favorites/11023>
- PokerStars — misiones diarias: <https://www.pokerstars.com/poker/promotions/daily-missions> · rueda: <https://www.pokerstars.com/poker/promotions/daily-prize-wheel-2/>
- PokerStars — escuela: <https://www.pokerstars.fr/en/poker/school> · RNG: <https://www.pokerstars.com/rng> · juego responsable: <https://www.pokerstars.com/casino/about/responsible-gaming> · Home Games: <https://www.pokerstars.com/poker/home-games/>
- GGPoker — Smart Betting: <https://ggpoker.com/poker-games/smart-betting/> · features de mesa: <https://ggpoker.com/poker-card-games/table-features/> · seguridad: <https://ggpoker.com/blog/new-security-measures-at-ggpoker/>
- 888poker — SNAP: <https://888poker.com/poker-games/snap>
- WPT Global — lobby y mesa: <https://worldpokerdeals.com/blog/how-has-the-wpt-global-client-lobby-changed> · <https://worldpokerdeals.com/rakeback-deals/wpt-global-review>
- WSOP.com — lobby y multi-mesa: <https://usgamingreview.com/online-poker/wsop-review/>
- ClubGG — clubs y reglas: <https://www.clubgg.com/> · <https://help.clubgg.com/article/Clubs---Basics>
- PokerBros — clubs, racha y economía: <https://pokernews.com/news/2020/07/pokerbros-play-poker-the-way-you-want-when-you-want-37631.htm>

Juegos y UX:

- Board Game Arena — turnos asíncronos y reloj: <http://en.boardgamearena.com/doc/Turn_based_FAQ> · <http://en.boardgamearena.com/doc/Game_clock>
- Colonist.io — ranked, temporadas y placements: <https://colonist.instantdocsbase.com/doc/how-does-the-ranked-system-work> · <https://blog.colonist.io/colonist-io-2025-summary>
- Chess.com — Game Review y ligas: <https://support.chess.com/en/articles/8584089-how-does-game-review-work> · <https://www.chess.com/article/view/chesscom-features>
- Balatro — juice y ajustes de velocidad: <https://teemo.dev/game-design/balatro/systems/game-feel-and-juice> · <https://blakecrosley.com/guides/design/balatro>
- Marvel Snap — partidas cortas y «Escaped!»: <https://www.theguardian.com/games/2022/nov/11/i-craved-a-bite-size-experience-ben-brode-on-the-making-of-marvel-snap> · <https://www.theverge.com/23437497/marvel-snap-developer-design-interview-mobile-steam>
- Duolingo — jugar antes de registrarse: <https://screensdesign.com/articles/duolingo-onboarding-design> · <https://www.925studios.co/blog/duolingo-design-breakdown>
- Discord — comunidad y bots: <https://docs.discord.com/developers/game-development/how-to-keep-your-players-engaged>
