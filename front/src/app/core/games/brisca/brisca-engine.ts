/**
 * La Brisca, en reglas puras.
 *
 * El juego de bazas más popular de España. Se reparten 3 cartas a cada uno y se descubre la
 * siguiente, que marca el **triunfo**. Cada uno juega una carta —**sin obligación de asistir al
 * palo ni de jugar triunfo**, y ahí está la gracia—, gana la más alta del triunfo (o, si no hay
 * triunfo, la más alta del palo con el que se salió), y **el que gana roba primero y sale** en la
 * siguiente. Se acaba cuando no quedan cartas que robar ni cartas en la mano.
 *
 * Detalles que están en las normas y que se implementan tal cual:
 * - La carta que marca el triunfo es **la última que se roba**: se queda en la mesa hasta que el
 *   mazo se agota.
 * - Quien gana una baza puede **cambiar la carta que pinta por el siete** de ese palo, antes de
 *   robar y nunca después de la penúltima baza.
 * - Al contar, cada uno suma el valor de las cartas de sus bazas: As 11, tres 10, rey 4, caballo
 *   3, sota 2. **Si hay empate a 60, el juego se anula** (no lo gana nadie y se vuelve a repartir).
 *
 * Como todos los motores del proyecto: recibe estado y devuelve estado, sin tocar nada por dentro.
 */

import { Card, SpanishSuit, buildDeck, dealSome, shuffle } from '../baraja';
import { Baza, fuerza, ganadorDeBaza, ordenarMano, tantos } from '../bazas';

export const MIN_JUGADORES = 2;
export const MAX_JUGADORES = 4;
export const CARTAS_POR_JUGADOR = 3;
/** Juegos que hay que ganar para llevarse la partida. */
export const JUEGOS_POR_DEFECTO = 3;
/** Los 60 tantos son la mitad de la baraja: si los dos llegan, el juego se anula. */
export const TANTOS_DE_EMPATE = 60;

export interface BriscaPlayer {
  id: number;
  name: string;
  isBot: boolean;
  hand: Card[];
  /** Las cartas de las bazas que ha ganado. */
  won: Card[];
  /** Bazas ganadas en este juego (para el registro). */
  tricks: number;
  /** Los tantos ya contados. En local se sacan de `won`; con amigos los manda el servidor. */
  tantos?: number;
  connected?: boolean;
}

export type BriscaEvent =
  | { kind: 'deal'; trump: Card['id'] }
  | { kind: 'play'; player: number; card: Card['id'] }
  | { kind: 'trick'; winner: number; tantos: number }
  | { kind: 'swap'; player: number; card: Card['id'] }
  | { kind: 'game-end'; scores: number[]; anulado: boolean }
  | { kind: 'match-end'; winner: number };

export interface BriscaState {
  players: BriscaPlayer[];
  /** Lo que queda por robar. La carta que pinta **no** está aquí: está en la mesa. */
  deck: Card[];
  /** La carta descubierta que marca el triunfo, hasta que alguien se la lleve. */
  trumpCard: Card | null;
  trumpSuit: SpanishSuit;
  turn: number;
  /** La baza en curso. */
  trick: Baza[];
  /** La última baza resuelta, para poder contarla en la mesa. */
  lastTrick: { winner: number; cards: Baza[] } | null;
  /** Quién ganó la última baza: es el único que puede cambiar el triunfo. */
  lastWinner: number | null;
  /** Se puede cambiar el triunfo mientras no se haya jugado la penúltima baza. */
  swapPermitido: boolean;
  dealer: number;
  /** Tantos de cada uno en el juego en curso. */
  scores: number[];
  /** Juegos ganados por cada uno (el empate a 60 no lo gana nadie). */
  gamesWon: number[];
  targetGames: number;
  events: BriscaEvent[];
  phase: 'playing' | 'game-end' | 'match-end';
  winner: number | null;
}

export class BriscaError extends Error {
  constructor(
    public readonly code: string,
    message: string,
  ) {
    super(message);
    this.name = 'BriscaError';
  }
}

export function newGame(opts: {
  names: string[];
  bots?: boolean[];
  targetGames?: number;
  dealer?: number;
  gamesWon?: number[];
  rng?: () => number;
}): BriscaState {
  const nombres = opts.names;
  if (nombres.length < MIN_JUGADORES || nombres.length > MAX_JUGADORES) {
    throw new BriscaError(
      'players',
      `la brisca se juega entre ${MIN_JUGADORES} y ${MAX_JUGADORES} jugadores`,
    );
  }

  const mazo = shuffle(buildDeck(1), opts.rng);
  const { hands, rest } = dealSome(mazo, nombres.length, CARTAS_POR_JUGADOR);
  // La siguiente carta se descubre: es la que marca el triunfo y la última que se robará.
  const trumpCard = rest[0] ?? null;
  const deck = rest.slice(1);
  const dealer = opts.dealer ?? nombres.length - 1;

  return {
    players: nombres.map((name, id) => ({
      id,
      name,
      isBot: opts.bots?.[id] ?? false,
      hand: ordenarMano(hands[id]),
      won: [],
      tricks: 0,
    })),
    deck,
    trumpCard,
    trumpSuit: trumpCard?.suit ?? 'o',
    turn: (dealer + 1) % nombres.length,
    trick: [],
    lastTrick: null,
    lastWinner: null,
    swapPermitido: true,
    dealer,
    scores: nombres.map(() => 0),
    gamesWon: opts.gamesWon ? [...opts.gamesWon] : nombres.map(() => 0),
    targetGames: opts.targetGames ?? JUEGOS_POR_DEFECTO,
    events: trumpCard ? [{ kind: 'deal', trump: trumpCard.id }] : [],
    phase: 'playing',
    winner: null,
  };
}

