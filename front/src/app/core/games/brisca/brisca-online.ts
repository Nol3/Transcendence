import { Card, SpanishSuit } from '../baraja';
import { Baza } from '../bazas';
import { BriscaEvent, BriscaState } from './brisca-engine';

/**
 * Adapta lo que manda el servidor a la forma del motor local.
 *
 * El servidor manda **tu** mano y **tus** bazas, y de los demás solo el recuento (los tantos ya
 * calculados). La mesa está escrita para el estado local, así que aquí se rellena lo que falta:
 * así el modo «con amigos» usa la misma mesa que el modo contra bots.
 */
export interface BriscaVista {
  players: {
    id: number;
    name: string;
    isBot: boolean;
    handCount: number;
    tantos?: number;
    tricks?: number;
    connected?: boolean;
  }[];
  myHand: Card[];
  myWon: Card[];
  trumpCard: Card | null;
  trumpSuit: SpanishSuit;
  deckCount: number;
  turn: number;
  trick: Baza[];
  lastTrick: { winner: number; cards: Baza[] } | null;
  lastWinner: number | null;
  swapPermitido: boolean;
  scores: number[];
  gamesWon: number[];
  targetGames: number;
  events: BriscaEvent[];
  phase: BriscaState['phase'];
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

export function estadoDesdeVista(vista: BriscaVista, seat: number): BriscaState {
  return {
    players: vista.players.map((p) => ({
      id: p.id,
      name: p.name,
      isBot: p.isBot,
      hand: p.id === seat ? vista.myHand : relleno(p.handCount),
      won: p.id === seat ? vista.myWon : [],
      tricks: p.tricks ?? 0,
      // El servidor ya manda los tantos contados: la mesa los usa tal cual.
      tantos: p.tantos ?? 0,
      connected: p.connected,
    })),
    deck: relleno(vista.deckCount),
    trumpCard: vista.trumpCard,
    trumpSuit: vista.trumpSuit,
    turn: vista.turn,
    trick: vista.trick,
    lastTrick: vista.lastTrick,
    lastWinner: vista.lastWinner,
    swapPermitido: vista.swapPermitido,
    dealer: 0,
    scores: vista.scores,
    gamesWon: vista.gamesWon,
    targetGames: vista.targetGames,
    events: vista.events,
    phase: vista.phase,
    winner: vista.winner,
  };
}
