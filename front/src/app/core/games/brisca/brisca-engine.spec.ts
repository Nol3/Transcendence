import { describe, expect, it } from 'vitest';

import { Card } from '../baraja';
import { fuerza, ganadorDeBaza, puntos, tantos } from '../bazas';
import {
  BriscaError,
  BriscaState,
  cambiarTriunfo,
  newGame,
  nextGame,
  play,
  puedeCambiarTriunfo,
  viewFor,
} from './brisca-engine';

function rng(seed = 1): () => number {
  let s = seed;
  return () => {
    s = (s * 1103515245 + 12345) % 2147483648;
    return s / 2147483648;
  };
}

function partida(n = 2, seed = 7): BriscaState {
  return newGame({
    names: Array.from({ length: n }, (_, i) => `J${i + 1}`),
    bots: [false, true].slice(0, n),
    rng: rng(seed),
  });
}

function carta(rank: number, suit: string): Card {
  return { id: `${rank}${suit}-0`, rank: rank as Card['rank'], suit: suit as Card['suit'], copy: 0 };
}

describe('Bazas · el orden de las cartas', () => {
  it('el tres va por delante del rey (la trampa al copiar del Culo)', () => {
    expect(fuerza(carta(3, 'o'))).toBeGreaterThan(fuerza(carta(12, 'o')));
    expect(fuerza(carta(1, 'o'))).toBeGreaterThan(fuerza(carta(3, 'o')));
    expect(fuerza(carta(2, 'o'))).toBeLessThan(fuerza(carta(4, 'o')));
  });

  it('los tantos son los de las normas', () => {
    expect(puntos(carta(1, 'o'))).toBe(11);
    expect(puntos(carta(3, 'c'))).toBe(10);
    expect(puntos(carta(12, 'e'))).toBe(4);
    expect(puntos(carta(11, 'b'))).toBe(3);
    expect(puntos(carta(10, 'o'))).toBe(2);
    expect(puntos(carta(7, 'o'))).toBe(0);
    expect(tantos([carta(1, 'o'), carta(3, 'c'), carta(7, 'e')])).toBe(21);
  });

  it('gana el triunfo más alto, aunque salga otro palo', () => {
    const baza = [
      { player: 0, card: carta(1, 'o') },
      { player: 1, card: carta(2, 'c') }, // triunfo, el más bajo
    ];
    expect(ganadorDeBaza(baza, 'c')).toBe(1);
  });

  it('sin triunfo en la mesa, gana la más alta del palo de salida', () => {
    const baza = [
      { player: 0, card: carta(4, 'o') },
      { player: 1, card: carta(12, 'c') }, // otro palo: no vale
    ];
    expect(ganadorDeBaza(baza, 'e')).toBe(0);
  });
});

describe('Brisca · reparto', () => {
  it('reparte tres cartas a cada uno y descubre la que pinta', () => {
    const s = partida(2);
    expect(s.players.map((p) => p.hand.length)).toEqual([3, 3]);
    expect(s.trumpCard).not.toBeNull();
    expect(s.trumpSuit).toBe(s.trumpCard!.suit);
  });

  it('no se pierde ninguna carta entre manos, mazo y la que pinta', () => {
    const s = partida(2);
    const enManos = s.players.reduce((n, p) => n + p.hand.length, 0);
    expect(enManos + s.deck.length + (s.trumpCard ? 1 : 0)).toBe(40);
  });

  it('no se puede jugar fuera de turno', () => {
    const s = partida(2);
    const otro = (s.turn + 1) % 2;
    expect(() => play(s, otro, s.players[otro].hand[0].id)).toThrow(BriscaError);
  });

  it('no se puede jugar una carta que no es tuya', () => {
    const s = partida(2);
    const ajeno = s.players[(s.turn + 1) % 2].hand[0].id;
    expect(() => play(s, s.turn, ajeno)).toThrow(/no es tuya/);
  });

  it('se puede jugar cualquier carta: no hay obligación de asistir', () => {
    const s = partida(2);
    // Cualquier carta de la mano vale, sea del palo que sea.
    for (const c of s.players[s.turn].hand) {
      expect(() => play(s, s.turn, c.id)).not.toThrow();
    }
  });
});

describe('Brisca · la baza', () => {
  it('el que gana se lleva las cartas, roba primero y sale', () => {
    let s = partida(2);
    const quien = s.turn;
    // Juega el triunfo más alto que tenga (o la primera carta).
    const triunfo = s.players[quien].hand.find((c) => c.suit === s.trumpSuit);
    s = play(s, quien, (triunfo ?? s.players[quien].hand[0]).id);
    s = play(s, s.turn, s.players[s.turn].hand[0].id);

    expect(s.trick).toHaveLength(0);
    expect(s.lastTrick).not.toBeNull();
    const ganador = s.lastTrick!.winner;
    expect(s.players[ganador].won).toHaveLength(2);
    expect(s.turn).toBe(ganador); // sale él
    expect(s.players[ganador].hand).toHaveLength(3); // ha robado
  });

  it('la carta que pinta es la última que se roba', () => {
    let s = partida(2);
    let vueltas = 0;
    while (s.trumpCard !== null && vueltas < 100) {
      vueltas++;
      s = play(s, s.turn, s.players[s.turn].hand[0].id);
      s = play(s, s.turn, s.players[s.turn].hand[0].id);
    }
    expect(s.trumpCard).toBeNull();
    expect(vueltas).toBeLessThan(100);
  });

  it('el juego termina cuando no queda nada que robar ni en la mano', () => {
    let s = partida(2);
    let vueltas = 0;
    while (s.phase === 'playing' && vueltas < 200) {
      vueltas++;
      s = play(s, s.turn, s.players[s.turn].hand[0].id);
      if (s.phase === 'playing') s = play(s, s.turn, s.players[s.turn].hand[0].id);
    }
    expect(s.phase).not.toBe('playing');
    expect(s.players.every((p) => p.hand.length === 0)).toBe(true);
    // Entre los dos se han repartido las 40 cartas.
    expect(s.players.reduce((n, p) => n + p.won.length, 0)).toBe(40);
    expect(s.scores[0] + s.scores[1]).toBe(120);
  });
});

