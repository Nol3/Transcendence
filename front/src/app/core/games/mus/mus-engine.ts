/**
 * El Mus, en reglas puras.
 *
 * Es el más grande de los cuatro y el único que **no** es de bazas: aquí no se juega una carta
 * contra otra, sino que cada pareja **apuesta** sobre lo que tiene en la mano, y se compara al
 * final de cada lance.
 *
 * Lo que hay que tener claro antes de leer nada:
 *
 * - **Se juega de cuatro, en dos parejas**, cada uno frente a su compañero: los asientos 0 y 2 son
 *   pareja, y el 1 y el 3 la otra.
 * - **No hay triunfo ni palos.** El orden de las cartas es: **rey o tres, caballo, sota, siete,
 *   seis, cinco, cuatro, dos o as**. O sea, el tres vale lo mismo que el rey y el dos lo mismo que
 *   el as: se juega «con ocho reyes y ocho ases».
 * - Antes de nada está **el mus**: cada uno, desde el mano, dice si quiere descartar o si corta.
 *   **En cuanto uno corta, se cierra el descarte para todos**, aunque alguno no haya hablado.
 * - Luego, los **cuatro lances en este orden**: grande, chica, pares y juego. El orden importa,
 *   porque una pareja puede llegar a las 40 piedras a mitad del recuento y ahí se acaba.
 * - Cada lance se **envida**: paso, envido, quiero, no quiero, envido más u órdago. En parejas
 *   prevalece la apuesta más alta de los dos.
 *
 * Igual que los demás motores: recibe estado y devuelve estado, sin tocar nada por dentro.
 */

import { Card, buildDeck, dealSome, shuffle } from '../baraja';

export const JUGADORES = 4;
/** Las 40 piedras a las que se juega el juego. */
export const PIEDRAS_PARA_GANAR = 40;
/** Los juegos que hay que ganar para llevarse la vaca. */
export const JUEGOS_POR_VACA = 3;
/** El envite mínimo. */
export const ENVIDO_MINIMO = 2;

export type Lance = 'grande' | 'chica' | 'pares' | 'juego';
export const LANCES: Lance[] = ['grande', 'chica', 'pares', 'juego'];

/** El orden de las cartas del mus, de mayor a menor. El tres va con el rey y el dos con el as. */
export const ORDEN_MUS: readonly Card['rank'][] = [12, 3, 11, 10, 7, 6, 5, 4, 1, 2];

/** Lo que vale cada carta al contar los puntos (para el punto). */
export function puntosMus(carta: Card): number {
  if (carta.rank === 12 || carta.rank === 3 || carta.rank === 11 || carta.rank === 10) return 10;
  if (carta.rank === 2 || carta.rank === 1) return 1;
  return carta.rank;
}

/** Lo que vale cada carta para el juego: aquí el tres vale 3 y el dos 1 (sin la regla de los 8 reyes). */
export function puntosJuego(carta: Card): number {
  if (carta.rank === 12 || carta.rank === 11 || carta.rank === 10) return 10;
  return carta.rank;
}

/** Las cartas que valen lo mismo: el tres con el rey y el dos con el as («ocho reyes y ocho ases»). */
const EQUIVALENCIAS: Partial<Record<Card['rank'], Card['rank']>> = { 3: 12, 2: 1 };

/** La fuerza de una carta en el mus: más alto gana. El tres empata con el rey y el dos con el as. */
export function fuerzaMus(carta: Card): number {
  const rank = EQUIVALENCIAS[carta.rank] ?? carta.rank;
  return ORDEN_MUS.length - ORDEN_MUS.indexOf(rank);
}

/** Las parejas: duples (dos parejas o cuatro iguales) > medias (tres iguales) > pareja. */
export type CategoriaPares = 'duples' | 'medias' | 'par' | null;

export interface Pares {
  categoria: CategoriaPares;
  /** La carta más alta de la combinación, para desempatar. */
  alto: number;
}

export interface Jugada {
  /** La carta más alta de la mano (grande). */
  grande: number;
  /** La carta más baja (chica). */
  chica: number;
  pares: Pares;
  /** La suma para el juego, o `null` si no llega a 31. */
  juego: number | null;
  /** La suma para el punto (el que más se acerque a 30). */
  punto: number;
}

