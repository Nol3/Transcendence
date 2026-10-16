/**
 * El Mentiroso, en reglas puras.
 *
 * Se reparte **toda** la baraja. Por turnos, cada uno echa una o varias cartas **boca abajo**
 * y dice qué son: puede mentir en el **valor**, nunca en la **cantidad** (la cantidad que
 * anuncia es la que pone). El valor que se anuncia lo fija quien abre la ronda y los demás lo
 * siguen. Cualquier jugador —no solo el siguiente— puede gritar «¡mentiroso!»:
 *
 * - Si el que puso decía la verdad, **se lleva el montón el que desconfió**.
 * - Si mentía, **se lo lleva el que puso**.
 *
 * Quien se lleva el montón abre la ronda siguiente, y gana la mano quien se queda sin cartas.
 * El servidor es quien sabe las cartas de verdad, así que resolver la desconfianza no tiene
 * trampa posible: es justo el juego que mejor le sienta a un servidor autoritativo.
 *
 * Como todos los motores del proyecto: recibe estado y devuelve estado, sin tocar nada por
 * dentro. Así se prueba sin navegador y el servidor puede usarlo tal cual.
 */

import { Card, SpanishRank, buildDeck, deal, shuffle } from '../baraja';

export const MIN_JUGADORES = 3;
export const MAX_JUGADORES = 6;
/** Manos ganadas que hacen falta para llevarse la partida. */
export const MANOS_POR_DEFECTO = 3;

export interface MentirosoPlayer {
  id: number;
  name: string;
  isBot: boolean;
  hand: Card[];
  /** Los cuatro iguales que ha retirado de la mesa (van aparte, ya no juegan). */
  retired: Card[];
  /** Manos ganadas en esta partida. */
  wins: number;
  /** Online: si sigue conectado. En local siempre es `true`. */
  connected?: boolean;
}

/** Lo último que se puso boca abajo, que es lo que se puede desconfiar. */
export interface MentirosoPlay {
  player: number;
  cards: Card[];
  claimedRank: SpanishRank;
}

export type MentirosoEvent =
  | { kind: 'play'; player: number; count: number; claimedRank: SpanishRank }
  | { kind: 'challenge'; player: number; against: number }
  | { kind: 'take'; player: number; count: number; mentira: boolean }
  | { kind: 'retire'; player: number; rank: SpanishRank }
  | { kind: 'out'; player: number; wins: number };

export interface MentirosoState {
  players: MentirosoPlayer[];
  /** El montón del centro, boca abajo. */
  pile: Card[];
  /** El valor que hay que seguir en esta ronda; `null` si el que abre aún no lo ha dicho. */
  claimedRank: SpanishRank | null;
  turn: number;
  lastPlay: MentirosoPlay | null;
  /** Manos jugadas (empieza en 1). */
  hand: number;
  targetWins: number;
  events: MentirosoEvent[];
  phase: 'playing' | 'hand-end' | 'match-end';
  /** Quién ganó la mano, cuando ya ha terminado. */
  winner: number | null;
}

/** Un movimiento imposible. Lleva código corto para que el servidor pueda traducirlo. */
export class MentirosoError extends Error {
  constructor(
    public readonly code: string,
    message: string,
  ) {
    super(message);
    this.name = 'MentirosoError';
  }
}

export function newGame(opts: {
  names: string[];
  bots?: boolean[];
  targetWins?: number;
  rng?: () => number;
}): MentirosoState {
  const nombres = opts.names;
  if (nombres.length < MIN_JUGADORES || nombres.length > MAX_JUGADORES) {
    throw new MentirosoError(
      'players',
      `el mentiroso se juega entre ${MIN_JUGADORES} y ${MAX_JUGADORES} jugadores`,
    );
  }

  const mazo = shuffle(buildDeck(1), opts.rng);
  const manos = deal(mazo, nombres.length);

  return {
    players: nombres.map((name, id) => ({
      id,
      name,
      isBot: opts.bots?.[id] ?? false,
      hand: manos[id],
      retired: [],
      wins: 0,
    })),
    pile: [],
    claimedRank: null,
    turn: 0,
    lastPlay: null,
    hand: 1,
    targetWins: opts.targetWins ?? MANOS_POR_DEFECTO,
    events: [],
    phase: 'playing',
    winner: null,
  };
}

