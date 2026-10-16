/**
 * El bot de la brisca.
 *
 * Juega como se juega en la mesa: si puede ganar la baza con una carta que **no valga tantos**,
 * la gana; si no, suelta la carta que menos le sirva. Guarda ases y treses para bazas que pueda
 * ganar, y no malgasta un triunfo alto si la baza no tiene nada que merezca la pena.
 *
 * No necesita saber nada que no esté en su vista, así que sirve igual para el modo local y para
 * los bots de una sala del servidor.
 */

import { Card } from '../baraja';
import { Baza, fuerza, puedeGanar } from '../bazas';
import { BriscaState } from './brisca-engine';

/** Lo que vale una carta para el bot: cuanto más valiosa, menos ganas de soltarla. */
function coste(carta: Card, triunfo: Card['suit']): number {
  // Los tantos que se lleva el rival si se la lleva él, más el valor de guardarla.
  const valor = carta.rank === 1 ? 11 : carta.rank === 3 ? 10 : carta.rank === 12 ? 4 : carta.rank === 11 ? 3 : carta.rank === 10 ? 2 : 0;
  const esTriunfo = carta.suit === triunfo ? 3 : 0;
  return valor + esTriunfo + fuerza(carta) / 10;
}

/**
 * Qué carta juega el bot. Devuelve el id, o `null` si no le toca.
 */
export function botDecision(state: BriscaState, seat: number): string | null {
  if (state.phase !== 'playing' || state.turn !== seat) return null;
  const yo = state.players[seat];
  if (!yo || yo.hand.length === 0) return null;

  const baza: Baza[] = state.trick;
  const triunfo = state.trumpSuit;

  // Si es el último en hablar y ya va ganando, no gasta nada: suelta lo más barato.
  if (baza.length === state.players.length - 1) {
    const ganadorAhora = ganadorParcial(baza, triunfo);
    if (ganadorAhora === seat) {
      return masBarata(yo.hand, triunfo).id;
    }
  }

  // Si puede ganar la baza, la gana con la carta más barata que sirva.
  const ganadoras = yo.hand
    .filter((c) => puedeGanar(c, baza, triunfo))
    .sort((a, b) => coste(a, triunfo) - coste(b, triunfo));
  if (ganadoras.length > 0) {
    return ganadoras[0].id;
  }

  // Si no puede ganarla, suelta la que menos le duela.
  return masBarata(yo.hand, triunfo).id;
}

/** Quién va ganando la baza tal y como está ahora. */
function ganadorParcial(baza: Baza[], triunfo: Card['suit']): number {
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

/** La carta que menos le importa perder: la de menos valor y menos fuerza. */
function masBarata(hand: Card[], triunfo: Card['suit']): Card {
  return [...hand].sort((a, b) => coste(a, triunfo) - coste(b, triunfo))[0];
}
