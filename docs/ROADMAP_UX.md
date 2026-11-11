# Transformación visual: de mesa de cartas a «Balatro táctil» en sala común

Objetivo: que los seis juegos se **sientan** como Balatro en un móvil —cartas grandes que responden
al dedo, una mano que se puede jugar con un pulgar— y que la partida con amigos funcione como una
**sala común estilo Kahoot**: un código, todos dentro, cada uno desde su teléfono.

Referencia estudiada: `LoreanXavier/balatro-portrait-mobile` (mod no oficial, MIT para su código).
Copiado **fuera del repositorio**, en `C:\Users\aleja\Desktop\github\_refs\balatro-portrait-mobile`,
para consulta. No se versiona ni se copia código: se toman **decisiones de diseño y cifras**.

---

## Lo que hace que Balatro se sienta a Balatro (y no a una mesa de cartas)

Del código del mod (parches en Lua sobre el juego real) y del vídeo, lo que de verdad mueve la
sensación:

1. **La carta es un objeto físico.** Se inclina en 3D siguiendo el dedo/ratón (`tilt_var.mx/my`),
   con un reflejo que se mueve con ella. El mod tiene que **limitar** ese desplazamiento porque con
   el dedo se dispara y la carta se «deforma en paralelo»: la inclinación es sutil, de unos pocos
   grados, no un efecto de feria.
2. **La mano es un abanico, no una fila.** Las cartas se reparten a lo ancho del hueco disponible
   (`usable_w`), con separación calculada según cuántas hay y un pequeño levantamiento; al
   seleccionar, **suben** y se tiñen.
3. **Un gesto, una acción.** El mod define el *flick* así: recorrido vertical mínimo de **1,4**
   unidades de juego, desviación horizontal máxima del **60 %** del recorrido vertical, y soltar en
   **menos de 0,45 s**. Fuera de eso es un toque o un arrastre, no una jugada. Y las cartas
   seleccionadas **acompañan** el arrastre (`group_follow`).
4. **Tocar pide información, no juega.** Desde la 1.0.6, un toque en una carta/joker/consumible abre
   su descripción y la deja abierta; otro toque (o tocar fuera) la cierra. Mantener pulsado sigue
   funcionando. La descripción abierta **no** deja pasar el toque al botón de debajo.
5. **Todo está sobredimensionado.** `card_button_mult = 1.4` en móvil; el HUD se escala según la
   altura de la pantalla (0,39 en pantallas altas, 0,46 en cortas) en vez de tener un tamaño fijo.
6. **Nada de scroll.** La mesa cabe entera: HUD arriba, zona de juego en medio, mano abajo. Si algo
   no cabe, se encoge el HUD, no se añade una barra de desplazamiento.
7. **Juice contenido:** rebote al repartir, golpe seco al jugar, números que suben con conteo,
   partículas al puntuar. Todo corto (<300 ms) y con sonido.

Medido en los fotogramas del vídeo (1080×1350): la mano ocupa la franja **y 55–90 %** y llega al
**80–94 % del ancho**, con cartas solapadas. Es decir: media pantalla para jugar, la otra mitad para
leer el estado.

---

## Tres acercamientos posibles

Antes de tocar nada hay que elegir el alcance. Los tres parten de lo que ya existe (componente
`playing-card`, baraja de Balatro ya compuesta, sonidos, i18n).

### A · «Arcade táctil» (máximo parecido a Balatro)

Cartas con inclinación 3D, abanico con rotación, barrido de brillo, partículas y rebotes; botones
grandes con contador; tipografía pixel. Es lo que se ve en el vídeo.

- **A favor:** es lo que pides y lo que engancha; se nota muchísimo en móvil.
- **En contra:** más CSS/animación por juego (seis), riesgo de marear si se abusa, y hay que
  mantenerlo accesible (movimiento reducido).
- **Coste:** alto (6-8 tandas).

### B · «Mesa limpia de un pulgar» (Balatro en la mecánica, sobrio en el adorno)

Misma disposición y mismos gestos (abanico, subir al seleccionar, flick para jugar, toque para
información), pero sin inclinación 3D ni partículas: sombras duras, transiciones cortas, tipografía
del proyecto.

- **A favor:** el 80 % de la sensación con el 40 % del trabajo; menos ruido y menos bugs.
- **En contra:** no es «igual que Balatro»; quien compare lado a lado lo notará.
- **Coste:** medio (3-4 tandas).

### C · «Sala común» primero (Kahoot con cartas)

Prioriza el flujo social —código grande, lobby en vivo, turnos con cuenta atrás, marcador entre
rondas, móvil para cada jugador— sobre el acabado de las cartas.

