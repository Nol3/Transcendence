/**
 * Baraja española para el Culo (Presidente).
 *
 * Lo común —palos, valores, construir el mazo, barajar y repartir— vive en `../baraja.ts`.
 * Aquí queda **lo que es del Culo**: su orden de fuerza, que no es el de ningún otro juego,
 * y su forma de ordenar la mano para pintarla.
 *
 * 40 cartas por baraja, y se puede jugar con una o dos; con dos, cada carta lleva `copy`
 * para que las repetidas sean distinguibles.
 */

import { Card, SpanishRank, SpanishSuit, buildDeck, deal, shuffle } from '../baraja';

export type { Card, SpanishRank, SpanishSuit };
export { buildDeck, deal, shuffle };

export const SUITS: SpanishSuit[] = ['o', 'c', 'e', 'b'];
export const RANKS: SpanishRank[] = [1, 2, 3, 4, 5, 6, 7, 10, 11, 12];

/**
 * Fuerza de una carta dentro del juego.
 *
 * El orden no es el de la baraja: de menor a mayor es 2, 3, 4, 5, 6, 7, Sota, Caballo,
 * Rey, As… y por encima de todas, **el 5 de oros**. Ese 5 de oros es además una carta
 * aparte: vale más que cualquier otra, así que **no se puede jugar junto a otros cincos**
 * (no comparten valor).
 */
export function strength(card: Card): number {
  if (card.rank === 5 && card.suit === 'o') return 12; // el 5 de oros manda
  if (card.rank === 1) return 11; // el As
  if (card.rank === 12) return 10; // el Rey
  if (card.rank === 11) return 9; // el Caballo
  if (card.rank === 10) return 8; // la Sota
  return card.rank; // del 2 al 7 valen lo que marcan
}

/** Clave de traducción del valor de la carta. */
export function rankKey(rank: SpanishRank): string {
  return `culo.rank.${rank}`;
}

/** Ordena una mano de mayor a menor fuerza, para pintarla siempre igual. */
export function sortHand(hand: Card[]): Card[] {
  return [...hand].sort((a, b) => strength(b) - strength(a) || a.suit.localeCompare(b.suit));
}
