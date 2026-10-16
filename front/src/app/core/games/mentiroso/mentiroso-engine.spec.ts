import { describe, expect, it } from 'vitest';

import { Card, SUITS, SpanishRank } from '../baraja';
import {
  MANOS_POR_DEFECTO,
  MentirosoError,
  MentirosoState,
  desconfiar,
  newGame,
  nextHand,
  play,
  retirar,
  viewFor,
} from './mentiroso-engine';

/** Generador con semilla: los tests tienen que salir siempre igual. */
function rng(seed = 1): () => number {
  let s = seed;
  return () => {
    s = (s * 1103515245 + 12345) % 2147483648;
    return s / 2147483648;
  };
}

function partida(n = 4, seed = 7): MentirosoState {
  return newGame({
    names: Array.from({ length: n }, (_, i) => `J${i + 1}`),
    rng: rng(seed),
  });
}

/** Una carta cualquiera de la mano de un jugador. */
function cartaDe(state: MentirosoState, id: number, i = 0): Card {
  return state.players[id].hand[i];
}

describe('Mentiroso · reparto y turnos', () => {
  it('reparte las 40 cartas sin perder ninguna', () => {
    const s = partida(4);
    const total = s.players.reduce((n, p) => n + p.hand.length, 0);
    expect(total).toBe(40);
    const ids = new Set(s.players.flatMap((p) => p.hand.map((c) => c.id)));
    expect(ids.size).toBe(40);
  });

  it('con seis jugadores no salen iguales, y así está bien', () => {
    const s = partida(6);
    const totales = s.players.map((p) => p.hand.length);
    expect(totales.reduce((a, b) => a + b, 0)).toBe(40);
    expect(Math.max(...totales) - Math.min(...totales)).toBeLessThanOrEqual(1);
  });

  it('no deja jugar fuera de turno', () => {
    const s = partida(4);
    expect(() => play(s, 1, [cartaDe(s, 1).id], 5)).toThrow(MentirosoError);
  });

  it('no deja jugar una carta que no es tuya', () => {
    const s = partida(4);
    const ajena = cartaDe(s, 1).id;
    expect(() => play(s, 0, [ajena], 5)).toThrow(/no es tuya/);
  });

  it('el que abre fija el valor y los demás no lo pueden cambiar', () => {
    let s = partida(4);
    s = play(s, 0, [cartaDe(s, 0).id], 5);
    expect(s.claimedRank).toBe(5);
    expect(() => play(s, 1, [cartaDe(s, 1).id], 7)).toThrow(/seguir el valor/);
  });

  it('no deja abrir sin decir qué cartas son', () => {
    const s = partida(4);
    expect(() => play(s, 0, [cartaDe(s, 0).id])).toThrow(/qué cartas son/);
  });
});

describe('Mentiroso · la cantidad no se puede mentir', () => {
  it('la cantidad anunciada es la que se ha puesto de verdad', () => {
    let s = partida(4);
    const cartas = s.players[0].hand.slice(0, 3).map((c) => c.id);
    s = play(s, 0, cartas, 5);
    const puesto = s.events.at(-1);
    expect(puesto).toMatchObject({ kind: 'play', count: 3 });
    expect(s.pile).toHaveLength(3);
  });

  it('sí se puede mentir en el valor (esa es la gracia)', () => {
    let s = partida(4);
    // Busca una carta que NO sea el 5 y juégala diciendo que es un 5.
    const mentirosa = s.players[0].hand.find((c) => c.rank !== 5)!;
    s = play(s, 0, [mentirosa.id], 5);
    expect(s.lastPlay?.claimedRank).toBe(5);
    expect(s.lastPlay?.cards[0].rank).not.toBe(5);
  });
});

describe('Mentiroso · desconfiar', () => {
  it('puede desconfiar cualquiera, no solo el siguiente', () => {
    let s = partida(4);
    const mentirosa = s.players[0].hand.find((c) => c.rank !== 5)!;
    s = play(s, 0, [mentirosa.id], 5);
    // El jugador 3 no es el siguiente (sería el 1) y aun así puede.
    s = desconfiar(s, 3);
    expect(s.events.some((e) => e.kind === 'challenge' && e.player === 3)).toBe(true);
  });

  it('si mentía, se lleva el montón el que puso', () => {
    let s = partida(4);
    const antes = s.players[0].hand.length;
    const mentirosa = s.players[0].hand.find((c) => c.rank !== 5)!;
    s = play(s, 0, [mentirosa.id], 5);
    s = desconfiar(s, 1);
    expect(s.pile).toHaveLength(0);
    expect(s.players[0].hand.length).toBe(antes); // la puso y la recupera
    expect(s.events.at(-1)).toMatchObject({ kind: 'take', player: 0, mentira: true });
  });

  it('si decía la verdad, se lleva el montón el que desconfió', () => {
    let s = partida(4);
    const suya = s.players[0].hand[0];
    s = play(s, 0, [suya.id], suya.rank); // esta vez no miente
    s = desconfiar(s, 2);
    expect(s.players[2].hand.some((c) => c.id === suya.id)).toBe(true);
    expect(s.events.at(-1)).toMatchObject({ kind: 'take', player: 2, mentira: false });
  });

  it('quien se lleva el montón abre la ronda siguiente, con valor libre', () => {
    let s = partida(4);
    const mentirosa = s.players[0].hand.find((c) => c.rank !== 5)!;
    s = play(s, 0, [mentirosa.id], 5);
    s = desconfiar(s, 1); // miente el 0, se lo lleva el 0
    expect(s.turn).toBe(0);
    expect(s.claimedRank).toBeNull();
  });

  it('no se puede desconfiar si no hay nada puesto', () => {
    const s = partida(4);
    expect(() => desconfiar(s, 1)).toThrow(/nada que desconfiar/);
  });

  it('no te puedes desconfiar a ti mismo', () => {
    let s = partida(4);
    s = play(s, 0, [cartaDe(s, 0).id], 5);
    expect(() => desconfiar(s, 0)).toThrow(/a ti mismo/);
  });

  it('a quien se ha quedado sin cartas no se le puede desconfiar', () => {
    let s = partida(3);
    // El jugador 0 se descarga de todo diciendo que son cincos (mienta o no, da igual).
    const todas = s.players[0].hand.map((c) => c.id);
    s = play(s, 0, todas, 5);
    expect(s.phase).toBe('hand-end'); // se queda sin cartas: gana la mano
    expect(() => desconfiar(s, 1)).toThrow(/no se le desconfía|ya ha terminado/);
  });
});