describe('Brisca · el cambio del triunfo', () => {
  it('solo puede cambiarlo quien acaba de ganar la baza', () => {
    let s = partida(2);
    const quien = s.turn;
    s = play(s, quien, s.players[quien].hand[0].id);
    s = play(s, s.turn, s.players[s.turn].hand[0].id);
    const perdedor = (s.lastWinner! + 1) % 2;
    expect(() => cambiarTriunfo(s, perdedor)).toThrow(/acaba de ganar/);
    expect(puedeCambiarTriunfo(s, perdedor)).toBe(false);
  });

  it('si no tienes el siete de triunfo, no hay cambio', () => {
    let s = partida(2);
    const quien = s.turn;
    s = play(s, quien, s.players[quien].hand[0].id);
    s = play(s, s.turn, s.players[s.turn].hand[0].id);
    const ganador = s.lastWinner!;
    const tieneSiete = s.players[ganador].hand.some(
      (c) => c.rank === 7 && c.suit === s.trumpSuit,
    );
    if (tieneSiete) return; // en esta mano sí lo tiene: el otro caso lo cubre el test de abajo
    expect(() => cambiarTriunfo(s, ganador)).toThrow(/siete de triunfo/);
  });

  it('con el siete en la mano, se queda con la carta que pintaba', () => {
    let s = partida(2);
    const quien = s.turn;
    s = play(s, quien, s.players[quien].hand[0].id);
    s = play(s, s.turn, s.players[s.turn].hand[0].id);
    const ganador = s.lastWinner!;
    const pintaba = s.trumpCard!;
    // Se le da el siete de ese palo a mano para poder probarlo.
    const siete: Card = { id: `7${pintaba.suit}-9`, rank: 7, suit: pintaba.suit, copy: 9 };
    s.players[ganador].hand = [...s.players[ganador].hand, siete];

    s = cambiarTriunfo(s, ganador);
    expect(s.trumpCard!.id).toBe(siete.id);
    expect(s.players[ganador].hand.some((c) => c.id === pintaba.id)).toBe(true);
    expect(s.events.at(-1)).toMatchObject({ kind: 'swap', player: ganador });
  });
});

describe('Brisca · la partida', () => {
  it('el empate a 60 anula el juego', () => {
    const s = partida(2);
    // Se monta a mano: 60 tantos cada uno.
    const mitad = [
      carta(1, 'o'), carta(3, 'c'), carta(12, 'e'), carta(11, 'b'), carta(10, 'o'),
      carta(1, 'c'), carta(3, 'e'), carta(12, 'b'), carta(11, 'o'), carta(10, 'c'),
    ];
    s.players[0].won = mitad;
    s.players[1].won = mitad.map((c, i) => ({ ...c, id: `${c.id}-b${i}` }));
    s.deck = [];
    s.trumpCard = null;
    s.players[0].hand = [];
    s.players[1].hand = [];
    // Se juega una baza imposible para forzar el cierre: mejor llamar al final directamente.
    const terminado = (() => {
      // Se resuelve jugando la última baza con las cartas ya repartidas: se rellenan a mano.
      s.players[0].hand = [carta(7, 'o')];
      s.players[1].hand = [carta(6, 'o')];
      let x = play(s, 0, s.players[0].hand[0].id);
      x = play(x, 1, x.players[1].hand[0].id);
      return x;
    })();
    expect(terminado.phase).not.toBe('playing');
    expect(terminado.events.some((e) => e.kind === 'game-end' && e.anulado)).toBe(true);
    expect(terminado.gamesWon).toEqual([0, 0]);
  });

  it('una partida entera con bots termina y no pierde cartas', () => {
    let s = partida(2, 99);
    let vueltas = 0;
    while (s.phase !== 'match-end' && vueltas < 400) {
      vueltas++;
      if (s.phase === 'game-end') {
        s = nextGame(s, rng(vueltas));
        continue;
      }
      s = play(s, s.turn, s.players[s.turn].hand[0].id);
    }
    expect(s.phase).toBe('match-end');
    expect(vueltas).toBeLessThan(400);
    expect(s.gamesWon.some((g) => g >= s.targetGames)).toBe(true);
    const total = s.players.reduce((n, p) => n + p.hand.length + p.won.length, 0);
    expect(total + s.deck.length + (s.trumpCard ? 1 : 0)).toBe(40);
  });

  it('no se reparte el juego siguiente si el anterior sigue vivo', () => {
    const s = partida(2);
    expect(() => nextGame(s)).toThrow(/no ha terminado/);
  });
});

describe('Brisca · lo que ve cada uno', () => {
  it('la vista trae tu mano y tus bazas, y de los demás solo el recuento', () => {
    const s = partida(2);
    const vista = viewFor(s, 1);
    expect(vista.myHand).toHaveLength(3);
    expect(vista.players[0]).not.toHaveProperty('hand');
    expect(vista.players[0].handCount).toBe(3);
    expect(vista).not.toHaveProperty('deck');
    expect(vista.deckCount).toBe(s.deck.length);
  });

  it('la carta que pinta sí se ve (está en la mesa)', () => {
    const s = partida(2);
    const vista = viewFor(s, 0);
    expect(vista.trumpCard?.id).toBe(s.trumpCard?.id);
    expect(vista.trumpSuit).toBe(s.trumpSuit);
  });
});
