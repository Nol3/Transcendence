import { describe, expect, it } from 'vitest';

import { Card, SpanishSuit } from '../baraja';
import { Baza } from '../bazas';
import {
  ACUSE_OTRO,
  ACUSE_TRIUNFO,
  DIEZ_ULTIMAS,
  TuteError,
  TuteState,
  acusesDisponibles,
  cantar,
  cantarTute,
  cartasPorJugador,
  esJugadaLegal,
  jugadasLegales,
  newGame,
  nextGame,
  play,
  tieneTute,
  viewFor,
} from './tute-engine';

function rng(seed = 1): () => number {
  let s = seed;
  return () => {
    s = (s * 1103515245 + 12345) % 2147483648;
    return s / 2147483648;
  };
}

function partida(n = 2, seed = 7): TuteState {
  return newGame({
    names: Array.from({ length: n }, (_, i) => `J${i + 1}`),
    bots: [false, true].slice(0, n),
    rng: rng(seed),
  });
}

function carta(rank: number, suit: string, copy = 0): Card {
  return { id: `${rank}${suit}-${copy}`, rank: rank as Card['rank'], suit: suit as Card['suit'], copy };
}

/** Monta una mesa a mano: manos concretas, baceta y triunfo a elección. */
function mesa(
  manos: Card[][],
  opts: { baceta?: Card[]; triunfo?: SpanishSuit; trick?: Baza[]; lastWinner?: number | null } = {},
): TuteState {
  // Siempre dos jugadores como mínimo: aunque el test solo mire la mano del primero, hace falta
  // alguien al otro lado de la mesa (es quien ha jugado la carta que hay en la baza).
  const s = partida(Math.max(2, manos.length));
  s.players = s.players.map((p, i) => ({ ...p, hand: manos[i] ?? [], won: [], cantados: 0 }));
  s.baceta = opts.baceta ?? [];
  s.trumpSuit = opts.triunfo ?? 'o';
  s.trick = opts.trick ?? [];
  s.lastWinner = opts.lastWinner ?? null;
  s.cantadoEnEstaBaza = [];
  s.turn = 0;
  return s;
}

describe('Tute · reparto', () => {
  it('ocho cartas a dos, trece a tres', () => {
    expect(cartasPorJugador(2)).toBe(8);
    expect(cartasPorJugador(3)).toBe(13);
    const s = partida(2);
    expect(s.players.map((p) => p.hand.length)).toEqual([8, 8]);
    expect(s.trumpCard).not.toBeNull();
  });

  it('no se pierde ninguna carta entre manos, baceta y la que pinta', () => {
    const s = partida(2);
    const enManos = s.players.reduce((n, p) => n + p.hand.length, 0);
    expect(enManos + s.baceta.length + (s.trumpCard ? 1 : 0)).toBe(40);
  });
});