- **A favor:** es lo que hace que se juegue **con amigos**, que es el objetivo real.
- **En contra:** sin el trabajo de A/B las cartas siguen pareciendo una web.
- **Coste:** medio (3-4 tandas), pero **no se pisa** con A/B: se puede hacer en paralelo.

**Recomendación adoptada (10-11-2026): B + C a la vez**, y luego subir a A por partes (la
inclinación y el abanico son lo que más se nota; las partículas y el CRT son lo último). Con B+C el
juego ya se siente móvil y se juega en grupo; A se añade encima sin rehacer nada.

### Decisiones tomadas (10-11-2026)

| Pregunta | Decisión |
|---|---|
| ¿A, B o C? | **B + C**, y después A por partes |
| ¿Dónde se juega? | **Cada uno en su móvil** (Kahoot). No hay pantalla común |
| Jugadores por sala | **2 a 6** |
| Baraja | **Se mantiene la de Balatro** (pixel art de la baraja francesa) |

---

## Plan por fases

Cada fase es desplegable por sí sola y deja la `main` intacta (se trabaja en `preprod`).

### F1 · Fundación de movimiento y medidas (base de todo) — 1 tanda

- [ ] **Tokens de carta** en `styles.scss`: grosor de borde, radio, sombra dura (`0 4px 0`),
      duración de muelle (`--card-spring: cubic-bezier(.2,.9,.25,1.2)`), elevación al seleccionar.
- [ ] **`playing-card` con estados**: `idle`, `elevada`, `seleccionada`, `jugada`, `ganadora`.
      Hoy la carta es estática; los juegos la decoran por fuera.
- [ ] **Tamaño por variable, no por `@media`**: `--carta-w` calculado con `clamp()` y con la altura
      disponible (equivalente al `hud_scale_tall/normal/short` del mod: 0,39 / 0,42 / 0,46).
- [ ] **Regla de oro:** nada de scroll en la mesa; si no cabe, encoge la mano.
- **Hecho cuando:** las 6 mesas se ven igual de grandes en un Pixel 7 y en un iPhone SE, sin scroll
  vertical, y los tests de móvil siguen en verde.

### F2 · La mano como abanico · ✅ hecho (10-11-2026)

- [ ] Componente **`mano`** compartido: reparte cartas a lo ancho (`usable_w`), calcula separación
      según cuántas haya, aplica rotación leve (±6° máximo) y desplazamiento vertical en arco.
- [ ] **Selección**: la carta sube ~10 px, se escala 1,06 y se tiñe; el resto se aparta un poco.
- [ ] **Sustituir** las cinco manos actuales (culo, brisca, tute, mus, mentiroso) por el componente.
- **Hecho cuando:** la misma mano se ve igual en los cinco juegos y el e2e de jugar una carta sigue
  pasando en móvil.

### F3 · Gestos: tocar, arrastrar, lanzar · ✅ casi (10-11-2026)

- [x] **Toque** = seleccionar (nunca jugar). **Doble toque** = jugar la carta sola.
- [x] **Gesto hacia arriba** para jugar: recorrido ≥ 56 px, desviación lateral ≤ 60 %, y se descarta
      si el dedo se queda más de 600 ms (si no, sería un arrastre sin querer).
- [x] **Toque mantenido** (450 ms) enseña la carta grande y centrada; se cierra tocando en cualquier
      sitio o con Escape, y el toque **no** pasa al botón de debajo.
- [x] Vibración corta al elegir (6 ms) y al abrir la vista (10 ms).
- [x] Enganchado en **brisca**, **culo** y **tute** (`(alLanzar)` → `lanzarPorId`, que elige y juega).
- [ ] **Arrastrar** manteniendo la selección agrupada (`group_follow`): pendiente.
- [ ] Mus y mentiroso: su mano no juega (descartar / elegir valor), así que siguen con botones.
- **Pendiente de verificar:** una baza entera de brisca solo con gestos (el doble toque y el gesto
  están probados por separado; falta la partida completa).

Ojo con el `z-index`: la mano fija es un contexto propio (6), así que la vista previa no puede
superarla desde dentro; con la vista abierta el host sube a 50 (`:host(.vista-abierta)`).

### F4 · Botones y HUD de pulgar · ⏳ a medias (10-11-2026)

- [x] Botonera inferior con **altura mínima 56 px** en el móvil (≤640 px), a lo ancho y repartida a
      partes iguales. Va justo encima de la mano fija, en la zona del pulgar.
- [x] Nada pegado al borde: `env(safe-area-inset-*)` a los lados y debajo de la mano.
- [ ] Contador (`3/5`) junto a la acción: pendiente, cada juego tendría que exponer cuántas cartas
      le quedan por jugar.
