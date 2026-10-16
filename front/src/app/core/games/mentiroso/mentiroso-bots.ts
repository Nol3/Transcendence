/**
 * El bot del Mentiroso.
 *
 * Juega como juega la gente: echa lo que dice que echa cuando lo tiene, y cuando no, miente
 * con la carta que menos le sirve. Y desconfía cuando las cuentas no le salen — si el valor
 * que se está diciendo es un valor que él tiene casi entero, el de antes tiene que estar
 * mintiendo.
 *
 * No necesita saber nada que no esté en su vista, así que sirve igual para el modo local y
 * para los bots de una sala del servidor.
 */

import { MentirosoState } from './mentiroso-engine';

export type BotDecision =
  | { action: 'play'; cardIds: string[]; claimedRank: number }
  | { action: 'challenge' }
  | { action: 'retire'; rank: number }
  | null;

/**
 * Qué hace el bot en su turno. Devuelve `null` si no le toca o no hay nada que hacer.
 *
 * `aleatorio` se inyecta para poder probarlo siempre igual.
 */
export function botDecision(
  state: MentirosoState,
  seat: number,
  aleatorio: () => number = Math.random,
): BotDecision {
  if (state.phase !== 'playing' || state.turn !== seat) return null;
  const yo = state.players[seat];
  if (!yo || yo.hand.length === 0) return null;

  // Los cuatro iguales se retiran sin pensarlo: son cartas que ya no valen para nada.
  const porValor = new Map<number, number>();
  for (const carta of yo.hand) porValor.set(carta.rank, (porValor.get(carta.rank) ?? 0) + 1);
  const cuatro = [...porValor.entries()].find(([, n]) => n === 4);
  if (cuatro) return { action: 'retire', rank: cuatro[0] };

  // ¿Desconfío? Si entre lo que ya hay puesto y lo que tengo yo se juntan tres o más del
  // valor que se está diciendo, al de antes no le quedan: está mintiendo.
  const ultima = state.lastPlay;
  if (ultima && ultima.player !== seat) {
    const yaEnLaMesa = state.pile.filter((c) => c.rank === ultima.claimedRank).length;
    const mias = yo.hand.filter((c) => c.rank === ultima.claimedRank).length;
    if (yaEnLaMesa + mias >= 3) return { action: 'challenge' };
    // Y de vez en cuando, por si acaso: un farol se huele, no se calcula.
    if (aleatorio() < 0.12) return { action: 'challenge' };
  }

  // El valor que toca: el que hay en la mesa, o el que más le convenga si abre.
  const valor = state.claimedRank ?? valorParaAbrir(yo.hand.map((c) => c.rank));

  // Si tiene de verdad, la echa (cuantas más, mejor: se quita cartas de encima).
  const reales = yo.hand.filter((c) => c.rank === valor);
  if (reales.length > 0) {
    return { action: 'play', cardIds: reales.map((c) => c.id), claimedRank: valor };
  }

  // Y si no, miente con la carta que menos le sirve: la que menos repetida tiene, para no
  // romper un trío o una pareja que pueda acabar en cuatro.
  const candidata = [...yo.hand].sort((a, b) => {
    const na = porValor.get(a.rank) ?? 0;
    const nb = porValor.get(b.rank) ?? 0;
    return na - nb || a.rank - b.rank;
  })[0];
  return { action: 'play', cardIds: [candidata.id], claimedRank: valor };
}

/** Con qué valor le conviene abrir: el que más cartas de verdad tenga. */
function valorParaAbrir(rangos: number[]): number {
  const cuenta = new Map<number, number>();
  for (const r of rangos) cuenta.set(r, (cuenta.get(r) ?? 0) + 1);
  return [...cuenta.entries()].sort((a, b) => b[1] - a[1] || a[0] - b[0])[0][0];
}