function clone(state: BriscaState): BriscaState {
  return {
    ...state,
    players: state.players.map((p) => ({
      ...p,
      hand: [...p.hand],
      won: [...p.won],
    })),
    deck: [...state.deck],
    trick: [...state.trick],
    lastTrick: state.lastTrick
      ? { winner: state.lastTrick.winner, cards: [...state.lastTrick.cards] }
      : null,
    scores: [...state.scores],
    gamesWon: [...state.gamesWon],
    events: [...state.events],
  };
}

function jugador(state: BriscaState, id: number): BriscaPlayer {
  const p = state.players[id];
  if (!p) throw new BriscaError('unknown_player', 'ese jugador no está en la mesa');
  return p;
}

/**
 * Jugar una carta. No hay obligación de asistir ni de montar: cualquier carta vale.
 */
export function play(state: BriscaState, playerId: number, cardId: string): BriscaState {
  if (state.phase !== 'playing') {
    throw new BriscaError('not_playing', 'el juego ya ha terminado');
  }
  if (state.turn !== playerId) {
    throw new BriscaError('not_your_turn', 'ahora no te toca');
  }
  const yo = jugador(state, playerId);
  const carta = yo.hand.find((c) => c.id === cardId);
  if (!carta) {
    throw new BriscaError('not_your_card', 'esa carta no es tuya');
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
 * Cambiar la carta que marca el triunfo por el siete de ese palo.
 *
 * Solo puede hacerlo quien acaba de ganar una baza, **antes de robar** y nunca después de la
 * penúltima baza (que es cuando la carta que pinta está a punto de caer sola).
 */
export function cambiarTriunfo(state: BriscaState, playerId: number): BriscaState {
  if (state.phase !== 'playing') {
    throw new BriscaError('not_playing', 'el juego ya ha terminado');
  }
  if (state.lastWinner !== playerId) {
    throw new BriscaError('not_your_trick', 'solo puede cambiarlo quien acaba de ganar la baza');
  }
  if (!state.swapPermitido) {
    throw new BriscaError('too_late', 'ya no se puede cambiar el triunfo');
  }
  const carta = state.trumpCard;
  if (!carta) {
    throw new BriscaError('no_trump', 'ya no queda carta que pinta');
  }
  const yo = jugador(state, playerId);
  const siete = yo.hand.find((c) => c.rank === 7 && c.suit === carta.suit);
  if (!siete) {
    throw new BriscaError('no_seven', 'no tienes el siete de triunfo');
  }

  const siguiente = clone(state);
  const mio = siguiente.players[playerId];
  mio.hand = ordenarMano([...mio.hand.filter((c) => c.id !== siete.id), carta]);
  siguiente.trumpCard = siete;
  siguiente.events = [...siguiente.events, { kind: 'swap', player: playerId, card: siete.id }];
  return siguiente;
}

/** Se lleva la baza el que la ganó, y roba: primero él, después los demás. */
function resolverBaza(state: BriscaState): BriscaState {
  const ganador = ganadorDeBaza(state.trick, state.trumpSuit);
  const cartas = state.trick.map((j) => j.card);
  const siguiente = clone(state);
  const suyo = siguiente.players[ganador];
  suyo.won = [...suyo.won, ...cartas];
  suyo.tricks += 1;
  siguiente.lastTrick = { winner: ganador, cards: state.trick };
  siguiente.trick = [];
  siguiente.lastWinner = ganador;
  siguiente.events = [
    ...siguiente.events,
    { kind: 'trick', winner: ganador, tantos: tantos(cartas) },
  ];

  // Roba primero el que ha ganado la baza, y luego el resto por orden.
  const n = siguiente.players.length;
  for (let i = 0; i < n; i++) {
    const quien = (ganador + i) % n;
    robar(siguiente, quien);
  }

  // Ya no queda nada que robar: se acaba el juego (y se cuentan los tantos).
  const sinCartas = siguiente.players.every((p) => p.hand.length === 0);
  if (sinCartas && siguiente.deck.length === 0 && siguiente.trumpCard === null) {
    return terminarJuego(siguiente);
  }

  // Quien ganó la baza sale en la siguiente.
  siguiente.turn = ganador;
  // El cambio del triunfo se corta al jugar la penúltima baza.
  siguiente.swapPermitido = siguiente.deck.length > 1;
  return siguiente;
}

/** Roba del mazo; y cuando el mazo se agota, la carta que pinta es la última. */
function robar(state: BriscaState, playerId: number): void {
  const jugadorActual = state.players[playerId];
  if (state.deck.length > 0) {
    const [carta, ...resto] = state.deck;
    jugadorActual.hand = ordenarMano([...jugadorActual.hand, carta]);
    state.deck = resto;
    return;
  }
  if (state.trumpCard) {
    jugadorActual.hand = ordenarMano([...jugadorActual.hand, state.trumpCard]);
    state.trumpCard = null;
  }
}

function terminarJuego(state: BriscaState): BriscaState {
  const siguiente = clone(state);
  siguiente.scores = siguiente.players.map((p) => tantos(p.won));
  const [a, b] = siguiente.scores;
  // Empate a 60: el juego se anula, no lo gana nadie.
  const anulado = siguiente.players.length === 2 && a === b && a === TANTOS_DE_EMPATE;
  let ganador: number | null = null;
  if (!anulado) {
    const maximo = Math.max(...siguiente.scores);
    const empatados = siguiente.scores.filter((s) => s === maximo).length;
    if (empatados === 1) ganador = siguiente.scores.indexOf(maximo);
  }
  if (ganador !== null) {
    siguiente.gamesWon[ganador] += 1;
  }
  siguiente.events = [
    ...siguiente.events,
    { kind: 'game-end', scores: siguiente.scores, anulado },
  ];
  siguiente.winner = ganador;

  const campeon = siguiente.gamesWon.findIndex((g) => g >= siguiente.targetGames);
  if (campeon !== -1) {
    siguiente.phase = 'match-end';
    siguiente.winner = campeon;
    siguiente.events = [...siguiente.events, { kind: 'match-end', winner: campeon }];
    return siguiente;
  }
  siguiente.phase = 'game-end';
  return siguiente;
}

/** Reparte el juego siguiente. Solo tiene sentido cuando el anterior ha terminado. */
export function nextGame(state: BriscaState, rng?: () => number): BriscaState {
  if (state.phase !== 'game-end') {
    throw new BriscaError('not_finished', 'el juego anterior todavía no ha terminado');
  }
  return newGame({
    names: state.players.map((p) => p.name),
    bots: state.players.map((p) => p.isBot),
    targetGames: state.targetGames,
    dealer: (state.dealer + 1) % state.players.length,
    gamesWon: state.gamesWon,
    rng,
  });
}

/** Lo que ve un jugador: su mano y sus bazas, y de los demás solo el recuento. */
export interface BriscaView {
  players: {
    id: number;
    name: string;
    isBot: boolean;
    handCount: number;
    tantos: number;
    tricks: number;
    connected?: boolean;
  }[];
  myHand: Card[];
  myWon: Card[];
  trumpCard: Card | null;
  trumpSuit: SpanishSuit;
  deckCount: number;
  turn: number;
  trick: Baza[];
  lastTrick: { winner: number; cards: Baza[] } | null;
  lastWinner: number | null;
  swapPermitido: boolean;
  scores: number[];
  gamesWon: number[];
  targetGames: number;
  events: BriscaEvent[];
  phase: BriscaState['phase'];
  winner: number | null;
}

export function viewFor(state: BriscaState, seat: number): BriscaView {
  const yo = state.players[seat];
  return {
    players: state.players.map((p) => ({
      id: p.id,
      name: p.name,
      isBot: p.isBot,
      handCount: p.hand.length,
      tantos: tantos(p.won),
      tricks: p.tricks,
      connected: p.connected,
    })),
    myHand: yo?.hand ?? [],
    myWon: yo?.won ?? [],
    trumpCard: state.trumpCard,
    trumpSuit: state.trumpSuit,
    deckCount: state.deck.length,
    turn: state.turn,
    trick: state.trick,
    lastTrick: state.lastTrick,
    lastWinner: state.lastWinner,
    swapPermitido: state.swapPermitido,
    scores: state.scores,
    gamesWon: state.gamesWon,
    targetGames: state.targetGames,
    events: state.events,
    phase: state.phase,
    winner: state.winner,
  };
}

/** ¿Puede este jugador cambiar el triunfo ahora mismo? */
export function puedeCambiarTriunfo(state: BriscaState, playerId: number): boolean {
  if (!state.swapPermitido || state.lastWinner !== playerId || !state.trumpCard) return false;
  return state.players[playerId].hand.some(
    (c) => c.rank === 7 && c.suit === state.trumpCard?.suit,
  );
}

/** Fuerza de una carta, expuesta para los bots y para la mesa. */
export { fuerza };