- [ ] HUD (turno, puntos, bazas) compacto arriba: hoy cada juego pinta lo suyo.
- [ ] Indicador de turno inequívoco (borde iluminado + nombre): el borde ya se ilumina; falta el
      nombre.
- **Hecho cuando:** una persona juega una ronda completa con una sola mano y sin mirar dos veces.

### La mesa ovalada (empezada)

- [x] Centro como **óvalo de fieltro** y rivales **sentados en arco** (los del medio más lejos, los
      de fuera más cerca). Regla común en `styles.scss` sobre `.mesa__rivales` con `--i` / `--n`.
- [x] Puesto en culo, brisca, tute y mentiroso. **Mus** no usa ese marcado: pendiente.
- [ ] Cada rival en **su posición** del óvalo (izquierda, arriba, derecha) en vez de una fila curvada.
- [ ] **La última carta que echó** cada uno delante de su asiento (hoy el centro solo enseña la
      última jugada, con el nombre de quien la echó).
- [ ] El turno marcado en el asiento de quien juega.

Nota de test: el e2e del doble toque se reintenta hasta tres veces porque los bots juegan entre
medias y la mano se recoloca; sin reintento fallaba por carrera, no por el gesto.

Truco: el botón vive dentro de `app-button`, así que estirar `.controles__botones button` no basta;
hay que estirar también el host (`.controles__botones > * { width: 100% }`).

### F5 · Sala común estilo Kahoot (el flujo con amigos) — 1-2 tandas

- [ ] **Código de sala gigante** (4 caracteres, legible a un metro) y enlace/QR para entrar directo.
- [ ] **Lobby en vivo**: avatares que aparecen, «listo» por jugador, cuenta atrás compartida.
- [ ] **Ritmo**: ronda → marcador entre rondas → siguiente. Marcador con animación de subida.
- [ ] **Espectador** claro: «estás mirando», sin cartas ajenas.
- [ ] Reconexión silenciosa (ya hay JWT y WebSocket): si se cae la red, vuelve a su silla.
- **Hecho cuando:** cuatro móviles entran con un código y terminan una partida de Mus sin recargar.

### F6 · El adorno de Balatro (solo si F1-F5 están cerradas) — 2 tandas

- [ ] **Inclinación 3D** de la carta siguiendo el dedo, con el desplazamiento **limitado** (el mod lo
      limita justo para que no se deforme) y reflejo que se mueve.
- [ ] **Barrido de brillo** al repartir, rebote al aterrizar.
- [ ] **Partículas** al ganar baza (10-14, cortas) y números que cuentan hacia arriba.
- [ ] **CRT/scanlines sutil y opcional** (ajuste en preferencias, apagado por defecto en móvil).
- [ ] Todo respeta `prefers-reduced-motion`: con movimiento reducido, sin inclinación ni partículas.
- **Hecho cuando:** se puede jugar igual con el ajuste de movimiento reducido activado.

---

## Lo que se puede reutilizar tal cual

| Del mod | En nuestro proyecto |
|---|---|
| Umbrales del *flick* (1,4 / 60 % / 0,45 s) | Constantes en `gestos.ts`, en píxeles |
| Escala del HUD por altura (0,39-0,46) | `clamp()` sobre `--altura-disponible` |
| `card_button_mult = 1.4` | Altura mínima de botón en mesa (56 px) |
| Toque = descripción, no acción | Comportamiento de la mano |
| Ajuste de movimiento reducido | `@media (prefers-reduced-motion)` |

**Lo que no se copia:** ni una línea de Lua, ni arte, ni sonidos del juego. La baraja ya está
compuesta en el repo y el resto es CSS/TS propio.

## Hecho ya (primera pasada de movilidad, 10-11-2026)

Lo mínimo para que la carta deje de ser una imagen: **inclinación 3D hacia el dedo, brillo que
sigue al puntero y muelle en los cambios de estado**, en el componente `playing-card` (común a los
seis juegos, sin tocar cada mesa).

- `--pc-rx` / `--pc-ry`: inclinación de **±7°** con ratón y **±4°** con el dedo, con el
  desplazamiento **limitado a ±1** antes de pasarlo a grados (sin eso, en los bordes la carta se
  deforma en un paralelogramo; es el mismo bug que arreglaron en el mod).
- `--pc-luz-x/y`: el brillo (`::after`, `soft-light`) sigue al puntero. Solo en el mazo de Balatro:
  sobre el pixel art de la baraja española un degradado lo enturbia.
- Muelle de **120 ms** (`cubic-bezier(.2,.9,.25,1.15)`) y elevación pequeña en la carta, porque el
  levantamiento grande ya lo hace el botón de la mano (10 px) — si sumaran, daría un salto doble.
