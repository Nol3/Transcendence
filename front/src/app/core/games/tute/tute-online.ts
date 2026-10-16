import { Card, SpanishSuit } from '../baraja';
import { Baza } from '../bazas';
import { TuteEvent, TuteState } from './tute-engine';

/**
 * Adapta lo que manda el servidor a la forma del motor local, para que el modo «con amigos» use la
 * misma mesa que el modo contra bots.
 *
 * El servidor manda tu mano y tus bazas, y de los demás solo el recuento (con los tantos ya
 * contados). La baceta solo llega como número: cuántas quedan.
 */
export interface TuteVista {
  players: {
    id: number;
    name: string;
    isBot: boolean;
    handCount: number;
    tantos?: number;
    cantados?: number;
    connected?: boolean;
  }[];
  myHand: Card[];
  myWon: Card[];
  trumpCard: Card | null;
  trumpSuit: SpanishSuit;
  bacetaCount: number;
  turn: number;
  trick: Baza[];
  lastTrick: { winner: number; cards: Baza[] } | null;
  lastWinner: number | null;
  scores: number[];
  targetTantos: number;
  events: TuteEvent[];
  phase: TuteState['phase'];
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

export function estadoDesdeVista(vista: TuteVista, seat: number): TuteState {
  return {
    players: vista.players.map((p) => ({
      id: p.id,
      name: p.name,
      isBot: p.isBot,
      hand: p.id === seat ? vista.myHand : relleno(p.handCount),
      won: p.id === seat ? vista.myWon : [],
      cantados: p.cantados ?? 0,
      tantos: p.tantos ?? 0,
      connected: p.connected,
    })),
    baceta: relleno(vista.bacetaCount),
    trumpCard: vista.trumpCard,
    trumpSuit: vista.trumpSuit,
    turn: vista.turn,
    trick: vista.trick,
    lastTrick: vista.lastTrick,
    lastWinner: vista.lastWinner,
    // Los acuses ya cantados en esta baza no vienen en la vista: si el jugador intenta repetir,
    // el servidor lo rechaza, que es quien manda.
    cantadoEnEstaBaza: [],
    esUltimaBaza: false,
    scores: vista.scores,
    targetTantos: vista.targetTantos,
    events: vista.events,
    phase: vista.phase,
    winner: vista.winner,
  };
}
