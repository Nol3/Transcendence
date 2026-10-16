/**
 * El Tute, en reglas puras.
 *
 * Como la brisca, es un juego de bazas, pero aquí **sí estás obligado** a jugar de una manera
 * concreta, y esa obligación cambia a mitad del juego:
 *
 * - **Mientras quede baceta** (cartas por repartir): solo es obligatorio asistir al **triunfo**,
 *   y sin necesidad de montar. Cualquier otra carta vale.
 * - **Terminada la baceta**: obligatorio **asistir, montar y fallar** — si puedes seguir el palo
 *   tienes que hacerlo, y si puedes superar la carta más alta de la mesa, también; si no tienes
 *   del palo, tienes que jugar triunfo.
 *
 * Y además se **canta**: rey y caballo del mismo palo en la mano valen 40 tantos si son del palo
 * de triunfo («las cuarenta») y 20 si son de otro («las veinte»). Solo se pueden cantar **después
 * de ganar una baza**, y un acuse por baza.
 *
 * Se gana el juego llegando a **101 tantos**, o cantando un **tute** (los cuatro reyes o los cuatro
 * caballos), que gana al instante. La **última baza vale 10** («las diez últimas»), y decide los
 * empates.
 *
 * Como todos los motores del proyecto: recibe estado y devuelve estado, sin tocar nada por dentro.
 */

import { Card, SpanishSuit, buildDeck, dealSome, shuffle } from '../baraja';
import { Baza, fuerza, ganadorDeBaza, ordenarMano, tantos } from '../bazas';

export const MIN_JUGADORES = 2;
export const MAX_JUGADORES = 4;
/** Los tantos que hay que reunir para ganar el juego. */
export const TANTOS_PARA_GANAR = 101;
/** Ganar la última baza vale esto (y decide los empates). */
export const DIEZ_ULTIMAS = 10;
/** Los acuses: rey + caballo del mismo palo. */
export const ACUSE_TRIUNFO = 40;
export const ACUSE_OTRO = 20;

export interface TutePlayer {
  id: number;
  name: string;
  isBot: boolean;
  hand: Card[];
  /** Cartas de las bazas ganadas. */
  won: Card[];
  /** Tantos ya cantados con acuses en este juego. */
  cantados: number;
  /** Los tantos ya contados. En local se sacan de `won`; con amigos los manda el servidor. */
  tantos?: number;
  connected?: boolean;
}

export type TuteEvent =
  | { kind: 'deal'; trump: Card['id'] }
  | { kind: 'play'; player: number; card: Card['id'] }
  | { kind: 'trick'; winner: number; tantos: number }
  | { kind: 'acuse'; player: number; suit: SpanishSuit; puntos: number; cuarenta: boolean }
  | { kind: 'tute'; player: number }
  | { kind: 'game-end'; scores: number[]; ultima: number }
  | { kind: 'match-end'; winner: number };

export interface TuteState {
  players: TutePlayer[];
  /** De dónde se roba. La carta que pinta va debajo. */
  baceta: Card[];
  trumpCard: Card | null;
  trumpSuit: SpanishSuit;
  turn: number;
  trick: Baza[];
  lastTrick: { winner: number; cards: Baza[] } | null;
  /** Quién ganó la última baza: es quien puede cantar. */
  lastWinner: number | null;
  /** Acuses ya cantados en esta baza (uno por baza y jugador). */
  cantadoEnEstaBaza: number[];
  /** La baza que se acaba de jugar es la última del juego. */
  esUltimaBaza: boolean;
  /** Tantos acumulados de la partida (varios juegos). */
  scores: number[];
  targetTantos: number;
  events: TuteEvent[];
  phase: 'playing' | 'game-end' | 'match-end';
  winner: number | null;
}

export class TuteError extends Error {
  constructor(
    public readonly code: string,
    message: string,
  ) {
    super(message);
    this.name = 'TuteError';
  }
}

/** Cartas que hay que repartir a cada uno según cuántos juegan. */
export function cartasPorJugador(jugadores: number): number {
  if (jugadores <= 2) return 8;
  if (jugadores === 3) return 13; // el «tute arrastrado»
  return 10; // cuatro, por parejas
}