/** Copia profunda del estado, que es lo que devuelven todas las acciones. */
function clone(state: MentirosoState): MentirosoState {
  return {
    ...state,
    players: state.players.map((p) => ({
      ...p,
      hand: [...p.hand],
      retired: [...p.retired],
    })),
    pile: [...state.pile],
    events: [...state.events],
    lastPlay: state.lastPlay
      ? { ...state.lastPlay, cards: [...state.lastPlay.cards] }
      : null,
  };
}

function jugador(state: MentirosoState, id: number): MentirosoPlayer {
  const p = state.players[id];
  if (!p) throw new MentirosoError('unknown_player', 'ese jugador no está en la mesa');
  return p;
}

/**
 * Poner cartas boca abajo diciendo qué son.
 *
 * `cardIds` son cartas **de tu mano**. `claimedRank` es lo que dices que son: si abres la
 * ronda, lo eliges tú; si no, tiene que ser el mismo que el que hay en la mesa (mentir sobre
 * el valor es el juego; cambiar el valor que se sigue, no).
 */
export function play(
  state: MentirosoState,
  playerId: number,
  cardIds: string[],
  claimedRank?: SpanishRank,
): MentirosoState {
  if (state.phase !== 'playing') {
    throw new MentirosoError('not_playing', 'la mano ya ha terminado');
  }
  if (state.turn !== playerId) {
    throw new MentirosoError('not_your_turn', 'ahora no te toca');
  }
  if (cardIds.length === 0) {
    throw new MentirosoError('no_cards', 'hay que poner al menos una carta');
  }

  const yo = jugador(state, playerId);
  const cartas: Card[] = [];
  for (const id of cardIds) {
    const carta = yo.hand.find((c) => c.id === id);
    if (!carta) {
      throw new MentirosoError('not_your_card', 'esa carta no es tuya');
    }
    cartas.push(carta);
  }

  // El valor que se sigue: lo fija quien abre, y los demás lo respetan.
  const valor = state.claimedRank ?? claimedRank;
  if (valor === undefined || valor === null) {
    throw new MentirosoError('no_rank', 'hay que decir qué cartas son');
  }
  if (state.claimedRank !== null && claimedRank !== undefined && claimedRank !== state.claimedRank) {
    throw new MentirosoError('rank_changed', 'hay que seguir el valor que hay en la mesa');
  }

  const siguiente = clone(state);
  const mio = siguiente.players[playerId];
  mio.hand = mio.hand.filter((c) => !cardIds.includes(c.id));
  siguiente.pile = [...siguiente.pile, ...cartas];
  siguiente.claimedRank = valor;
  siguiente.lastPlay = { player: playerId, cards: cartas, claimedRank: valor };
  siguiente.events = [
    ...siguiente.events,
    { kind: 'play', player: playerId, count: cartas.length, claimedRank: valor },
  ];

  // Si se ha quedado sin cartas, gana la mano: a quien no tiene cartas no se le desconfía.
  if (mio.hand.length === 0) {
    return terminarMano(siguiente, playerId);
  }

  siguiente.turn = (playerId + 1) % siguiente.players.length;
  return siguiente;
}

/**
 * Gritar «¡mentiroso!».
 *
 * Puede hacerlo **cualquiera**, no solo el siguiente. Si el que puso decía la verdad, se
 * lleva el montón quien desconfió; si mentía, se lo lleva quien puso. Y en los dos casos,
 * quien se lleva el montón abre la ronda siguiente.
 */
export function desconfiar(state: MentirosoState, challengerId: number): MentirosoState {
  if (state.phase !== 'playing') {
    throw new MentirosoError('not_playing', 'la mano ya ha terminado');
  }
  const ultima = state.lastPlay;
  if (!ultima) {
    throw new MentirosoError('nothing_to_challenge', 'todavía no hay nada que desconfiar');
  }
  const acusador = jugador(state, challengerId);
  if (acusador.id === ultima.player) {
    throw new MentirosoError('self_challenge', 'no te puedes desconfiar a ti mismo');
  }
  // A quien se ha quedado sin cartas no se le puede desconfiar.
  if (jugador(state, ultima.player).hand.length === 0) {
    throw new MentirosoError('player_out', 'a quien se ha quedado sin cartas no se le desconfía');
  }

  const mentira = ultima.cards.some((c) => c.rank !== ultima.claimedRank);
  const seLleva = mentira ? ultima.player : challengerId;

  const siguiente = clone(state);
  const cuantas = siguiente.pile.length;
  siguiente.players[seLleva].hand = [...siguiente.players[seLleva].hand, ...siguiente.pile];
  siguiente.pile = [];
  siguiente.claimedRank = null;
  siguiente.lastPlay = null;
  siguiente.turn = seLleva;
  siguiente.events = [
    ...siguiente.events,
    { kind: 'challenge', player: challengerId, against: ultima.player },
    { kind: 'take', player: seLleva, count: cuantas, mentira },
  ];
  return siguiente;
}

