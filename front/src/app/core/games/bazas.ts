/**
 * Lo que comparten los juegos de bazas (brisca y tute).
 *
 * En los dos se juega una carta, gana la mejor y el que gana se lleva la baza. Lo que cambia
 * es cuándo estás obligado a asistir y cuánto valen las cartas al final, y eso vive en cada
 * juego. Aquí está lo de los dos:
 *
 * - **El orden de fuerza**, que NO es el del Culo ni el de la baraja: de menor a mayor es
 *   `2 < 4 < 5 < 6 < 7 < Sota < Caballo < Rey < 3 < As`. El **tres** es la segunda carta más
 *   alta, no la tercera: es el error clásico al añadir un juego de bazas copiando del Culo.
 * - **Lo que vale cada carta** al contar los tantos: As 11, tres 10, rey 4, caballo 3, sota 2,
 *   y el resto (7, 6, 5, 4, 2) no vale nada aunque sirva para ganar bazas.
 * - **Quién gana una baza**: la carta más alta del palo de triunfo; si no hay triunfo, la más
 *   alta del palo con el que se salió.
 */

import { Card, SpanishRank } from './baraja';

/** Fuerza de una carta en brisca y tute. Ojo: el tres va segundo. */
const FUERZA: Record<SpanishRank, number> = {
  2: 1,
  4: 2,
  5: 3,
  6: 4,
  7: 5,
  10: 6, // Sota
  11: 7, // Caballo
  12: 8, // Rey
  3: 9, // ← el tres, por delante del rey
  1: 10, // As
};

/** Tantos que vale cada carta al terminar el juego. */
const PUNTOS: Record<SpanishRank, number> = {
  1: 11, // As
  3: 10, // Tres
  12: 4, // Rey
  11: 3, // Caballo
  10: 2, // Sota
  7: 0,
  6: 0,
  5: 0,
  4: 0,
  2: 0,
};

/** De menor a mayor, para pintar el panel de reglas. */
export const ORDEN_BAZAS: SpanishRank[] = [2, 4, 5, 6, 7, 10, 11, 12, 3, 1];

export function fuerza(card: Card): number {
  return FUERZA[card.rank];
}

export function puntos(card: Card): number {
  return PUNTOS[card.rank];
}

/** Cuántos tantos suman unas cartas ganadas (una baza o todas las de la partida). */
export function tantos(cards: Card[]): number {
  return cards.reduce((total, carta) => total + puntos(carta), 0);
}

export interface Baza {
  player: number;
  card: Card;
}

/**
 * Quién gana la baza.
 *
 * Gana la carta más alta **del palo de triunfo**; si no se jugó triunfo, la más alta del palo
 * con el que salió el primero. En brisca y tute no hay empates posibles: la baraja no repite
 * carta dentro de un palo.
 */
export function ganadorDeBaza(baza: Baza[], triunfo: Card['suit']): number {
  if (baza.length === 0) return -1;
  let mejor = baza[0];
  for (const jugada of baza.slice(1)) {
    const gana =
      jugada.card.suit === triunfo && mejor.card.suit !== triunfo
        ? true
        : jugada.card.suit !== mejor.card.suit
          ? false
          : fuerza(jugada.card) > fuerza(mejor.card);
    if (gana) mejor = jugada;
  }
  return mejor.player;
}

/** ¿Puede esta carta ganar la baza que hay ahora mismo en la mesa? */
export function puedeGanar(card: Card, baza: Baza[], triunfo: Card['suit']): boolean {
  const paloSalida = baza[0]?.card.suit ?? card.suit;
  const cartasTriunfo = baza.filter((j) => j.card.suit === triunfo);
  if (card.suit === triunfo) {
    return cartasTriunfo.every((j) => fuerza(card) > fuerza(j.card));
  }
  if (cartasTriunfo.length > 0) return false; // hay triunfo en la mesa y no es tuyo
  if (card.suit !== paloSalida) return false;
  return baza.filter((j) => j.card.suit === paloSalida).every((j) => fuerza(card) > fuerza(j.card));
}

/** Las cartas de la mano que valen tantos (ases, treses, reyes, caballos y sotas). */
export function cartasDeValor(hand: Card[]): Card[] {
  return hand.filter((c) => puntos(c) > 0);
}

/** Ordena una mano de mayor a menor fuerza, agrupada por palo, para pintarla siempre igual. */
export function ordenarMano(hand: Card[]): Card[] {
  return [...hand].sort(
    (a, b) => a.suit.localeCompare(b.suit) || fuerza(b) - fuerza(a),
  );
}