describe('Tute · las obligaciones (aquí está el juego)', () => {
  it('con baceta, solo obliga el triunfo y sin montar', () => {
    // Sale trébol (triunfo) y tengo un trébol bajo y una carta de otro palo: obligado a jugar trébol.
    const s = mesa(
      [[carta(2, 'c'), carta(1, 'e')]],
      { baceta: [carta(4, 'b')], triunfo: 'c', trick: [{ player: 1, card: carta(7, 'c') }] },
    );
    const legales = jugadasLegales(s, 0);
    expect(legales.map((c) => c.id)).toEqual(['2c-0']); // el dos, aunque no monte al siete
  });

  it('con baceta, si sale otro palo vale cualquier carta', () => {
    const s = mesa(
      [[carta(2, 'c'), carta(1, 'e')]],
      { baceta: [carta(4, 'b')], triunfo: 'c', trick: [{ player: 1, card: carta(7, 'e') }] },
    );
    expect(jugadasLegales(s, 0)).toHaveLength(2);
  });

  it('sin baceta, hay que montar si se puede', () => {
    // Sale oros con un cuatro; tengo el siete y el dos de oros: obligado a montar con el siete.
    const s = mesa(
      [[carta(7, 'o'), carta(2, 'o')]],
      { baceta: [], triunfo: 'c', trick: [{ player: 1, card: carta(4, 'o') }] },
    );
    expect(jugadasLegales(s, 0).map((c) => c.id)).toEqual(['7o-0']);
  });

  it('sin baceta y sin poder montar, asistes con lo que tengas', () => {
    // Ojo: el tres monta al siete (va por delante del rey), así que para "no poder montar" hay
    // que usar cartas que de verdad no llegan.
    const s = mesa(
      [[carta(2, 'o'), carta(4, 'o')]],
      { baceta: [], triunfo: 'c', trick: [{ player: 1, card: carta(7, 'o') }] },
    );
    expect(jugadasLegales(s, 0).map((c) => c.id).sort()).toEqual(['2o-0', '4o-0']);
  });

  it('sin baceta, si no tienes del palo estás obligado a fallar', () => {
    const s = mesa(
      [[carta(2, 'c'), carta(4, 'e')]],
      { baceta: [], triunfo: 'c', trick: [{ player: 1, card: carta(7, 'o') }] },
    );
    expect(jugadasLegales(s, 0).map((c) => c.id)).toEqual(['2c-0']); // el trébol, obligado
  });

  it('sin del palo y sin triunfo, vale cualquier carta (contrafallo)', () => {
    const s = mesa(
      [[carta(2, 'b'), carta(4, 'e')]],
      { baceta: [], triunfo: 'c', trick: [{ player: 1, card: carta(7, 'o') }] },
    );
    expect(jugadasLegales(s, 0)).toHaveLength(2);
  });

  it('jugar una carta que no toca se rechaza con su motivo', () => {
    // Con el siete en la mesa y sin poder montar, las dos cartas valen.
    const s = mesa(
      [[carta(2, 'o'), carta(4, 'o')]],
      { baceta: [], triunfo: 'c', trick: [{ player: 1, card: carta(7, 'o') }] },
    );
    expect(esJugadaLegal(s, 0, '2o-0')).toBe(true);
    expect(esJugadaLegal(s, 0, '4o-0')).toBe(true);

    // Pero si puedes montar, estás obligado: el tres sí monta al siete.
    const s2 = mesa(
      [[carta(3, 'o'), carta(2, 'o')]],
      { baceta: [], triunfo: 'c', trick: [{ player: 1, card: carta(7, 'o') }] },
    );
    expect(esJugadaLegal(s2, 0, '2o-0')).toBe(false);
    expect(esJugadaLegal(s2, 0, '3o-0')).toBe(true);
    expect(() => play(s2, 0, '2o-0')).toThrow(TuteError);
  });

  it('el primero en salir puede jugar cualquier carta', () => {
    const s = mesa([[carta(2, 'o'), carta(3, 'e')]], { baceta: [carta(4, 'b')], triunfo: 'c' });
    expect(jugadasLegales(s, 0)).toHaveLength(2);
  });
});

describe('Tute · acuses', () => {
  it('rey y caballo del triunfo valen 40; de otro palo, 20', () => {
    const s = mesa(
      [[carta(12, 'c'), carta(11, 'c'), carta(12, 'o'), carta(11, 'o')]],
      { baceta: [], triunfo: 'c', lastWinner: 0 },
    );
    expect(acusesDisponibles(s, 0).sort()).toEqual(['c', 'o']);

    const conCuarenta = cantar(s, 0, 'c');
    expect(conCuarenta.players[0].cantados).toBe(ACUSE_TRIUNFO);
    expect(conCuarenta.events.at(-1)).toMatchObject({ cuarenta: true, puntos: 40 });

    const conVeinte = cantar(s, 0, 'o');
    expect(conVeinte.players[0].cantados).toBe(ACUSE_OTRO);
  });

  it('no se puede cantar si no has ganado la baza', () => {
    const s = mesa([[carta(12, 'c'), carta(11, 'c')]], { baceta: [], triunfo: 'c', lastWinner: 1 });
    expect(acusesDisponibles(s, 0)).toEqual([]);
    expect(() => cantar(s, 0, 'c')).toThrow(/ganar una baza/);
  });

  it('solo se canta un acuse por baza', () => {
    const s = mesa(
      [[carta(12, 'c'), carta(11, 'c'), carta(12, 'o'), carta(11, 'o')]],
      { baceta: [], triunfo: 'c', lastWinner: 0 },
    );
    const una = cantar(s, 0, 'c');
    expect(() => cantar(una, 0, 'o')).toThrow(/un acuse por baza/);
  });

  it('sin rey y caballo del mismo palo no hay acuse', () => {
    const s = mesa([[carta(12, 'c'), carta(11, 'e')]], { baceta: [], triunfo: 'c', lastWinner: 0 });
    expect(() => cantar(s, 0, 'c')).toThrow(/rey y caballo/);
  });
});