/** Evalúa las cuatro cartas de un jugador. */
export function evaluar(mano: Card[]): Jugada {
  const fuerzas = mano.map(fuerzaMus);
  const porRango = new Map<Card['rank'], number>();
  for (const c of mano) porRango.set(c.rank, (porRango.get(c.rank) ?? 0) + 1);

  const repes = [...porRango.entries()].sort((a, b) => b[1] - a[1]);
  const cuantos = repes[0]?.[1] ?? 0;
  const dosParejas = repes.filter(([, n]) => n === 2).length === 2;
  const categoria: CategoriaPares =
    cuantos === 4 || dosParejas ? 'duples' : cuantos === 3 ? 'medias' : cuantos === 2 ? 'par' : null;

  // Para desempatar manda la carta más alta **de la combinación**: en un póker o en unas medias es
  // el rango repetido; en unas duples, la más alta de las dos parejas.
  let alto = 0;
  if (categoria === 'duples') {
    const rangos = cuantos === 4 ? [repes[0][0]] : repes.filter(([, n]) => n === 2).map(([r]) => r);
    alto = Math.max(...rangos.map((r) => fuerzaMus({ rank: r } as Card)));
  } else if (categoria) {
    alto = fuerzaMus({ rank: repes[0][0] } as Card);
  }

  const sumaJuego = mano.reduce((n, c) => n + puntosJuego(c), 0);
  return {
    grande: Math.max(...fuerzas),
    chica: Math.min(...fuerzas),
    pares: { categoria, alto },
    juego: sumaJuego >= 31 ? sumaJuego : null,
    punto: mano.reduce((n, c) => n + puntosMus(c), 0),
  };
}

/**
 * El orden del juego, de mejor a peor: **31, 32, 40, 37, 36, 35, 34, 33**.
 *
 * El 31 es la «una» y gana siempre. El 38 y el 39 no existen, porque la baraja no tiene ochos ni
 * nueves. Devuelve la posición (0 = la mejor) o -1 si no es un juego.
 */
export function ordenJuego(suma: number): number {
  const orden = [31, 32, 40, 37, 36, 35, 34, 33];
  return orden.indexOf(suma);
}

/** Compara dos jugadas del mismo lance. Positivo si gana la primera. */
export function comparar(a: Jugada, b: Jugada, lance: Lance): number {
  if (lance === 'grande') return a.grande - b.grande;
  if (lance === 'chica') return b.chica - a.chica;
  if (lance === 'pares') {
    const peso = (c: CategoriaPares) => (c === 'duples' ? 3 : c === 'medias' ? 2 : c === 'par' ? 1 : 0);
    const d = peso(a.pares.categoria) - peso(b.pares.categoria);
    return d !== 0 ? d : a.pares.alto - b.pares.alto;
  }
  // Juego: si alguien tiene juego, gana el mejor; si no, se va al punto.
  if (a.juego !== null || b.juego !== null) {
    if (a.juego === null) return -1;
    if (b.juego === null) return 1;
    return ordenJuego(b.juego) - ordenJuego(a.juego); // orden más bajo = mejor
  }
  // Menos distancia al 30 es mejor, así que el signo va al revés que en los demás lances.
  return puntoCerca(b.punto) - puntoCerca(a.punto);
}

/** Lo cerca que está del 30, para el punto: más pequeño es mejor. */
function puntoCerca(punto: number): number {
  return punto <= 30 ? 30 - punto : 100 + (punto - 30);
}

// ── Apuestas ──────────────────────────────────────────────────────────────────

export type Apuesta = 'paso' | 'envido' | 'quiero' | 'no_quiero' | 'envido_mas' | 'ordago';

export interface Envite {
  /** Quién la hizo. */
  quien: number;
  /** Cuántas piedras. */
  cuantas: number;
  /** Si es un órdago, se juega la vaca entera. */
  ordago: boolean;
}

// ── Estado ────────────────────────────────────────────────────────────────────