/**
 * Retirar los cuatro iguales (variante española).
 *
 * Cuando alguien reúne las cuatro cartas de un mismo valor puede enseñarlas y sacarlas del
 * juego. Es una decisión suya, no una obligación: sirve para quitarse de encima cartas que
 * ya no le valen.
 */
export function retirar(state: MentirosoState, playerId: number, rank: SpanishRank): MentirosoState {
  if (state.phase !== 'playing') {
    throw new MentirosoError('not_playing', 'la mano ya ha terminado');
  }
  const yo = jugador(state, playerId);
  const cuatro = yo.hand.filter((c) => c.rank === rank);
  if (cuatro.length < 4) {
    throw new MentirosoError('not_four', 'hacen falta las cuatro cartas del mismo valor');
  }

  const siguiente = clone(state);
  const mio = siguiente.players[playerId];
  mio.hand = mio.hand.filter((c) => c.rank !== rank);
  mio.retired = [...mio.retired, ...cuatro];
  siguiente.events = [...siguiente.events, { kind: 'retire', player: playerId, rank }];

  if (mio.hand.length === 0) {
    return terminarMano(siguiente, playerId);
  }
  // Si retira sin ser su turno, el turno no se mueve.
  return siguiente;
}

function terminarMano(state: MentirosoState, ganador: number): MentirosoState {
  const siguiente = clone(state);
  siguiente.players[ganador].wins += 1;
  siguiente.phase = siguiente.players[ganador].wins >= siguiente.targetWins ? 'match-end' : 'hand-end';
  siguiente.winner = ganador;
  siguiente.events = [
    ...siguiente.events,
    { kind: 'out', player: ganador, wins: siguiente.players[ganador].wins },
  ];
  return siguiente;
}

/** Reparte la mano siguiente. Solo tiene sentido cuando la anterior ha terminado. */
export function nextHand(state: MentirosoState, rng?: () => number): MentirosoState {
  if (state.phase !== 'hand-end') {
    throw new MentirosoError('not_finished', 'la mano anterior todavía no ha terminado');
  }
  const mazo = shuffle(buildDeck(1), rng);
  const manos = deal(mazo, state.players.length);

  return {
    ...clone(state),
    players: state.players.map((p, i) => ({
      ...p,
      hand: manos[i],
      retired: [],
      isBot: p.isBot,
      wins: p.wins,
      connected: p.connected,
    })),
    pile: [],
    claimedRank: null,
    turn: state.winner ?? 0,
    lastPlay: null,
    hand: state.hand + 1,
    events: [],
    phase: 'playing',
    winner: null,
  };
}

/** Quién sigue en pie y cuántas cartas le quedan, para pintar la mesa. */
export function cartasDe(state: MentirosoState, playerId: number): number {
  return state.players[playerId]?.hand.length ?? 0;
}

/**
 * Lo que ve un jugador: su mano entera y, de los demás, solo cuántas cartas les quedan.
 * El montón no se revela nunca (eso es el juego); lo que sí se ve es el valor que se sigue.
 */
export interface MentirosoView {
  players: { id: number; name: string; isBot: boolean; handCount: number; wins: number; connected?: boolean }[];
  myHand: Card[];
  claimedRank: SpanishRank | null;
  pileCount: number;
  turn: number;
  hand: number;
  targetWins: number;
  events: MentirosoEvent[];
  phase: MentirosoState['phase'];
  winner: number | null;
  /** Solo cuando la mano ha terminado: qué se llevó el que desconfió. */
  lastResult: { mentira: boolean; player: number } | null;
}

export function viewFor(state: MentirosoState, seat: number): MentirosoView {
  const ultimo = [...state.events].reverse().find((e) => e.kind === 'take');
  return {
    players: state.players.map((p) => ({
      id: p.id,
      name: p.name,
      isBot: p.isBot,
      handCount: p.hand.length,
      wins: p.wins,
      connected: p.connected,
    })),
    myHand: state.players[seat]?.hand ?? [],
    claimedRank: state.claimedRank,
    pileCount: state.pile.length,
    turn: state.turn,
    hand: state.hand,
    targetWins: state.targetWins,
    events: state.events,
    phase: state.phase,
    winner: state.winner,
    lastResult: ultimo ? { mentira: ultimo.kind === 'take' ? ultimo.mentira : false, player: 0 } : null,
  };
}
