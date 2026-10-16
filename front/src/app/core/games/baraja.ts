/**
 * La baraja española, compartida por todos los juegos.
 *
 * Aquí vive **lo que es igual en todos**: los cuatro palos, los diez valores por palo, cómo
 * se construye el mazo, cómo se baraja y cómo se reparte.
 *
 * Lo que **no** está aquí es el orden de fuerza, porque cambia en cada juego y es justo lo
 * que hace que una baraja sirva para jugar a cosas distintas:
 *
 * - **Culo**: `2 < 3 < 4 < 5 < 6 < 7 < Sota < Caballo < Rey < As`, y por encima de todo el
 *   **5 de oros** (`core/games/culo/culo-deck.ts`).
 * - **Brisca y tute**: `2 < 4 < 5 < 6 < 7 < Sota < Caballo < Rey < 3 < As` — el **tres** es la
 *   segunda carta más alta, no la tercera (`core/games/bazas.ts`).
 * - **Mus**: no hay orden ni palos que valgan; solo puntos (`core/games/mus/`).
 *
 * Por eso cada juego trae su tabla en vez de heredarla de aquí: copiar la del Culo es el error
 * clásico al añadir un juego de bazas.
 */

export type SpanishSuit = 'o' | 'c' | 'e' | 'b';
/** 1 = As, 2..7, 10 = Sota, 11 = Caballo, 12 = Rey. */
export type SpanishRank = 1 | 2 | 3 | 4 | 5 | 6 | 7 | 10 | 11 | 12;

export interface Card {
  /** Identificador único dentro de la partida (dos barajas = copias). */
  id: string;
  suit: SpanishSuit;
  rank: SpanishRank;
  /** 0 para la primera baraja, 1 para la segunda. */
  copy: number;
}

export const SUITS: SpanishSuit[] = ['o', 'c', 'e', 'b'];
export const RANKS: SpanishRank[] = [1, 2, 3, 4, 5, 6, 7, 10, 11, 12];

/** Los nombres de los palos, en el orden en que se dicen siempre. */
export const SUIT_KEYS: Record<SpanishSuit, string> = {
  o: 'baraja.suit.oros',
  c: 'baraja.suit.copas',
  e: 'baraja.suit.espadas',
  b: 'baraja.suit.bastos',
};

/** Clave de traducción del valor de una carta (As, Sota, Caballo, Rey…). */
export function rankKey(rank: SpanishRank): string {
  return `baraja.rank.${rank}`;
}

export function buildDeck(decks: 1 | 2 = 1): Card[] {
  const cartas: Card[] = [];
  for (let copy = 0; copy < decks; copy++) {
    for (const suit of SUITS) {
      for (const rank of RANKS) {
        cartas.push({ id: `${rank}${suit}-${copy}`, suit, rank, copy });
      }
    }
  }
  return cartas;
}

/** Baraja de Fisher-Yates. `rng` se inyecta para poder probar con un orden fijo. */
export function shuffle<T>(items: T[], rng: () => number = Math.random): T[] {
  const copia = [...items];
  for (let i = copia.length - 1; i > 0; i--) {
    const j = Math.floor(rng() * (i + 1));
    [copia[i], copia[j]] = [copia[j], copia[i]];
  }
  return copia;
}

/**
 * Reparte **todas** las cartas, de una en una y por turnos.
 *
 * Con 40 cartas y 6 jugadores no salen iguales, y así es como se juega: el reparto se
 * termina y a quien le toque una carta de más, la tiene.
 */
export function deal(deck: Card[], players: number): Card[][] {
  const manos: Card[][] = Array.from({ length: players }, () => []);
  deck.forEach((carta, i) => manos[i % players].push(carta));
  return manos;
}

/**
 * Reparte **n** cartas a cada uno y devuelve lo que sobra (el mazo).
 *
 * Es lo que necesitan los juegos que no reparten todo de golpe (brisca: 3 cartas y a robar;
 * tute: 8 o 10 con baceta).
 */
export function dealSome(deck: Card[], players: number, each: number): {
  hands: Card[][];
  rest: Card[];
} {
  const manos: Card[][] = Array.from({ length: players }, () => []);
  let i = 0;
  for (let n = 0; n < each; n++) {
    for (let p = 0; p < players; p++) {
      if (i < deck.length) manos[p].push(deck[i++]);
    }
  }
  return { hands: manos, rest: deck.slice(i) };
}