export interface MusPlayer {
  id: number;
  name: string;
  isBot: boolean;
  hand: Card[];
  /** La jugada evaluada de su mano (el servidor la sabe; en la vista solo se enseña a su dueño). */
  jugada: Jugada;
  /** Si ya ha dicho «mus» o «no hay mus» en esta mano. */
  hablado: boolean;
  /** Cuántas veces ha cambiado cartas: el bot solo pide mus una vez por mano. */
  descartes: number;
  connected?: boolean;
}

export interface MusTeam {
  id: number;
  players: number[];
  piedras: number;
  juegos: number;
}

export type MusEvent =
  | { kind: 'deal' }
  | { kind: 'mus'; player: number }
  | { kind: 'cortar'; player: number }
  | { kind: 'descartar'; player: number; cuantas: number }
  | { kind: 'envite'; player: number; apuesta: Apuesta; cuantas: number }
  | { kind: 'lance'; lance: Lance; team: number; piedras: number }
  | { kind: 'nadie'; lance: Lance }
  | { kind: 'game-end'; team: number }
  | { kind: 'vaca'; team: number };

export interface MusState {
  players: MusPlayer[];
  teams: [MusTeam, MusTeam];
  /** Quién habla primero. */
  mano: number;
  phase: 'mus' | 'descartar' | 'lances' | 'game-end' | 'vaca-end';
  /** El lance que se está jugando. */
  lance: Lance | null;
  /** En qué lance toca hablar a cada asiento (`null` = ya ha hablado en este lance). */
  habladoEnLance: number[];
  /** El envite vivo, si lo hay. */
  envite: Envite | null;
  /** Quién tiene que responder al envite. */
  responde: number | null;
  /** Los que ya se han plantado en este lance. */
  pasados: number[];
  /** Los envites de este lance, para el tanteo (piedras ya ganadas). */
  piedrasDelLance: number;
  /** El resultado de este lance, una vez resuelto. */
  ganadorLance: number | null;
  events: MusEvent[];
  winner: number | null;
}

export class MusError extends Error {
  constructor(
    public readonly code: string,
    message: string,
  ) {
    super(message);
    this.name = 'MusError';
  }
}

/** La pareja de cada asiento: el 0 con el 2, el 1 con el 3. */
export function parejaDe(seat: number): number {
  return seat % 2;
}

export function newGame(opts: {
  names: string[];
  bots?: boolean[];
  piedras?: [number, number];
  juegos?: [number, number];
  mano?: number;
  rng?: () => number;
}): MusState {
  if (opts.names.length !== JUGADORES) {
    throw new MusError('players', 'el mus se juega de cuatro, en dos parejas');
  }
  const mazo = shuffle(buildDeck(1), opts.rng);
  const { hands } = dealSome(mazo, JUGADORES, 4);
  const mano = opts.mano ?? 0;

  const players: MusPlayer[] = opts.names.map((name, id) => ({
    id,
    name,
    isBot: opts.bots?.[id] ?? false,
    hand: [...hands[id]],
    jugada: evaluar(hands[id]),
    hablado: false,
    descartes: 0,
  }));

  return {
    players,
    teams: [
      { id: 0, players: [0, 2], piedras: opts.piedras?.[0] ?? 0, juegos: opts.juegos?.[0] ?? 0 },
      { id: 1, players: [1, 3], piedras: opts.piedras?.[1] ?? 0, juegos: opts.juegos?.[1] ?? 0 },
    ],
    mano,
    phase: 'mus',
    lance: null,
    habladoEnLance: [],
    envite: null,
    responde: null,
    pasados: [],
    piedrasDelLance: 0,
    ganadorLance: null,
    events: [{ kind: 'deal' }],
    winner: null,
  };
}

function clone(state: MusState): MusState {
  return {
    ...state,
    players: state.players.map((p) => ({ ...p, hand: [...p.hand], jugada: { ...p.jugada } })),
    teams: [
      { ...state.teams[0], players: [...state.teams[0].players] },
      { ...state.teams[1], players: [...state.teams[1].players] },
    ],
    habladoEnLance: [...state.habladoEnLance],
    pasados: [...state.pasados],
    envite: state.envite ? { ...state.envite } : null,
    events: [...state.events],
  };
}