export function newGame(opts: {
  names: string[];
  bots?: boolean[];
  scores?: number[];
  dealer?: number;
  rng?: () => number;
}): TuteState {
  const nombres = opts.names;
  if (nombres.length < MIN_JUGADORES || nombres.length > MAX_JUGADORES) {
    throw new TuteError(
      'players',
      `el tute se juega entre ${MIN_JUGADORES} y ${MAX_JUGADORES} jugadores`,
    );
  }

  const mazo = shuffle(buildDeck(1), opts.rng);
  const { hands, rest } = dealSome(mazo, nombres.length, cartasPorJugador(nombres.length));
  // La carta que pinta queda debajo de la baceta: es la última que se roba.
  const trumpCard = rest[0] ?? null;
  const baceta = rest.slice(1);

  return {
    players: nombres.map((name, id) => ({
      id,
      name,
      isBot: opts.bots?.[id] ?? false,
      hand: ordenarMano(hands[id]),
      won: [],
      cantados: 0,
    })),
    baceta,
    trumpCard,
    trumpSuit: trumpCard?.suit ?? 'o',
    turn: (opts.dealer ?? nombres.length - 1) + 1 > nombres.length - 1
      ? 0
      : (opts.dealer ?? nombres.length - 1) + 1,
    trick: [],
    lastTrick: null,
    lastWinner: null,
    cantadoEnEstaBaza: [],
    esUltimaBaza: false,
    scores: opts.scores ? [...opts.scores] : nombres.map(() => 0),
    targetTantos: TANTOS_PARA_GANAR,
    events: trumpCard ? [{ kind: 'deal', trump: trumpCard.id }] : [],
    phase: 'playing',
    winner: null,
  };
}

function clone(state: TuteState): TuteState {
  return {
    ...state,
    players: state.players.map((p) => ({
      ...p,
      hand: [...p.hand],
      won: [...p.won],
    })),
    baceta: [...state.baceta],
    trick: [...state.trick],
    lastTrick: state.lastTrick
      ? { winner: state.lastTrick.winner, cards: [...state.lastTrick.cards] }
      : null,
    cantadoEnEstaBaza: [...state.cantadoEnEstaBaza],
    scores: [...state.scores],
    events: [...state.events],
  };
}

function jugador(state: TuteState, id: number): TutePlayer {
  const p = state.players[id];
  if (!p) throw new TuteError('unknown_player', 'ese jugador no está en la mesa');
  return p;
}

/**
 * Qué cartas se pueden jugar ahora mismo. Aquí está el juego de verdad.
 *
 * Mientras quede baceta solo obliga el triunfo (y sin montar); después hay que asistir, montar
 * y fallar. Si no tienes del palo y tampoco triunfo, vale cualquier carta (contrafallo).
 */
export function jugadasLegales(state: TuteState, playerId: number): Card[] {
  const mano = jugador(state, playerId).hand;
  const baza = state.trick;
  const triunfo = state.trumpSuit;
  if (baza.length === 0) return mano; // sale el primero: cualquier carta vale

  const paloSalida = baza[0].card.suit;
  const triunfos = mano.filter((c) => c.suit === triunfo);

  // Mientras quede baceta: solo es obligatorio asistir al palo de triunfo, sin montar.
  if (state.baceta.length > 0) {
    if (paloSalida !== triunfo) return mano;
    return triunfos.length > 0 ? triunfos : mano;
  }

  // Terminada la baceta: asistir, montar y fallar.
  const delPalo = mano.filter((c) => c.suit === paloSalida);
  if (delPalo.length > 0) {
    const maxima = Math.max(
      ...baza.filter((j) => j.card.suit === paloSalida).map((j) => fuerza(j.card)),
    );
    const queMontan = delPalo.filter((c) => fuerza(c) > maxima);
    return queMontan.length > 0 ? queMontan : delPalo;
  }
  // No tiene del palo: obligatorio fallar (jugar triunfo) si tiene.
  return triunfos.length > 0 ? triunfos : mano;
}

/** ¿Es legal esta carta ahora mismo? */
export function esJugadaLegal(state: TuteState, playerId: number, cardId: string): boolean {
  return jugadasLegales(state, playerId).some((c) => c.id === cardId);
}

export function play(state: TuteState, playerId: number, cardId: string): TuteState {
  if (state.phase !== 'playing') {
    throw new TuteError('not_playing', 'el juego ya ha terminado');
  }
  if (state.turn !== playerId) {
    throw new TuteError('not_your_turn', 'ahora no te toca');
  }
  const carta = jugador(state, playerId).hand.find((c) => c.id === cardId);
  if (!carta) {
    throw new TuteError('not_your_card', 'esa carta no es tuya');
  }
  if (!esJugadaLegal(state, playerId, cardId)) {
    throw new TuteError('must_follow', 'tienes que asistir, montar o fallar');
  }

  const siguiente = clone(state);
  const mio = siguiente.players[playerId];
  mio.hand = mio.hand.filter((c) => c.id !== cardId);
  siguiente.trick = [...siguiente.trick, { player: playerId, card: carta }];
  siguiente.events = [...siguiente.events, { kind: 'play', player: playerId, card: carta.id }];
  siguiente.lastWinner = null;

  if (siguiente.trick.length < siguiente.players.length) {
    siguiente.turn = (playerId + 1) % siguiente.players.length;
    return siguiente;
  }
  return resolverBaza(siguiente);
}

