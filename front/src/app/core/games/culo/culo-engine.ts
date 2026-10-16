/**
 * Reglas del Culo (Presidente).
 *
 * El motor es **puro**: cada función recibe un estado y devuelve uno nuevo, sin tocar
 * nada por dentro. Así la mesa que se pinta siempre sale de aplicar una regla, y las
 * reglas se pueden probar sin navegador.
 *
 * Lo esencial del juego, tal y como está escrito en las normas:
 *  - Una jugada son **una o varias cartas del mismo valor**.
 *  - Para responder hay que jugar **exactamente la misma cantidad** de cartas y de
 *    **valor superior**. Ni una menos, ni una más, ni de otro valor.
 *  - **Se puede pasar aunque tengas jugada**: pasar es una decisión, no una obligación.
 *  - La baza sigue hasta que todos los demás pasan; el último que jugó válido se lleva
 *    las cartas y abre la siguiente.
 *  - El primero que se queda sin cartas es el **Presidente** y el último el **Culo**,
 *    y en la ronda siguiente intercambian cartas.
 */
import {
  Card,
  SpanishRank,
  buildDeck,
  deal,
  shuffle,
  sortHand,
  strength,
} from './culo-deck';

export type Role = 'presidente' | 'vicepresidente' | 'neutro' | 'viceculo' | 'culo';

/** Una jugada: cartas del mismo valor. */
export interface Combo {
  cards: Card[];
  strength: number;
}

export interface PlayerState {
  id: number;
  name: string;
  isBot: boolean;
  hand: Card[];
  role: Role | null;
  /** Puesto en el que se quedó sin cartas (1 = primero). `null` si sigue jugando. */
  place: number | null;
  /**
   * Cuántas cartas tiene. En local es siempre `hand.length`, pero online los demás
   * llegan con la mano vacía (sus cartas no salen del servidor) y solo se sabe el número.
   */
  handCount?: number;
  /** Online: si sigue conectado. En local siempre es `true`. */
  connected?: boolean;
}

/** Lo que hay encima de la mesa. */
export interface Trick {
  cards: Card[];
  /** Quién la abrió (el último que jugó válido). */
  by: number;
  strength: number;
  count: number;
}

export type GameEvent =
  | { kind: 'play'; player: number; count: number; strength: number }
  | { kind: 'pass'; player: number }
  | { kind: 'trick'; player: number }
  | { kind: 'out'; player: number; place: number };

export interface GameState {
  players: PlayerState[];
  turn: number;
  table: Trick | null;
  /** Quiénes han pasado en la baza actual (no pueden volver a entrar en ella). */
  passed: number[];
  round: number;
  decks: 1 | 2;
  events: GameEvent[];
  phase: 'playing' | 'round-end';
}

export interface NewGameOptions {
  names: string[];
  bots: boolean[];
  decks?: 1 | 2;
  round?: number;
  rng?: () => number;
}

// ── Jugadas ──────────────────────────────────────────────────────────────────

/** Devuelve la jugada si todas las cartas son del mismo valor; `null` si no. */
export function comboOf(cards: Card[]): Combo | null {
  if (cards.length === 0) return null;
  const valor = strength(cards[0]);
  return cards.every((c) => strength(c) === valor) ? { cards, strength: valor } : null;
}

/** ¿`play` responde a lo que hay en la mesa? Misma cantidad y más valor. */
export function canBeat(play: Combo, table: Trick | null): boolean {
  if (!table) return true;
  return play.cards.length === table.count && play.strength > table.strength;
}

/**
 * Todas las jugadas que puede hacer un jugador ahora mismo.
 *
 * Con mesa: las que tienen exactamente su cantidad y más valor. Sin mesa (abriendo):
 * cualquier cantidad de cualquier valor que tenga en la mano.
 */