function jugador(state: MusState, id: number): MusPlayer {
  const p = state.players[id];
  if (!p) throw new MusError('unknown_player', 'ese jugador no está en la mesa');
  return p;
}

/** El orden en que hablan en un lance: se empieza por el mano. */
function turnoDe(state: MusState, i: number): number {
  return (state.mano + i) % JUGADORES;
}

// ── El mus ────────────────────────────────────────────────────────────────────

/** Decir «mus»: quiero descartar. Solo vale si nadie ha cortado todavía. */
/** Se habla por orden, empezando por el mano. */
function comprobarTurno(state: MusState, playerId: number): void {
  if (turnoActual(state) !== playerId) {
    throw new MusError('not_your_turn', 'ahora no te toca');
  }
}

export function decirMus(state: MusState, playerId: number): MusState {
  if (state.phase !== 'mus') {
    throw new MusError('not_mus', 'ya no se puede pedir mus');
  }
  comprobarTurno(state, playerId);
  const yo = jugador(state, playerId);
  if (yo.hablado) throw new MusError('already_spoke', 'ya has hablado en esta mano');

  const siguiente = clone(state);
  siguiente.players[playerId].hablado = true;
  siguiente.events = [...siguiente.events, { kind: 'mus', player: playerId }];
  return avanzarMus(siguiente);
}

/** Cortar el mus: se cierra el descarte para todos y se pasa a los lances. */
export function cortarMus(state: MusState, playerId: number): MusState {
  if (state.phase !== 'mus') {
    throw new MusError('not_mus', 'ya no se puede cortar el mus');
  }
  comprobarTurno(state, playerId);
  const yo = jugador(state, playerId);
  if (yo.hablado) throw new MusError('already_spoke', 'ya has hablado en esta mano');

  const siguiente = clone(state);
  siguiente.players[playerId].hablado = true;
  siguiente.events = [...siguiente.events, { kind: 'cortar', player: playerId }];
  // En cuanto uno corta, se cierra el descarte para todos.
  siguiente.phase = 'lances';
  siguiente.lance = LANCES[0];
  siguiente.habladoEnLance = [];
  siguiente.pasados = [];
  return siguiente;
}

function avanzarMus(state: MusState): MusState {
  const siguiente = clone(state);
  if (siguiente.players.every((p) => p.hablado)) {
    // Todos quieren mus: se descarta y se vuelve a hablar. Al descarte se entra con las marcas
    // limpias, porque el descarte también va por turnos.
    for (const p of siguiente.players) p.hablado = false;
    siguiente.phase = 'descartar';
  }
  return siguiente;
}

/** Descartar cartas (solo se puede si todos pidieron mus). */
export function descartar(state: MusState, playerId: number, cardIds: string[], rng?: () => number): MusState {
  if (state.phase !== 'descartar') {
    throw new MusError('not_discard', 'ahora no se descarta');
  }
  comprobarTurno(state, playerId);
  const yo = jugador(state, playerId);
  if (cardIds.length === 0 || cardIds.length > 4) {
    throw new MusError('bad_discard', 'se descartan entre una y cuatro cartas');
  }
  for (const id of cardIds) {
    if (!yo.hand.some((c) => c.id === id)) {
      throw new MusError('not_your_card', 'esa carta no es tuya');
    }
  }

  const siguiente = clone(state);
  const mazo = shuffle(buildDeck(1), rng);
  const nuevas: Card[] = [];
  const yaUsadas = new Set(siguiente.players.flatMap((p) => p.hand.map((c) => c.id)));
  for (const carta of mazo) {
    if (nuevas.length >= cardIds.length) break;
    if (yaUsadas.has(carta.id) || nuevas.some((n) => n.id === carta.id)) continue;
    nuevas.push(carta);
  }
  const mia = siguiente.players[playerId];
  mia.hand = [...mia.hand.filter((c) => !cardIds.includes(c.id)), ...nuevas];
  mia.jugada = evaluar(mia.hand);
  mia.descartes += 1;
  // `hablado` marca que ya ha descartado en esta vuelta; cuando todos han descartado, se vuelve al
  // mus con la marca limpia para poder volver a hablar.
  mia.hablado = true;
  siguiente.events = [
    ...siguiente.events,
    { kind: 'descartar', player: playerId, cuantas: cardIds.length },
  ];
  if (siguiente.players.every((p) => p.hablado)) {
    for (const p of siguiente.players) p.hablado = false;
    siguiente.phase = 'mus';
  }
  return siguiente;
}