- **`prefers-reduced-motion`**: sin inclinación, sin brillo y sin animaciones.
- Probado con `e2e/cartas.spec.ts`: la carta se inclina al mover el puntero, vuelve a plana al
  salir, y con movimiento reducido no se mueve.

### F2 · El abanico (hecho)

Un componente **`app-mano`** que usan los cinco juegos (culo, brisca, tute, mus y mentiroso) en vez
de repetir la mano en cada plantilla:

- **Geometría en CSS**, con dos números por carta (`--i`, `--n`): el giro se reparte entre los
  extremos (**±8°**, la primera y la última; el centro recto, sea cual sea el número de cartas) y un
  **arco de abanico**: la carta del medio es la más alta y las de fuera bajan 26 px, como un abanico
  de verdad apoyado en los extremos. El hueco de esa caída se reserva abajo (`padding-bottom`), si no
  las cartas se salían de la pantalla.
- **La mano va pegada al borde inferior** de la pantalla, como en Pokémon TCG Pocket: `position:
  fixed` y la página reserva su hueco (`body.tiene-mano`), en vez de `sticky`, porque en estas mesas
  la mano va antes que los controles en el HTML y con `sticky` los controles acababan detrás.
- **El ancho de carta se calcula**: N cartas ocupan `W + (N−1)·0,62·W`, así que con el ancho de la
  ventana se despeja W (64 px con siete cartas, ~54 px con diez en un móvil de 390). Antes, con diez
  cartas la mano se salía 48 px por la izquierda y media mano quedaba fuera.
- Al pasar por encima (o con el teclado) la carta **se levanta y se endereza**: deja de tapar a la
  siguiente y se lee entera. La elegida se queda arriba, con aro de color.
- **Por carta**: `deshabilitada` (el tute solo deja jugar algunas) e `ilegal` (se ve al 42 % para que
  se entienda el porqué). El nombre accesible sale de `culo.*` o `baraja.*` según el juego.
- **`prefers-reduced-motion`**: sin abanico ni levantamiento.

### La baraja española (para más adelante)

La de 40 no está hecha con arte propio: los cinco juegos usan el arte 8-bit del juego en C con los
nombres de aquí. Cuando haya una baraja española de verdad, se cambia `BARAJA.es` en
`playing-card.ts` y listo (el componente ya pide `carpeta` + `extension`).

- **Descargada y guardada** en `Desktop/github/_refs/baraja-espanola-pixel/` (fuera del repo):
  [Spanish Deck – Pixel Art, de jcanabal](https://jcanabal.itch.io/spanish-deck-pixel-art). Edición
  gratuita: **40 cartas + dorso, PNG transparente de 73×113**. Encaja con el estilo del proyecto.
  ⚠️ La página **no indica licencia**: antes de publicarlo hay que pedírsela al autor o comprar la
  edición completa.
- **Alternativa sin dudas de licencia**: [Baraja española completa en Wikimedia
  Commons](https://commons.wikimedia.org/wiki/File:Baraja_espa%C3%B1ola_completa.png) (dominio
  público, una sola imagen de 2.496×1.595 que habría que recortar en 40 cartas) y
  [Baraja española.svg](https://commons.wikimedia.org/wiki/File:Baraja_espa%C3%B1ola.svg).
- **Numeración del pack**: los ficheros van `1.PNG` … `40.PNG` sin decir el palo; hay que mirarlos uno
  a uno para hacer el mapa (los pips se cuentan igual que se hizo con `1.cards` del juego).

### La baraja

El poker y los cinco juegos usan ya el **arte 8-bit del propio juego** (`juego/assets/cards/BASIC`),
reescalado a WebP por `scripts/generar_baraja_8bit.py`: 53 cartas francesas en `cards/8bit` y las 41
de la española en `cards/es8bit`, 0,4 MB entre las dos. La española de 40 es la francesa **sin 8, 9
ni 10**, así que es el mismo dibujo con los nombres de aquí (oros → diamantes, copas → corazones,
espadas → picas, bastos → tréboles; sota → J, caballo → Q, rey → K). Las reglas no cambian: por
dentro la sota sigue siendo la carta 10.

Verificado con la suite completa (**68 e2e** de escritorio, **2 en `fixme`** documentado) y **4/4** en
móvil. El test de móvil comprueba, carta por carta, que **ninguna se sale** de la pantalla (ni por
arriba, ni por los lados, ni por abajo) y que los botones responden a un toque de verdad.

Pendiente de esta familia: los **gestos** (F3) y las **partículas/CRT** (F6).