export function legalCombos(state: GameState, playerId: number): Combo[] {
  const jugador = state.players[playerId];
  if (!jugador) return [];
  const porValor = new Map<number, Card[]>();
  for (const carta of jugador.hand) {
    const v = strength(carta);
    porValor.set(v, [...(porValor.get(v) ?? []), carta]);
  }

  const jugadas: Combo[] = [];
  for (const [valor, cartas] of porValor) {
    if (state.table) {
      // Respondiendo: hay que igualar la cantidad exacta y superar el valor.
      if (cartas.length >= state.table.count && valor > state.table.strength) {
        jugadas.push({ cards: cartas.slice(0, state.table.count), strength: valor });
      }
    } else {
      // Abriendo: vale cualquier cantidad de ese valor.
      for (let n = 1; n <= cartas.length; n++) {
        jugadas.push({ cards: cartas.slice(0, n), strength: valor });
      }
    }
  }
  return jugadas;
}

// ── Arranque de ronda ────────────────────────────────────────────────────────

export function newGame(opciones: NewGameOptions): GameState {
  const { names, bots, decks = 1, round = 1, rng = Math.random } = opciones;
  const baraja = shuffle(buildDeck(decks), rng);
  const manos = deal(baraja, names.length);

  return {
    players: names.map((name, i) => ({
      id: i,
      name,
      isBot: bots[i],
      hand: sortHand(manos[i]),
      role: null,
      place: null,
    })),
    // La primera ronda empieza uno cualquiera; a partir de la segunda abre el Presidente.
    turn: Math.floor(rng() * names.length),
    table: null,
    passed: [],
    round,
    decks,
    events: [],
    phase: 'playing',
  };
}

// ── Jugar ────────────────────────────────────────────────────────────────────

export function canPlay(state: GameState, playerId: number, cards: Card[]): boolean {
  if (state.phase !== 'playing' || state.turn !== playerId) return false;
  if (cards.length === 0) return false;
  const jugador = state.players[playerId];
  if (!jugador) return false;
  // La misma carta no se puede jugar dos veces: si no se comprueba, dos copias del
  // mismo id pasarían por «pareja» y te descartarías de una sola carta.
  const ids = cards.map((c) => c.id);
  if (new Set(ids).size !== ids.length) return false;
  // Las cartas tienen que ser suyas (por id: con dos barajas hay repetidas).
  const suyas = ids.every((id) => jugador.hand.some((h) => h.id === id));
  if (!suyas) return false;
  const jugada = comboOf(cards);
  return jugada !== null && canBeat(jugada, state.table);
}

export function play(state: GameState, playerId: number, cards: Card[]): GameState {
  if (!canPlay(state, playerId, cards)) return state;
  const jugada = comboOf(cards)!;
  const ids = new Set(cards.map((c) => c.id));

  const jugadores = state.players.map((p) =>
    p.id === playerId ? { ...p, hand: p.hand.filter((c) => !ids.has(c.id)) } : p,
  );
  const eventos: GameEvent[] = [
    ...state.events,
    { kind: 'play', player: playerId, count: cards.length, strength: jugada.strength },
  ];

  const base: GameState = {
    ...state,
    players: jugadores,
    table: { cards, by: playerId, strength: jugada.strength, count: cards.length },
    // Quien juega vuelve a estar dentro: si había pasado, su jugada lo reengancha.
    passed: state.passed.filter((p) => p !== playerId),
    events: eventos,
  };

  return afterAction(base, playerId);
}

export function pass(state: GameState, playerId: number): GameState {
  if (state.phase !== 'playing' || state.turn !== playerId) return state;
  const base: GameState = {
    ...state,
    passed: state.passed.includes(playerId) ? state.passed : [...state.passed, playerId],
    events: [...state.events, { kind: 'pass', player: playerId }],
  };
  return afterAction(base, playerId);
}