// ── Los lances y las apuestas ─────────────────────────────────────────────────

/** Pasar en el lance actual. */
export function pasar(state: MusState, playerId: number): MusState {
  comprobarLance(state, playerId);
  const siguiente = clone(state);
  siguiente.players[playerId].hablado = true;
  siguiente.pasados = [...siguiente.pasados, playerId];
  siguiente.events = [
    ...siguiente.events,
    { kind: 'envite', player: playerId, apuesta: 'paso', cuantas: 0 },
  ];
  return cerrarOLance(siguiente, playerId);
}

/** Envidar (mínimo dos piedras). */
export function envidar(state: MusState, playerId: number, cuantas = ENVIDO_MINIMO): MusState {
  comprobarLance(state, playerId);
  if (cuantas < ENVIDO_MINIMO) {
    throw new MusError('too_small', 'el envite mínimo son dos piedras');
  }
  if (state.envite && cuantas <= state.envite.cuantas) {
    throw new MusError('too_small', 'hay que subir el envite');
  }
  const siguiente = clone(state);
  siguiente.players[playerId].hablado = true;
  siguiente.envite = { quien: playerId, cuantas, ordago: false };
  // Responde **la pareja contraria**: el siguiente en el orden de habla que no sea de mi pareja
  // (si no se filtra, un compañero acabaría respondiendo a su propio envite).
  siguiente.responde = siguienteContrario(siguiente, playerId);
  siguiente.events = [
    ...siguiente.events,
    { kind: 'envite', player: playerId, apuesta: 'envido', cuantas },
  ];
  return siguiente;
}

/** Órdago: se juega la vaca entera. */
export function ordago(state: MusState, playerId: number): MusState {
  comprobarLance(state, playerId);
  const siguiente = clone(state);
  siguiente.players[playerId].hablado = true;
  siguiente.envite = { quien: playerId, cuantas: 0, ordago: true };
  siguiente.responde = siguienteContrario(siguiente, playerId);
  siguiente.events = [
    ...siguiente.events,
    { kind: 'envite', player: playerId, apuesta: 'ordago', cuantas: 0 },
  ];
  return siguiente;
}

/** Querer el envite: el lance se juega por lo apostado. */
export function quiero(state: MusState, playerId: number): MusState {
  if (!state.envite || state.responde !== playerId) {
    throw new MusError('nothing_to_accept', 'no hay nada que querer');
  }
  const siguiente = clone(state);
  const envite = siguiente.envite!;
  siguiente.piedrasDelLance += envite.cuantas;
  siguiente.envite = null;
  siguiente.responde = null;
  siguiente.players[playerId].hablado = true;
  siguiente.events = [
    ...siguiente.events,
    { kind: 'envite', player: playerId, apuesta: 'quiero', cuantas: envite.cuantas },
  ];
  // Ya está apostado: se resuelve el lance.
  return resolverLance(siguiente);
}

/** No querer: quien envidó se lleva una piedra y se pasa al lance siguiente. */
export function noQuiero(state: MusState, playerId: number): MusState {
  if (!state.envite || state.responde !== playerId) {
    throw new MusError('nothing_to_reject', 'no hay nada que rechazar');
  }
  const siguiente = clone(state);
  const envite = siguiente.envite!;
  siguiente.teams[parejaDe(envite.quien)].piedras += 1;
  siguiente.envite = null;
  siguiente.responde = null;
  siguiente.events = [
    ...siguiente.events,
    { kind: 'envite', player: playerId, apuesta: 'no_quiero', cuantas: 0 },
    { kind: 'lance', lance: siguiente.lance!, team: parejaDe(envite.quien), piedras: 1 },
  ];
  // Ojo: esta piedra también puede llegar a las 40 y terminar el juego. Si solo se comprobara al
  // resolver el lance, una pareja podría pasarse de 40 por un envite rechazado y seguir jugando.
  if (!comprobarFin(siguiente, parejaDe(envite.quien))) return siguienteLance(siguiente);
  return siguiente;
}

