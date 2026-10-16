import { Card, SpanishRank } from '../baraja';
import { MentirosoEvent, MentirosoPlay, MentirosoState } from './mentiroso-engine';

/**
 * Adapta lo que manda el servidor a la forma del motor local.
 *
 * El servidor manda **tu** mano entera y, de los demás, solo cuántas cartas les quedan (y del
 * montón, solo el número: eso es el juego). La mesa del juego está escrita para el estado local,
 * así que aquí se rellena lo que falta con cartas de relleno: así el modo «con amigos» usa la
 * misma mesa que el modo contra bots, en vez de tener dos pantallas que se van separando.
 */
export interface MentirosoVista {
  players: {
    id: number;
    name: string;
    isBot: boolean;
    handCount: number;
    wins?: number;
    connected?: boolean;
  }[];
  myHand: Card[];
  claimedRank: SpanishRank | null;
  pileCount: number;
  turn: number;
  hand: number;
  targetWins: number;
  events: MentirosoEvent[];
  phase: MentirosoState['phase'];
  winner: number | null;
}

/** Cartas de relleno: solo se usan para contar (nunca se enseñan). */
function relleno(cuantas: number): Card[] {
  return Array.from({ length: cuantas }, (_, i) => ({
    id: `oculta-${i}`,
    rank: 1 as Card['rank'],
    suit: 'o' as Card['suit'],
    copy: 0,
  }));
}

export function estadoDesdeVista(vista: MentirosoVista, seat: number): MentirosoState {
  return {
    players: vista.players.map((p) => ({
      id: p.id,
      name: p.name,
      isBot: p.isBot,
      hand: p.id === seat ? vista.myHand : relleno(p.handCount),
      // Los cuatro iguales retirados y las manos ganadas los manda el servidor; si no, a cero.
      retired: [],
      wins: p.wins ?? 0,
      connected: p.connected,
    })),
    pile: relleno(vista.pileCount),
    claimedRank: vista.claimedRank,
    turn: vista.turn,
    lastPlay: ultimaJugada(vista),
    hand: vista.hand,
    targetWins: vista.targetWins,
    events: vista.events,
    phase: vista.phase,
    winner: vista.winner,
  };
}

/** La última jugada, reconstruida del registro (la mesa la usa para el cartel del centro). */
function ultimaJugada(vista: MentirosoVista): MentirosoPlay | null {
  const jugadas = vista.events.filter((e) => e.kind === 'play');
  const ultima = jugadas[jugadas.length - 1];
  if (!ultima || ultima.kind !== 'play') return null;
  // El registro dice cuántas cartas se pusieron, no cuáles (no se enseñan): van de relleno.
  return { player: ultima.player, cards: relleno(ultima.count), claimedRank: ultima.claimedRank };
}