/** Decide a quién le toca, si se cierra la baza o si se acaba la ronda. */
function afterAction(state: GameState, actor: number): GameState {
  let s = state;

  // ¿Se ha quedado sin cartas quien acaba de jugar?
  if (s.players[actor].hand.length === 0 && s.players[actor].place === null) {
    const puesto = s.players.filter((p) => p.place !== null).length + 1;
    s = {
      ...s,
      players: s.players.map((p) => (p.id === actor ? { ...p, place: puesto } : p)),
      events: [...s.events, { kind: 'out', player: actor, place: puesto }],
    };
  }

  // Si solo queda uno con cartas, la ronda está decidida.
  const conCartas = s.players.filter((p) => p.hand.length > 0);
  if (conCartas.length <= 1) {
    const ultimo = conCartas[0];
    if (ultimo) {
      const puesto = s.players.filter((p) => p.place !== null).length + 1;
      s = {
        ...s,
        players: s.players.map((p) => (p.id === ultimo.id ? { ...p, place: puesto } : p)),
      };
    }
    return assignRoles({ ...s, phase: 'round-end' });
  }

  const siguiente = nextToAct(s);
  if (siguiente === -1 || siguiente === s.table?.by) {
    // Todos los demás han pasado (o el que abrió se ha quedado sin cartas): se cierra
    // la baza y abre quien la ganó, o el siguiente con cartas si ya no está.
    return closeTrick(s);
  }
  return { ...s, turn: siguiente };
}

/** Siguiente jugador que puede actuar: con cartas y sin haber pasado en esta baza. */
function nextToAct(state: GameState): number {
  const n = state.players.length;
  for (let i = 1; i <= n; i++) {
    const idx = (state.turn + i) % n;
    const p = state.players[idx];
    if (p.hand.length === 0) continue;
    if (state.passed.includes(idx)) continue;
    return idx;
  }
  return -1;
}

function nextActiveAfter(state: GameState, from: number): number {
  const n = state.players.length;
  for (let i = 1; i <= n; i++) {
    const idx = (from + i) % n;
    if (state.players[idx].hand.length > 0) return idx;
  }
  return from;
}

function closeTrick(state: GameState): GameState {
  const ganador = state.table?.by ?? state.turn;
  const lider =
    state.players[ganador].hand.length > 0 ? ganador : nextActiveAfter(state, ganador);
  return {
    ...state,
    table: null,
    passed: [],
    turn: lider,
    events: [...state.events, { kind: 'trick', player: ganador }],
  };
}

// ── Fin de ronda: puestos y roles ────────────────────────────────────────────

/**
 * Reparte los roles según el orden en que cada uno se quedó sin cartas.
 *
 * Con **3 jugadores** no hay vicepresidente ni viceculo (el segundo sería a la vez
 * vicepresidente y viceculo): quedan Presidente, un neutro y Culo. Con 4 o más, el
 * segundo es Vicepresidente y el penúltimo Viceculo.
 */
export function assignRoles(state: GameState): GameState {
  const n = state.players.length;
  const porPuesto = [...state.players].sort((a, b) => (a.place ?? 99) - (b.place ?? 99));

  const roles = new Map<number, Role>();
  if (porPuesto.length) {
    roles.set(porPuesto[0].id, 'presidente');
    roles.set(porPuesto[porPuesto.length - 1].id, 'culo');
  }
  if (n >= 4) {
    roles.set(porPuesto[1].id, 'vicepresidente');
    roles.set(porPuesto[porPuesto.length - 2].id, 'viceculo');
  }
  for (const p of state.players) {
    if (!roles.has(p.id)) roles.set(p.id, 'neutro');
  }

  return {
    ...state,
    players: state.players.map((p) => ({ ...p, role: roles.get(p.id) ?? null })),
    phase: 'round-end',
  };
}

/** Los puestos, de primero a último, con su rol. */
export function standings(state: GameState): PlayerState[] {
  return [...state.players].sort((a, b) => (a.place ?? 99) - (b.place ?? 99));
}

// ── Intercambio entre rondas ─────────────────────────────────────────────────

export interface Swap {
  from: number;
  to: number;
  cards: Card[];
}