/** El siguiente jugador del orden de habla que es de la pareja contraria. */
function siguienteContrario(state: MusState, playerId: number): number {
  for (let i = 1; i <= JUGADORES; i++) {
    const seat = (playerId + i) % JUGADORES;
    if (parejaDe(seat) !== parejaDe(playerId)) return seat;
  }
  return (playerId + 1) % JUGADORES;
}

function comprobarLance(state: MusState, playerId: number): void {
  if (state.phase !== 'lances') {
    throw new MusError('not_lances', 'ahora no se envidan lances');
  }
  comprobarTurno(state, playerId);
  if (state.envite) {
    throw new MusError('betting', 'hay un envite sin resolver');
  }
  const yo = jugador(state, playerId);
  if (yo.hablado) throw new MusError('already_spoke', 'ya has hablado en este lance');
}

/** Cierra el lance si ya han hablado los cuatro (o se han plantado los dos de una pareja). */
function cerrarOLance(state: MusState, playerId: number): MusState {
  const siguiente = clone(state);
  if (siguiente.players.every((p) => p.hablado)) {
    // Nadie envidó: el lance se decide comparando las manos.
    return resolverLance(siguiente);
  }
  void playerId;
  return siguiente;
}

/**
 * Resuelve el lance comparando las mejores jugadas de cada pareja.
 *
 * Se suman las piedras del envite (si lo hubo) a lo que vale la jugada: en pares, 1 por pareja,
 * 2 por medias y 3 por duples; en juego, 2 si no es 31 y 3 si es 31; en punto, 1 extra.
 */
function resolverLance(state: MusState): MusState {
  const siguiente = clone(state);
  const lance = siguiente.lance!;

  const mejorDe = (team: number): { seat: number; jugada: Jugada } => {
    const asientos = siguiente.teams[team].players;
    let mejor = { seat: asientos[0], jugada: siguiente.players[asientos[0]].jugada };
    for (const seat of asientos.slice(1)) {
      if (comparar(siguiente.players[seat].jugada, mejor.jugada, lance) > 0) {
        mejor = { seat, jugada: siguiente.players[seat].jugada };
      }
    }
    return mejor;
  };

  const a = mejorDe(0);
  const b = mejorDe(1);
  const cmp = comparar(a.jugada, b.jugada, lance);
  if (cmp === 0) {
    // Empate: no se lleva nadie las piedras del lance.
    siguiente.events = [...siguiente.events, { kind: 'nadie', lance }];
    return siguienteLance(siguiente);
  }

  const ganador = cmp > 0 ? 0 : 1;
  const gana = ganador === 0 ? a : b;

  const piedras = loQueVale(gana.jugada, lance) + siguiente.piedrasDelLance;
  siguiente.teams[ganador].piedras += piedras;
  siguiente.ganadorLance = ganador;
  siguiente.events = [
    ...siguiente.events,
    { kind: 'lance', lance, team: ganador, piedras },
  ];

  // Una pareja puede llegar a las 40 a mitad del recuento: ahí se acaba.
  if (comprobarFin(siguiente, ganador)) return siguiente;
  return siguienteLance(siguiente);
}

/**
 * Lo que vale la jugada en cada lance: en pares, 3 unas duples, 2 unas medias y 1 una pareja; en
 * juego, 3 si es la «una» (31), 2 otro juego y 1 si se ha ido al punto; en grande y chica, 2.
 */
function loQueVale(jugada: Jugada, lance: Lance): number {
  if (lance === 'pares') {
    return jugada.pares.categoria === 'duples' ? 3 : jugada.pares.categoria === 'medias' ? 2 : 1;
  }
  if (lance === 'juego') {
    if (jugada.juego === null) return 1; // se ha ido al punto
    return jugada.juego === 31 ? 3 : 2;
  }
  return 2;
}