/**
 * Cantar un acuse: rey y caballo del mismo palo.
 *
 * Solo se puede **después de ganar una baza**, y un acuse por baza. Vale 40 si es del palo de
 * triunfo («las cuarenta») y 20 si es de otro («las veinte»).
 */
export function cantar(state: TuteState, playerId: number, suit: SpanishSuit): TuteState {
  if (state.phase !== 'playing') {
    throw new TuteError('not_playing', 'el juego ya ha terminado');
  }
  if (state.lastWinner !== playerId) {
    throw new TuteError('not_your_trick', 'solo se puede cantar después de ganar una baza');
  }
  if (state.cantadoEnEstaBaza.includes(playerId)) {
    throw new TuteError('already_sung', 'solo se puede cantar un acuse por baza');
  }
  const mano = jugador(state, playerId).hand;
  const tieneRey = mano.some((c) => c.suit === suit && c.rank === 12);
  const tieneCaballo = mano.some((c) => c.suit === suit && c.rank === 11);
  if (!tieneRey || !tieneCaballo) {
    throw new TuteError('no_acuse', 'no tienes rey y caballo de ese palo');
  }

  const cuarenta = suit === state.trumpSuit;
  const puntos = cuarenta ? ACUSE_TRIUNFO : ACUSE_OTRO;
  const siguiente = clone(state);
  siguiente.players[playerId].cantados += puntos;
  siguiente.cantadoEnEstaBaza = [...siguiente.cantadoEnEstaBaza, playerId];
  siguiente.events = [
    ...siguiente.events,
    { kind: 'acuse', player: playerId, suit, puntos, cuarenta },
  ];
  return siguiente;
}

/** ¿Puede cantar este jugador ahora mismo, y por qué palo? */
export function acusesDisponibles(state: TuteState, playerId: number): SpanishSuit[] {
  if (state.lastWinner !== playerId || state.cantadoEnEstaBaza.includes(playerId)) return [];
  const mano = jugador(state, playerId).hand;
  const palos: SpanishSuit[] = [];
  for (const suit of ['o', 'c', 'e', 'b'] as SpanishSuit[]) {
    const rey = mano.some((c) => c.suit === suit && c.rank === 12);
    const caballo = mano.some((c) => c.suit === suit && c.rank === 11);
    if (rey && caballo) palos.push(suit);
  }
  return palos;
}

/** ¿Tiene un tute (los cuatro reyes o los cuatro caballos)? Eso gana al instante. */
export function tieneTute(state: TuteState, playerId: number): boolean {
  const mano = jugador(state, playerId).hand;
  for (const rank of [12, 11] as const) {
    const palos = new Set(mano.filter((c) => c.rank === rank).map((c) => c.suit));
    if (palos.size === 4) return true;
  }
  return false;
}

/** Cantar el tute: gana el juego al instante. */
export function cantarTute(state: TuteState, playerId: number): TuteState {
  if (!tieneTute(state, playerId)) {
    throw new TuteError('no_tute', 'no tienes los cuatro reyes ni los cuatro caballos');
  }
  const siguiente = clone(state);
  siguiente.events = [...siguiente.events, { kind: 'tute', player: playerId }];
  siguiente.winner = playerId;
  siguiente.phase = 'match-end';
  return siguiente;
}

function resolverBaza(state: TuteState): TuteState {
  const ganador = ganadorDeBaza(state.trick, state.trumpSuit);
  const cartas = state.trick.map((j) => j.card);
  const siguiente = clone(state);
  const suyo = siguiente.players[ganador];
  suyo.won = [...suyo.won, ...cartas];
  siguiente.lastTrick = { winner: ganador, cards: state.trick };
  siguiente.trick = [];
  siguiente.lastWinner = ganador;
  siguiente.cantadoEnEstaBaza = [];
  siguiente.events = [
    ...siguiente.events,
    { kind: 'trick', winner: ganador, tantos: tantos(cartas) },
  ];

  // Roba primero el que ha ganado, y luego el resto. La carta que pinta es la última.
  const n = siguiente.players.length;
  for (let i = 0; i < n; i++) {
    robar(siguiente, (ganador + i) % n);
  }

  const sinCartas = siguiente.players.every((p) => p.hand.length === 0);
  const sinBaceta = siguiente.baceta.length === 0 && siguiente.trumpCard === null;
  if (sinCartas && sinBaceta) {
    siguiente.esUltimaBaza = true;
    return terminarJuego(siguiente, ganador);
  }

  siguiente.turn = ganador;
  return siguiente;
}