/**
 * Intercambio de cartas antes de la siguiente ronda:
 *  - El Culo le da sus **2 mejores** al Presidente, y el Presidente sus **2 peores** al Culo.
 *  - El Viceculo le da su **mejor** al Vicepresidente, que devuelve su **peor**.
 *
 * Se calcula aquí y se aplica con `applySwaps`, para poder enseñarlo antes de hacerlo.
 */
export function exchangeSwaps(state: GameState): Swap[] {
  const porRol = (rol: Role) => state.players.find((p) => p.role === rol);
  const presidente = porRol('presidente');
  const culo = porRol('culo');
  const vicepresidente = porRol('vicepresidente');
  const viceculo = porRol('viceculo');

  const swaps: Swap[] = [];
  if (presidente && culo) {
    const mejores = (p: PlayerState, n: number) =>
      sortHand(p.hand).slice(0, Math.min(n, p.hand.length));
    const peores = (p: PlayerState, n: number) =>
      sortHand(p.hand).slice(-Math.min(n, p.hand.length));

    swaps.push({ from: culo.id, to: presidente.id, cards: mejores(culo, 2) });
    swaps.push({ from: presidente.id, to: culo.id, cards: peores(presidente, 2) });
  }
  if (vicepresidente && viceculo) {
    swaps.push({ from: viceculo.id, to: vicepresidente.id, cards: sortHand(viceculo.hand).slice(0, 1) });
    swaps.push({
      from: vicepresidente.id,
      to: viceculo.id,
      cards: sortHand(vicepresidente.hand).slice(-1),
    });
  }
  return swaps.filter((s) => s.cards.length > 0);
}

/**
 * Reparte la ronda siguiente y **después** intercambia las cartas que tocan.
 *
 * El orden importa, y aquí se equivocó: si los intercambios se calculan sobre la mano vieja
 * y luego se reparte, el reparto se lleva por delante las cartas intercambiadas y el
 * intercambio **nunca ocurre** (la regla del Culo se quedaba en nada y no se notaba, porque
 * las dos funciones por separado están bien). Va en el motor para que se pueda probar.
 */
export function nextRoundWithSwaps(state: GameState, rng?: () => number): GameState {
  const nueva = nextRound(state, rng);
  return applySwaps(nueva, exchangeSwaps(nueva));
}

export function applySwaps(state: GameState, swaps: Swap[]): GameState {
  const manos = state.players.map((p) => [...p.hand]);
  for (const swap of swaps) {
    const ids = new Set(swap.cards.map((c) => c.id));
    manos[swap.from] = manos[swap.from].filter((c) => !ids.has(c.id));
    manos[swap.to] = [...manos[swap.to], ...swap.cards];
  }
  return {
    ...state,
    players: state.players.map((p, i) => ({ ...p, hand: sortHand(manos[i]) })),
  };
}

/** Arranca la ronda siguiente conservando nombres, bots y roles ya intercambiados. */
export function nextRound(
  state: GameState,
  rng: () => number = Math.random,
): GameState {
  const baraja = shuffle(buildDeck(state.decks), rng);
  const manos = deal(baraja, state.players.length);
  const presidente = state.players.find((p) => p.role === 'presidente');

  return {
    ...state,
    players: state.players.map((p, i) => ({
      ...p,
      hand: sortHand(manos[i]),
      place: null,
      // Los roles se recalculan al final de esta ronda; aquí solo se arrastran para
      // saber quién abre.
    })),
    turn: presidente ? presidente.id : Math.floor(rng() * state.players.length),
    table: null,
    passed: [],
    round: state.round + 1,
    events: [],
    phase: 'playing',
  };
}

/** Etiqueta del rol, para pintarlo. */
export function roleKey(role: Role): string {
  return `culo.role.${role}`;
}

/** Nombre legible del valor, para el registro de la mesa. */
export function rankLabelKey(rank: SpanishRank): string {
  return `culo.rank.${rank}`;
}