describe('Tute · el tute y el final', () => {
  it('los cuatro reyes son un tute y ganan al instante', () => {
    const s = mesa(
      [[carta(12, 'o'), carta(12, 'c'), carta(12, 'e'), carta(12, 'b')]],
      { baceta: [], triunfo: 'c' },
    );
    expect(tieneTute(s, 0)).toBe(true);
    const ganado = cantarTute(s, 0);
    expect(ganado.phase).toBe('match-end');
    expect(ganado.winner).toBe(0);
  });

  it('sin los cuatro no hay tute', () => {
    const s = mesa(
      [[carta(12, 'o'), carta(12, 'c'), carta(12, 'e'), carta(11, 'b')]],
      { baceta: [], triunfo: 'c' },
    );
    expect(tieneTute(s, 0)).toBe(false);
    expect(() => cantarTute(s, 0)).toThrow(/cuatro reyes/);
  });

  it('ganar la última baza vale 10 tantos', () => {
    // Los dos con una carta y sin baceta: la que se juega es la última baza.
    const s = mesa([[carta(1, 'o')], [carta(2, 'o')]], { baceta: [], triunfo: 'c' });
    s.trumpCard = null; // ya no queda nada que robar: esta es la última baza
    const jugado = play(play(s, 0, '1o-0'), 1, '2o-0');
    expect(jugado.phase).not.toBe('playing');
    const evento = jugado.events.find((e) => e.kind === 'game-end');
    expect(evento).toMatchObject({ ultima: 0 }); // ganó el as
    expect(jugado.scores[0]).toBe(11 + DIEZ_ULTIMAS);
    expect(jugado.scores[1]).toBe(0);
  });

  it('una partida entera con bots termina y no pierde cartas', () => {
    let s = partida(2, 99);
    let vueltas = 0;
    while (s.phase !== 'match-end' && vueltas < 600) {
      vueltas++;
      if (s.phase === 'game-end') {
        s = nextGame(s, rng(vueltas));
        continue;
      }
      const legales = jugadasLegales(s, s.turn);
      s = play(s, s.turn, legales[0].id);
    }
    expect(s.phase).toBe('match-end');
    expect(vueltas).toBeLessThan(600);
    const total = s.players.reduce((n, p) => n + p.hand.length + p.won.length, 0);
    expect(total + s.baceta.length + (s.trumpCard ? 1 : 0)).toBe(40);
  });

  it('no se reparte el juego siguiente si el anterior sigue vivo', () => {
    expect(() => nextGame(partida(2))).toThrow(/no ha terminado/);
  });
});

describe('Tute · lo que ve cada uno', () => {
  it('la vista trae tu mano y tus jugadas legales, y de los demás solo el recuento', () => {
    const s = partida(2);
    const vista = viewFor(s, 1);
    expect(vista.myHand).toHaveLength(8);
    expect(vista.players[0]).not.toHaveProperty('hand');
    expect(vista.players[0].handCount).toBe(8);
    expect(vista.jugadasLegales.length).toBeGreaterThan(0);
    expect(vista).not.toHaveProperty('baceta');
  });

  it('las jugadas legales de la vista son las de verdad', () => {
    const s = mesa(
      [[carta(7, 'o'), carta(2, 'o')]],
      { baceta: [], triunfo: 'c', trick: [{ player: 1, card: carta(4, 'o') }] },
    );
    const vista = viewFor(s, 0);
    expect(vista.jugadasLegales).toEqual(['7o-0']);
    expect(vista.obligaMontar).toBe(true);
  });
});