describe('Mentiroso · retirar los cuatro iguales', () => {
  it('retira las cuatro cartas del mismo valor y las saca del juego', () => {
    let s = partida(4);
    // Se le dan cuatro iguales a mano (una de cada palo) para poder probarlo.
    const valor = s.players[0].hand[0].rank;
    const cuatro = SUITS.map((suit) => ({ id: `${valor}${suit}-0`, suit, rank: valor, copy: 0 }));
    s.players[0].hand = [...cuatro, ...s.players[0].hand.slice(4)];

    const antes = s.players[0].hand.length;
    s = retirar(s, 0, valor);
    expect(s.players[0].hand.length).toBe(antes - 4);
    expect(s.players[0].retired).toHaveLength(4);
    expect(s.events.at(-1)).toMatchObject({ kind: 'retire', player: 0 });
  });

  it('no deja retirar si no tienes los cuatro', () => {
    const s = partida(4);
    expect(() => retirar(s, 0, 5)).toThrow(/cuatro cartas/);
  });

  it('retirar sin ser tu turno no mueve el turno', () => {
    let s = partida(4);
    const valor = s.players[2].hand[0].rank;
    const cuatro = SUITS.map((suit) => ({ id: `${valor}${suit}-0`, suit, rank: valor, copy: 0 }));
    s.players[2].hand = [...cuatro, ...s.players[2].hand.slice(4)];
    const turno = s.turn;
    s = retirar(s, 2, valor);
    expect(s.turn).toBe(turno);
  });
});

describe('Mentiroso · la partida', () => {
  it('la mano la gana quien se queda sin cartas', () => {
    let s = partida(3);
    const todas = s.players[1].hand.map((c) => c.id);
    s = play(s, 0, [cartaDe(s, 0).id], 5);
    s = play(s, 1, todas, 5);
    expect(s.phase).toBe('hand-end');
    expect(s.winner).toBe(1);
    expect(s.players[1].wins).toBe(1);
  });

  it('la partida termina al llegar a las manos pactadas', () => {
    let s = partida(3);
    for (let mano = 0; mano < MANOS_POR_DEFECTO; mano++) {
      if (s.phase === 'hand-end') s = nextHand(s, rng(mano + 3));
      // El jugador 0 se descarga entero en su primer turno.
      s = play(s, 0, s.players[0].hand.map((c) => c.id), 5);
      if (s.phase === 'hand-end' && mano < MANOS_POR_DEFECTO - 1) s = nextHand(s, rng(mano + 10));
    }
    expect(s.players[0].wins).toBe(MANOS_POR_DEFECTO);
    expect(s.phase).toBe('match-end');
  });

  it('no se puede repartir la mano siguiente si la anterior sigue viva', () => {
    const s = partida(3);
    expect(() => nextHand(s)).toThrow(/no ha terminado/);
  });

  it('una partida entera con bots siempre termina y no pierde cartas', () => {
    let s = partida(4, 99);
    let vueltas = 0;
    while (s.phase !== 'match-end' && vueltas < 4000) {
      vueltas++;
      if (s.phase === 'hand-end') {
        s = nextHand(s, rng(vueltas));
        continue;
      }
      // Bot sencillo: echa una carta diciendo lo que toca (miente si hace falta).
      const yo = s.players[s.turn];
      const valor = (s.claimedRank ?? yo.hand[0].rank) as SpanishRank;
      const carta = yo.hand.find((c) => c.rank === valor) ?? yo.hand[0];
      s = play(s, s.turn, [carta.id], valor);
    }
    expect(s.phase).toBe('match-end');
    expect(vueltas).toBeLessThan(4000);

    // Al acabar cada mano, las 40 cartas siguen repartidas entre todos.
    const total = s.players.reduce((n, p) => n + p.hand.length + p.retired.length, 0);
    expect(total + s.pile.length).toBe(40);
  });
});

describe('Mentiroso · lo que ve cada uno', () => {
  it('la vista trae tu mano entera y de los demás solo el número', () => {
    const s = partida(4);
    const vista = viewFor(s, 1);
    expect(vista.myHand).toHaveLength(s.players[1].hand.length);
    expect(vista.myHand[0]).toHaveProperty('suit');
    // De los otros, solo el recuento: no hay forma de ver sus cartas.
    const otro = vista.players[0];
    expect(otro).not.toHaveProperty('hand');
    expect(otro.handCount).toBe(s.players[0].hand.length);
  });

  it('el montón nunca se revela, solo cuántas cartas lleva', () => {
    let s = partida(4);
    s = play(s, 0, [cartaDe(s, 0).id], 5);
    const vista = viewFor(s, 2);
    expect(vista.pileCount).toBe(1);
    expect(vista).not.toHaveProperty('pile');
    expect(JSON.stringify(vista)).not.toContain('"cards"');
  });
});
