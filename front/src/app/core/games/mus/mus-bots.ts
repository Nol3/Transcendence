/**
 * El bot del Mus.
 *
 * Es el más listo de los cuatro bots del proyecto, porque aquí no hay bazas que ganar: hay que
 * **evaluar los cuatro lances** y decidir cuándo apretar. La idea es sencilla y no desentona:
 *
 * - En el mus: si la mano no tiene ni pares ni juego, pide mus; si tiene algo, corta.
 * - Al descartar: se queda con lo que forma la jugada (los pares y las cartas que dan juego) y
 *   cambia el resto.
 * - En los lances: pasa si no tiene nada; envida si tiene una jugada fuerte; y responde a los
 *   envites según lo buena que sea su mano.
 *
 * No necesita saber nada que no esté en su vista, así que vale igual para el modo local y para los
 * bots de una sala del servidor.
 */

import { Card } from '../baraja';
import { Jugada, Lance, MusState, comparar, evaluar, parejaDe, turnoActual } from './mus-engine';

export type MusDecision =
  | { action: 'mus' }
  | { action: 'cortar' }
  | { action: 'descartar'; cardIds: string[] }
  | { action: 'pasar' }
  | { action: 'envidar'; cuantas: number }
  | { action: 'ordago' }
  | { action: 'quiero' }
  | { action: 'no_quiero' }
  | null;

/** ¿Merece la pena jugar esta mano? Cuenta las jugadas que tiene. */
export function valorJugada(j: Jugada): number {
  let valor = 0;
  if (j.pares.categoria === 'duples') valor += 3;
  else if (j.pares.categoria === 'medias') valor += 2;
  else if (j.pares.categoria === 'par') valor += 1;
  if (j.juego !== null) valor += 3;
  // Una grande muy alta o una chica muy baja también valen.
  if (j.grande >= 9) valor += 1;
  if (j.chica <= 2) valor += 1;
  return valor;
}

/** Lo buena que es esta mano para un lance concreto. */
function fuerzaEn(j: Jugada, lance: Lance, todas: Jugada[]): number {
  const mejores = todas.map((o) => comparar(j, o, lance));
  // Cuántas manos de la mesa gana: 0 = la peor, n = la mejor.
  return mejores.filter((c) => c > 0).length;
}

export function botDecision(state: MusState, seat: number): MusDecision {
  if (state.phase === 'game-end' || state.phase === 'vaca-end') return null;
  if (turnoActual(state) !== seat) return null;

  const yo = state.players[seat];

  if (state.phase === 'mus') {
    // Solo se pide mus una vez: si ya ha cambiado cartas y sigue sin tener nada, corta. Sin ese
    // tope, cuatro bots pidiendo mus se quedarían dando vueltas para siempre.
    if (valorJugada(yo.jugada) >= 2 || yo.descartes >= 1) return { action: 'cortar' };
    return { action: 'mus' };
  }

  if (state.phase === 'descartar') {
    return { action: 'descartar', cardIds: cartasQueSobran(yo.hand) };
  }

  // En los lances.
  const lance = state.lance;
  if (!lance) return null;

  // Si hay un envite esperando respuesta, contesta.
  if (state.envite && state.responde === seat) {
    const mia = yo.jugada;
    const suya = mejorDeLaParejaContraria(state, seat, lance);
    const gano = suya ? comparar(mia, suya, lance) > 0 : true;
    const valor = valorJugada(mia);
    if (state.envite.ordago) return gano && valor >= 4 ? { action: 'quiero' } : { action: 'no_quiero' };
    if (gano && valor >= 3) return { action: 'quiero' };
    if (valor >= 2 && state.envite.cuantas <= 2) return { action: 'quiero' };
    return { action: 'no_quiero' };
  }

  const todas = state.players.map((p) => p.jugada);
  const ganoLaMesa = fuerzaEn(yo.jugada, lance, todas) === todas.length - 1;
  const valor = valorJugada(yo.jugada);

  if (ganoLaMesa && valor >= 3) {
    return valor >= 6 ? { action: 'ordago' } : { action: 'envidar', cuantas: 2 };
  }
  if (valor >= 4) return { action: 'envidar', cuantas: 2 };
  return { action: 'pasar' };
}

/** Las cartas que no aportan nada: las que no forman parte de la jugada. */
function cartasQueSobran(mano: Card[]): string[] {
  const porRango = new Map<Card['rank'], Card[]>();
  for (const c of mano) porRango.set(c.rank, [...(porRango.get(c.rank) ?? []), c]);

  const utiles = new Set<string>();
  // Las repetidas que forman la combinación.
  for (const [, cartas] of porRango) {
    if (cartas.length >= 2) for (const c of cartas) utiles.add(c.id);
  }
  // Y las más altas y más bajas, que valen para grande y chica.
  const ordenadas = [...mano].sort((a, b) => evaluar([b]).grande - evaluar([a]).grande);
  utiles.add(ordenadas[0]?.id ?? '');
  utiles.add(ordenadas[ordenadas.length - 1]?.id ?? '');

  const sobran = mano.filter((c) => !utiles.has(c.id)).map((c) => c.id);
  // Nunca se descartan las cuatro: se descarta lo que sobra, y si sobra todo, tres.
  return sobran.length === 4 ? sobran.slice(0, 3) : sobran;
}

function mejorDeLaParejaContraria(state: MusState, seat: number, lance: Lance): Jugada | null {
  const contrarios = state.teams[1 - parejaDe(seat)].players;
  let mejor: Jugada | null = null;
  for (const id of contrarios) {
    const j = state.players[id].jugada;
    if (!mejor || comparar(j, mejor, lance) > 0) mejor = j;
  }
  return mejor;
}
