import { Card } from '../baraja';
import { Jugada, MusEvent, MusState } from './mus-engine';

/**
 * Adapta lo que manda el servidor a la forma del motor local.
 *
 * Aquí hay un detalle que importa: en el mus las jugadas de los rivales **no se ven**. La vista del
 * servidor manda la tuya y la de tu compañero (que en la mesa real se dirían por señas) y, de los
 * rivales, nada: por eso se rellenan con una jugada vacía, no con la de verdad.
 */
export interface MusVista {
  players: { id: number; name: string; isBot: boolean; handCount: number; connected?: boolean }[];
  teams: { id: number; players: number[]; piedras: number; juegos: number }[];
  myHand: Card[];
  myJugada: Jugada;
  mano: number;
  phase: MusState['phase'];
  lance: MusState['lance'];
  turn: number | null;
  envite: MusState['envite'];
  responde: number | null;
  pasados: number[];
  companero: { id: number; name: string; jugada: Jugada } | null;
  events: MusEvent[];
  winner: number | null;
}

const JUGADA_VACIA: Jugada = {
  grande: 0,
  chica: 0,
  pares: { categoria: null, alto: 0 },
  juego: null,
  punto: 0,
};

/** Cartas de relleno: solo se usan para contar (nunca se enseñan). */
function relleno(cuantas: number): Card[] {
  return Array.from({ length: cuantas }, (_, i) => ({
    id: `oculta-${i}`,
    rank: 1 as Card['rank'],
    suit: 'o' as Card['suit'],
    copy: 0,
  }));
}

export function estadoDesdeVista(vista: MusVista, seat: number): MusState {
  const turno = vista.turn;
  return {
    players: vista.players.map((p) => ({
      id: p.id,
      name: p.name,
      isBot: p.isBot,
      hand: p.id === seat ? vista.myHand : relleno(p.handCount),
      jugada:
        p.id === seat
          ? vista.myJugada
          : p.id === vista.companero?.id
            ? vista.companero.jugada
            : JUGADA_VACIA,
      // Se marca a todos menos al que le toca hablar, para que el turno que calcula la mesa sea
      // el mismo que dice el servidor.
      hablado: p.id !== turno,
      descartes: 0,
      connected: p.connected,
    })),
    // Las parejas son siempre dos: el tipo lo pide como tupla.
    teams: [
      { ...vista.teams[0], players: [...vista.teams[0].players] },
      { ...vista.teams[1], players: [...vista.teams[1].players] },
    ],
    mano: vista.mano,
    phase: vista.phase,
    lance: vista.lance,
    habladoEnLance: [],
    envite: vista.envite,
    responde: vista.responde,
    pasados: vista.pasados,
    piedrasDelLance: 0,
    ganadorLance: null,
    events: vista.events,
    winner: vista.winner,
  };
}
