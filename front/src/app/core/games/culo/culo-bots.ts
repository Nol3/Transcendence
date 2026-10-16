/**
 * Cómo juegan los bots del Culo.
 *
 * No pretenden ser brillantes, pero sí jugar como juega una persona: no regalan las
 * cartas altas, aprovechan para descartarse cuando están cerca del final y, cuando
 * abren, eligen el tamaño de la jugada pensando en lo que les deja hacer a los demás.
 */
import { Card, sortHand, strength } from './culo-deck';
import { Combo, GameState, legalCombos } from './culo-engine';

export interface BotDecision {
  cards: Card[];
}

/**
 * Decide qué hace el bot: devuelve las cartas que juega o `null` si pasa.
 *
 * `rng` se inyecta para poder probar el comportamiento sin depender del azar.
 */
export function botDecision(
  state: GameState,
  playerId: number,
  rng: () => number = Math.random,
): BotDecision | null {
  const jugadas = legalCombos(state, playerId);
  if (jugadas.length === 0) return null;

  const mano = state.players[playerId].hand;

  // 1) Si puede quedarse sin cartas de una vez, lo hace: es el objetivo del juego.
  const seDescarta = jugadas.find((j) => j.cards.length === mano.length);
  if (seDescarta) return { cards: seDescarta.cards };

  // 2) Si le quedan pocas cartas, juega: está a punto de ser Presidente.
  if (mano.length <= 2) {
    return { cards: masBarata(jugadas).cards };
  }

  const mejor = masBarata(jugadas);

  // 3) Guardarse las cartas altas es una jugada legítima: si la única salida es jugar
  //    algo muy alto y todavía tiene mano de sobra, a veces pasa.
  const esCartaAlta = mejor.strength >= 9; // Caballo o mejor
  if (state.table && esCartaAlta && mano.length > 4 && rng() < 0.45) {
    return null;
  }

  // 4) Abriendo: cuantas más cartas juegue de golpe, menos respuestas posibles deja.
  if (!state.table) {
    const porTamano = [...jugadas].sort(
      (a, b) => b.cards.length - a.cards.length || a.strength - b.strength,
    );
    const grande = porTamano[0];
    // Con grupos de tres o más, abre fuerte; si no, abre barato.
    if (grande.cards.length >= 3) return { cards: grande.cards };
  }

  return { cards: mejor.cards };
}

/** La jugada que menos fuerza gasta, para no malgastar cartas altas. */
function masBarata(jugadas: Combo[]): Combo {
  return [...jugadas].sort(
    (a, b) => a.strength - b.strength || a.cards.length - b.cards.length,
  )[0];
}

/** Cartas que el bot tiraría si tuviera que descartarse de algo (para la UI). */
export function peoresCartas(mano: Card[], n: number): Card[] {
  return sortHand(mano).slice(-n);
}

/** ¿El bot tiene con qué responder? Sirve para enseñar «puede jugar» sin enseñar qué. */
export function botCanPlay(state: GameState, playerId: number): boolean {
  return legalCombos(state, playerId).length > 0;
}

/** Fuerza máxima de la mano, para la vista de «cartas fuertes» del jugador. */
export function maxStrength(mano: Card[]): number {
  return mano.reduce((max, c) => Math.max(max, strength(c)), 0);
}