function robar(state: TuteState, playerId: number): void {
  const jugadorActual = state.players[playerId];
  if (state.baceta.length > 0) {
    const [carta, ...resto] = state.baceta;
    jugadorActual.hand = ordenarMano([...jugadorActual.hand, carta]);
    state.baceta = resto;
    return;
  }
  if (state.trumpCard) {
    jugadorActual.hand = ordenarMano([...jugadorActual.hand, state.trumpCard]);
    state.trumpCard = null;
  }
}

function terminarJuego(state: TuteState, ganadorUltima: number): TuteState {
  const siguiente = clone(state);
  // Los tantos se **acumulan** entre juegos: la partida va a 101 y se llega sumando juegos.
  // Antes se escribían solo los de este juego, así que `scores` nunca pasaba de ~100 y el
  // final de partida de unas líneas más abajo era inalcanzable.
  siguiente.scores = siguiente.players.map(
    (p) =>
      (state.scores[p.id] ?? 0) +
      tantos(p.won) +
      p.cantados +
      (p.id === ganadorUltima ? DIEZ_ULTIMAS : 0),
  );
  siguiente.events = [
    ...siguiente.events,
    { kind: 'game-end', scores: [...siguiente.scores], ultima: ganadorUltima },
  ];

  const campeon = siguiente.scores.findIndex((s) => s >= siguiente.targetTantos);
  if (campeon !== -1) {
    siguiente.phase = 'match-end';
    siguiente.winner = campeon;
    siguiente.events = [...siguiente.events, { kind: 'match-end', winner: campeon }];
    return siguiente;
  }
  siguiente.phase = 'game-end';
  siguiente.winner = null;
  return siguiente;
}

/** Reparte el juego siguiente, sumando los tantos de este. */
export function nextGame(state: TuteState, rng?: () => number): TuteState {
  if (state.phase !== 'game-end') {
    throw new TuteError('not_finished', 'el juego anterior todavía no ha terminado');
  }
  return newGame({
    names: state.players.map((p) => p.name),
    bots: state.players.map((p) => p.isBot),
    scores: state.scores,
    rng,
  });
}

/** Lo que ve un jugador: su mano y sus bazas, y de los demás solo el recuento. */
export interface TuteView {
  players: {
    id: number;
    name: string;
    isBot: boolean;
    handCount: number;
    tantos: number;
    cantados: number;
    connected?: boolean;
  }[];
  myHand: Card[];
  myWon: Card[];
  trumpCard: Card | null;
  trumpSuit: SpanishSuit;
  bacetaCount: number;
  turn: number;
  trick: Baza[];
  lastTrick: { winner: number; cards: Baza[] } | null;
  lastWinner: number | null;
  jugadasLegales: string[];
  acuses: SpanishSuit[];
  puedeTute: boolean;
  obligaMontar: boolean;
  scores: number[];
  targetTantos: number;
  events: TuteEvent[];
  phase: TuteState['phase'];
  winner: number | null;
}

export function viewFor(state: TuteState, seat: number): TuteView {
  const yo = state.players[seat];
  return {
    players: state.players.map((p) => ({
      id: p.id,
      name: p.name,
      isBot: p.isBot,
      handCount: p.hand.length,
      tantos: tantos(p.won),
      cantados: p.cantados,
      connected: p.connected,
    })),
    myHand: yo?.hand ?? [],
    myWon: yo?.won ?? [],
    trumpCard: state.trumpCard,
    trumpSuit: state.trumpSuit,
    bacetaCount: state.baceta.length,
    turn: state.turn,
    trick: state.trick,
    lastTrick: state.lastTrick,
    lastWinner: state.lastWinner,
    jugadasLegales: yo ? jugadasLegales(state, seat).map((c) => c.id) : [],
    acuses: yo ? acusesDisponibles(state, seat) : [],
    puedeTute: yo ? tieneTute(state, seat) : false,
    obligaMontar: state.baceta.length === 0,
    scores: state.scores,
    targetTantos: state.targetTantos,
    events: state.events,
    phase: state.phase,
    winner: state.winner,
  };
}