/** Si la pareja ha llegado a las 40 piedras, se anota el juego (y la vaca si es el tercero). */
function comprobarFin(state: MusState, team: number): boolean {
  if (state.teams[team].piedras < PIEDRAS_PARA_GANAR) return false;
  state.teams[team].juegos += 1;
  state.events = [...state.events, { kind: 'game-end', team }];
  if (state.teams[team].juegos >= JUEGOS_POR_VACA) {
    state.phase = 'vaca-end';
    state.winner = team;
    state.events = [...state.events, { kind: 'vaca', team }];
  } else {
    state.phase = 'game-end';
  }
  return true;
}

function siguienteLance(state: MusState): MusState {
  const siguiente = clone(state);
  const actual = LANCES.indexOf(siguiente.lance ?? 'grande');
  const proximo = LANCES[actual + 1] ?? null;
  siguiente.lance = proximo;
  siguiente.habladoEnLance = [];
  siguiente.pasados = [];
  siguiente.envite = null;
  siguiente.responde = null;
  siguiente.piedrasDelLance = 0;
  siguiente.ganadorLance = null;
  for (const p of siguiente.players) p.hablado = false;
  if (proximo === null) {
    // Se han jugado los cuatro lances sin que nadie llegue a 40: se reparte otra mano.
    siguiente.phase = 'mus';
    siguiente.mano = (siguiente.mano + 1) % JUGADORES;
  }
  return siguiente;
}

/** Reparte la mano siguiente, conservando las piedras y los juegos. */
export function nextHand(state: MusState, rng?: () => number): MusState {
  const nueva = newGame({
    names: state.players.map((p) => p.name),
    bots: state.players.map((p) => p.isBot),
    piedras: [state.teams[0].piedras, state.teams[1].piedras],
    juegos: [state.teams[0].juegos, state.teams[1].juegos],
    mano: (state.mano + 1) % JUGADORES,
    rng,
  });
  return nueva;
}

// ── Lo que ve cada uno ────────────────────────────────────────────────────────

export interface MusView {
  players: { id: number; name: string; isBot: boolean; handCount: number; connected?: boolean }[];
  teams: { id: number; players: number[]; piedras: number; juegos: number }[];
  myHand: Card[];
  myJugada: Jugada;
  mano: number;
  phase: MusState['phase'];
  lance: Lance | null;
  /** En qué lances toca hablar. */
  turn: number | null;
  envite: Envite | null;
  responde: number | null;
  pasados: number[];
  /** Lo que le queda por decir en la fase de mus. */
  puedoHablar: boolean;
  /** La jugada de mi compañero (solo la veo yo). */
  companero: { id: number; name: string; jugada: Jugada } | null;
  events: MusEvent[];
  winner: number | null;
}

export function viewFor(state: MusState, seat: number): MusView {
  const yo = state.players[seat];
  const companeroSeat = state.teams[parejaDe(seat)].players.find((p) => p !== seat) ?? null;
  const companero = companeroSeat !== null ? state.players[companeroSeat] : null;

  return {
    players: state.players.map((p) => ({
      id: p.id,
      name: p.name,
      isBot: p.isBot,
      handCount: p.hand.length,
      connected: p.connected,
    })),
    teams: state.teams.map((t) => ({
      id: t.id,
      players: [...t.players],
      piedras: t.piedras,
      juegos: t.juegos,
    })),
    myHand: yo?.hand ?? [],
    myJugada: yo?.jugada ?? evaluar([]),
    mano: state.mano,
    phase: state.phase,
    lance: state.lance,
    turn: turnoActual(state),
    envite: state.envite,
    responde: state.responde,
    pasados: [...state.pasados],
    puedoHablar: !!yo && !yo.hablado && (state.phase === 'mus' || state.phase === 'lances'),
    companero: companero
      ? { id: companero.id, name: companero.name, jugada: companero.jugada }
      : null,
    events: state.events,
    winner: state.winner,
  };
}

/** A quién le toca hablar ahora (en el mus o en los lances). */
export function turnoActual(state: MusState): number | null {
  if (state.responde !== null) return state.responde;
  // Las tres fases en las que se habla van por el mismo orden: empezando por el mano.
  if (state.phase === 'mus' || state.phase === 'lances' || state.phase === 'descartar') {
    for (let i = 0; i < JUGADORES; i++) {
      const seat = turnoDe(state, i);
      if (!state.players[seat].hablado) return seat;
    }
  }
  return null;
}

