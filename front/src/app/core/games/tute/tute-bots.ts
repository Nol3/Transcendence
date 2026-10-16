/**
 * El bot del Tute.
 *
 * Canta lo que puede cantar (el tute gana el juego, y un acuse son tantos gratis), y juega
 * respetando las obligaciones: como el motor le dice qué cartas son legales, el bot solo tiene que
 * elegir entre ellas — ganar la baza con la más barata que sirva, o soltar la que menos le duela.
 *
 * No necesita saber nada que no esté en su vista, así que sirve igual para el modo local y para
 * los bots de una sala del servidor.
 */

import { Card } from '../baraja';
import { Baza, fuerza, puntos } from '../bazas';
import { TuteState, acusesDisponibles, jugadasLegales, tieneTute } from './tute-engine';

export type BotDecision =
  | { action: 'play'; cardId: string }
  | { action: 'sing'; suit: string }
  | { action: 'tute' }
  | null;

/** Lo que le duele al bot soltar una carta. */
function coste(carta: Card, triunfo: Card['suit']): number {
  return puntos(carta) + (carta.suit === triunfo ? 3 : 0) + fuerza(carta) / 10;
}

/** ¿Va ganando esta jugador la baza tal y como está? */
function vaGanando(baza: Baza[], seat: number, triunfo: Card['suit']): boolean {
  if (baza.length === 0) return false;
  const paloSalida = baza[0].card.suit;
  let mejor = baza[0];
  for (const jugada of baza.slice(1)) {
    const suya = jugada.card;
    const gana =
      suya.suit === triunfo && mejor.card.suit !== triunfo
        ? true
        : suya.suit !== mejor.card.suit
          ? false
          : fuerza(suya) > fuerza(mejor.card);
    if (gana) mejor = jugada;
  }
  void paloSalida;
  return mejor.player === seat;
}

export function botDecision(state: TuteState, seat: number): BotDecision {
  if (state.phase !== 'playing') return null;

  // El tute gana el juego: si lo tiene, lo canta.
  if (tieneTute(state, seat)) return { action: 'tute' };

  // Un acuse son tantos gratis: se canta en cuanto se puede (las cuarenta primero).
  const acuses = acusesDisponibles(state, seat);
  if (acuses.length > 0) {
    const cuarenta = acuses.find((s) => s === state.trumpSuit);
    return { action: 'sing', suit: cuarenta ?? acuses[0] };
  }

  if (state.turn !== seat) return null;
  const legales = jugadasLegales(state, seat);
  if (legales.length === 0) return null;

  const triunfo = state.trumpSuit;
  const ultimo = state.trick.length === state.players.length - 1;

  // Si es el último y ya va ganando, no gasta nada: suelta lo más barato que sea legal.
  if (ultimo && vaGanando(state.trick, seat, triunfo)) {
    return { action: 'play', cardId: masBarata(legales, triunfo).id };
  }

  // Si alguna de las legales gana la baza, la gana con la más barata.
  const ganadoras = legales
    .filter((c) => ganariaLaBaza(state.trick, c, triunfo))
    .sort((a, b) => coste(a, triunfo) - coste(b, triunfo));
  if (ganadoras.length > 0) return { action: 'play', cardId: ganadoras[0].id };

  return { action: 'play', cardId: masBarata(legales, triunfo).id };
}

function ganariaLaBaza(baza: Baza[], carta: Card, triunfo: Card['suit']): boolean {
  const conCarta: Baza[] = [...baza, { player: -1, card: carta }];
  const paloSalida = conCarta[0].card.suit;
  let mejor = conCarta[0];
  for (const jugada of conCarta.slice(1)) {
    const suya = jugada.card;
    const gana =
      suya.suit === triunfo && mejor.card.suit !== triunfo
        ? true
        : suya.suit !== mejor.card.suit
          ? false
          : fuerza(suya) > fuerza(mejor.card);
    if (gana) mejor = jugada;
  }
  void paloSalida;
  return mejor.player === -1;
}

function masBarata(legales: Card[], triunfo: Card['suit']): Card {
  return [...legales].sort((a, b) => coste(a, triunfo) - coste(b, triunfo))[0];
}
