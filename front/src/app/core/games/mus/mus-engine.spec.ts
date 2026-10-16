import { describe, expect, it } from 'vitest';

import { Card } from '../baraja';
import { botDecision } from './mus-bots';
import {
  JUGADORES,
  LANCES,
  PIEDRAS_PARA_GANAR,
  MusState,
  comparar,
  cortarMus,
  decirMus,
  descartar,
  envidar,
  evaluar,
  fuerzaMus,
  newGame,
  nextHand,
  noQuiero,
  ordago,
  ordenJuego,
  parejaDe,
  pasar,
  quiero,
  turnoActual,
  viewFor,
} from './mus-engine';

function rng(seed = 1): () => number {
  let s = seed;
  return () => {
    s = (s * 1103515245 + 12345) % 2147483648;
    return s / 2147483648;
  };
}

function carta(rank: number, suit = 'o', copy = 0): Card {
  return { id: `${rank}${suit}-${copy}`, rank: rank as Card['rank'], suit: suit as Card['suit'], copy };
}

function partida(seed = 5): MusState {
  return newGame({ names: ['A', 'B', 'C', 'D'], bots: [false, false, false, false], rng: rng(seed) });
}

/** Cuatro manos cualquiera, para los tests que solo miran las apuestas. */
function manosBase(): Card[][] {
  return [
    [carta(12), carta(7), carta(4), carta(1)],
    [carta(11), carta(6), carta(5), carta(2)],
    [carta(10), carta(7, 'c'), carta(4, 'c'), carta(1, 'c')],
    [carta(7, 'e'), carta(6, 'e'), carta(5, 'e'), carta(2, 'e')],
  ];
}

/** Monta una mesa con manos concretas. */
function mesa(manos: Card[][]): MusState {
  const s = partida();
  s.players = s.players.map((p, i) => ({ ...p, hand: manos[i], jugada: evaluar(manos[i]), hablado: false }));
  s.phase = 'lances';
  s.lance = 'grande';
  return s;
}

describe('Mus · el orden de las cartas (ocho reyes y ocho ases)', () => {
  it('el tres vale lo mismo que el rey y el dos lo mismo que el as', () => {
    expect(fuerzaMus(carta(3))).toBe(fuerzaMus(carta(12)));
    expect(fuerzaMus(carta(2))).toBe(fuerzaMus(carta(1)));
  });

  it('de mayor a menor: rey o tres, caballo, sota, siete, seis, cinco, cuatro, dos o as', () => {
    const orden = [12, 3, 11, 10, 7, 6, 5, 4, 1, 2].map((r) => fuerzaMus(carta(r)));
    expect(orden).toEqual([...orden].sort((a, b) => b - a));
  });
});

describe('Mus · las jugadas', () => {
  it('la grande es la carta más alta y la chica la más baja', () => {
    const j = evaluar([carta(12), carta(7), carta(4), carta(1)]);
    expect(j.grande).toBe(fuerzaMus(carta(12)));
    expect(j.chica).toBe(fuerzaMus(carta(1)));
  });

  it('las parejas van por categorías: duples > medias > pareja', () => {
    expect(evaluar([carta(12), carta(12), carta(7), carta(7)]).pares.categoria).toBe('duples');
    expect(evaluar([carta(12), carta(12), carta(12), carta(12)]).pares.categoria).toBe('duples');
    expect(evaluar([carta(12), carta(12), carta(12), carta(7)]).pares.categoria).toBe('medias');
    expect(evaluar([carta(12), carta(12), carta(7), carta(4)]).pares.categoria).toBe('par');
    expect(evaluar([carta(12), carta(7), carta(4), carta(1)]).pares.categoria).toBe(null);
  });

  it('a igualdad de pares gana la carta más alta de la combinación', () => {
    const conReyes = evaluar([carta(12), carta(12), carta(4), carta(1)]);
    const conCuatros = evaluar([carta(4), carta(4), carta(12), carta(1)]);
    expect(comparar(conReyes, conCuatros, 'pares')).toBeGreaterThan(0);
  });

  it('el juego es sumar 31 o más; el punto, lo que se acerca al 30', () => {
    // Para el juego el tres vale 3: 3 + sota (10) + rey (10) + caballo (10) = 33.
    expect(evaluar([carta(3), carta(10), carta(12), carta(11)]).juego).toBe(33);
    // Pero para el punto el tres vale 10 (como el rey): 10 + 10 + 10 + 10 = 40.
    expect(evaluar([carta(3), carta(10), carta(12), carta(11)]).punto).toBe(40);
    expect(evaluar([carta(7), carta(6), carta(5), carta(4)]).juego).toBe(null);
    expect(evaluar([carta(7), carta(6), carta(5), carta(4)]).punto).toBe(22);
  });

  it('el orden del juego es 31, 32, 40, 37, 36, 35, 34, 33 (el 38 y el 39 no existen)', () => {
    expect(ordenJuego(31)).toBe(0); // la «una», la mejor
    expect(ordenJuego(32)).toBe(1);
    expect(ordenJuego(40)).toBe(2);
    expect(ordenJuego(33)).toBe(7); // la peor
    expect(ordenJuego(38)).toBe(-1);
    expect(ordenJuego(39)).toBe(-1);
    expect(ordenJuego(30)).toBe(-1);
  });

  it('el 31 gana a cualquier otro juego', () => {
    const una = evaluar([carta(12), carta(11), carta(10), carta(1)]); // 10+10+10+1 = 31
    const peor = evaluar([carta(3), carta(10), carta(12), carta(11)]); // 3+10+10+10 = 33
    expect(una.juego).toBe(31);
    expect(peor.juego).toBe(33);
    expect(comparar(una, peor, 'juego')).toBeGreaterThan(0);
  });

  it('sin juego se va al punto, y gana el que más se acerca al 30', () => {
    // Ninguna llega a 31, así que se compara el punto: 28 gana a 27.
    const veintiocho = evaluar([carta(12), carta(7), carta(6), carta(5)]);
    const veintisiete = evaluar([carta(12), carta(7), carta(6), carta(4)]);
    expect(veintiocho.juego).toBe(null);
    expect(veintiocho.punto).toBe(28);
    expect(veintisiete.punto).toBe(27);
    expect(comparar(veintiocho, veintisiete, 'juego')).toBeGreaterThan(0);
  });
});

describe('Mus · el mus', () => {
  it('se corta una sola vez: en cuanto uno corta, se cierra para todos', () => {
    const s = decirMus(partida(), 0); // habla el mano
    const cortada = cortarMus(s, 1);
    expect(cortada.phase).toBe('lances');
    expect(cortada.lance).toBe('grande');
    // Los que no habían hablado ya no pueden pedir mus.
    expect(() => decirMus(cortada, 2)).toThrow(/ya no se puede pedir mus/);
  });

  it('si todos piden mus, se pasa al descarte', () => {
    let s = partida();
    for (const seat of [0, 1, 2, 3]) s = decirMus(s, seat);
    expect(s.phase).toBe('descartar');
  });

  it('se habla por turno, empezando por el mano', () => {
    const s = partida();
    expect(() => decirMus(s, 2)).toThrow(/ahora no te toca/);
    const suyo = decirMus(s, 0);
    // Y el que ya ha hablado no vuelve a hablar (ahora le toca al siguiente).
    expect(() => decirMus(suyo, 0)).toThrow(/ahora no te toca/);
  });

  it('se descartan cartas y se vuelve a la fase de mus', () => {
    let s = partida();
    for (const seat of [0, 1, 2, 3]) s = decirMus(s, seat);
    const antes = s.players[0].hand.map((c) => c.id);
    const cambiadas = descartar(s, 0, [antes[0], antes[1]], rng(9));
    expect(cambiadas.players[0].hand).toHaveLength(4);
    expect(cambiadas.players[0].hand.map((c) => c.id)).not.toContain(antes[0]);
    expect(cambiadas.events.at(-1)).toMatchObject({ kind: 'descartar', cuantas: 2 });
  });
});

describe('Mus · los envites', () => {
  it('quien responde un envite es siempre de la pareja contraria', () => {
    // Habla el mano, y luego el siguiente: en los dos casos responde un contrario.
    const s0 = envidar(mesa(manosBase()), 0, 2);
    expect(parejaDe(s0.responde!)).not.toBe(parejaDe(0));

    const trasPasar = pasar(mesa(manosBase()), 0);
    const s1 = envidar(trasPasar, 1, 2);
    expect(parejaDe(s1.responde!)).not.toBe(parejaDe(1));
  });

  it('el envite mínimo son dos piedras', () => {
    expect(() => envidar(mesa(manosBase()), 0, 1)).toThrow(/mínimo son dos/);
  });

  it('no querer un envite le da una piedra a quien lo hizo', () => {
    const s = noQuiero(envidar(mesa(manosBase()), 0, 2), 1);
    expect(s.teams[0].piedras).toBe(1);
    expect(s.envite).toBe(null);
    expect(s.events.at(-1)).toMatchObject({ kind: 'lance', team: 0, piedras: 1 });
  });

  it('querer un envite resuelve el lance con las piedras apostadas', () => {
    // La pareja 0 con los dos reyes (duples), la pareja 1 con nada.
    const s = mesa([
      [carta(12, 'o', 0), carta(12, 'c', 0), carta(7), carta(4)],
      [carta(6), carta(5), carta(4, 'c'), carta(1)],
      [carta(12, 'e', 0), carta(12, 'b', 0), carta(6, 'c'), carta(5, 'c')],
      [carta(7, 'c'), carta(6, 'e'), carta(5, 'e'), carta(1, 'c')],
    ]);
    const resuelto = quiero(envidar(s, 0, 2), 1);
    // Grande (2 por ganarla) + las 2 apostadas.
    expect(resuelto.teams[0].piedras).toBe(4);
    expect(resuelto.events.some((e) => e.kind === 'lance' && e.piedras === 4)).toBe(true);
  });

  it('no se puede envidar dos veces seguidas sin resolver el envite', () => {
    const s = envidar(mesa(manosBase()), 0, 2);
    // Con un envite vivo, al que le toca es al que tiene que responder.
    expect(() => envidar(s, s.responde!, 3)).toThrow(/envite sin resolver/);
  });

  it('el órdago también lo responde un contrario', () => {
    const s = ordago(mesa(manosBase()), 0);
    expect(s.envite?.ordago).toBe(true);
    expect(parejaDe(s.responde!)).not.toBe(parejaDe(0));
  });
});

describe('Mus · los cuatro lances y el tanteo', () => {
  it('los lances van en orden: grande, chica, pares y juego', () => {
    expect(LANCES).toEqual(['grande', 'chica', 'pares', 'juego']);
  });

  it('pasando los cuatro se resuelve el lance y se pasa al siguiente', () => {
    const s = mesa([
      [carta(12), carta(7), carta(4), carta(1)],
      [carta(11), carta(6), carta(5), carta(2)],
      [carta(10), carta(7, 'c'), carta(4, 'c'), carta(1, 'c')],
      [carta(7, 'e'), carta(6, 'e'), carta(5, 'e'), carta(2, 'e')],
    ]);
    let t = s;
    for (const seat of [0, 1, 2, 3]) t = pasar(t, seat);
    expect(t.lance).toBe('chica');
    expect(t.teams[0].piedras).toBe(2); // la pareja 0 tiene el rey: gana la grande
  });

  it('en pares, unas duples valen 3 piedras, unas medias 2 y una pareja 1', () => {
    const base = [
      [carta(12), carta(7), carta(4), carta(1)],
      [carta(11), carta(6), carta(5), carta(2)],
      [carta(10), carta(7, 'c'), carta(4, 'c'), carta(1, 'c')],
      [carta(7, 'e'), carta(6, 'e'), carta(5, 'e'), carta(2, 'e')],
    ];
    const conPares = (mano0: Card[]) => {
      const s = mesa([mano0, ...base.slice(1)]);
      s.lance = 'pares';
      let t = s;
      for (const seat of [0, 1, 2, 3]) t = pasar(t, seat);
      return t.teams[0].piedras;
    };
    expect(conPares([carta(12), carta(12, 'c'), carta(7), carta(7, 'c')])).toBe(3); // duples
    expect(conPares([carta(12), carta(12, 'c'), carta(12, 'e'), carta(12, 'b')])).toBe(3); // póker = duples
    expect(conPares([carta(12), carta(12, 'c'), carta(12, 'e'), carta(4)])).toBe(2); // medias
    expect(conPares([carta(12), carta(12, 'c'), carta(7), carta(4)])).toBe(1); // pareja
  });

  it('en juego, un 31 vale 3 piedras y otro juego 2', () => {
    const conJuego = (mano0: Card[]) => {
      const s = mesa([
        mano0,
        [carta(7, 'c'), carta(6, 'c'), carta(5, 'c'), carta(4, 'c')],
        [carta(7, 'e'), carta(6, 'e'), carta(5, 'e'), carta(4, 'e')],
        [carta(7, 'b'), carta(6, 'b'), carta(5, 'b'), carta(4, 'b')],
      ]);
      s.lance = 'juego';
      let t = s;
      for (const seat of [0, 1, 2, 3]) t = pasar(t, seat);
      return t.teams[0].piedras;
    };
    expect(conJuego([carta(12), carta(11), carta(10), carta(1)])).toBe(3); // 31 = la una
    expect(conJuego([carta(3), carta(10), carta(12), carta(11)])).toBe(2); // 33
  });

  it('llegar a 40 piedras a mitad del recuento termina el juego', () => {
    const s = mesa([
      [carta(12), carta(12, 'c'), carta(7), carta(7, 'c')],
      [carta(6), carta(5), carta(4), carta(1)],
      [carta(12, 'e'), carta(12, 'b'), carta(6, 'c'), carta(5, 'c')],
      [carta(7, 'e'), carta(6, 'e'), carta(5, 'e'), carta(1, 'c')],
    ]);
    s.teams[0].piedras = PIEDRAS_PARA_GANAR - 2; // gana la grande: 2 piedras justas para 40
    let t = s;
    for (const seat of [0, 1, 2, 3]) t = pasar(t, seat);
    expect(t.teams[0].piedras).toBeGreaterThanOrEqual(PIEDRAS_PARA_GANAR);
    expect(t.teams[0].juegos).toBe(1);
    expect(t.phase).toBe('game-end');
  });

  it('la mano siguiente conserva piedras y juegos', () => {
    const s = partida();
    s.teams[0].piedras = 12;
    s.teams[1].juegos = 1;
    const nueva = nextHand(s, rng(3));
    expect(nueva.teams[0].piedras).toBe(12);
    expect(nueva.teams[1].juegos).toBe(1);
    expect(nueva.phase).toBe('mus');
  });
});

describe('Mus · el bot y la partida entera', () => {
  it('el bot pide mus con una mano mala y corta con una buena', () => {
    const mala = mesa([
      [carta(7), carta(6), carta(5), carta(4)],
      [carta(7, 'c'), carta(6, 'c'), carta(5, 'c'), carta(4, 'c')],
      [carta(7, 'e'), carta(6, 'e'), carta(5, 'e'), carta(4, 'e')],
      [carta(7, 'b'), carta(6, 'b'), carta(5, 'b'), carta(4, 'b')],
    ]);
    mala.phase = 'mus';
    mala.mano = 0;
    expect(botDecision(mala, 0)).toEqual({ action: 'mus' });

    const buena = mesa([
      [carta(12), carta(12, 'c'), carta(12, 'e'), carta(7)],
      [carta(7, 'c'), carta(6, 'c'), carta(5, 'c'), carta(4, 'c')],
      [carta(7, 'e'), carta(6, 'e'), carta(5, 'e'), carta(4, 'e')],
      [carta(7, 'b'), carta(6, 'b'), carta(5, 'b'), carta(4, 'b')],
    ]);
    buena.phase = 'mus';
    buena.mano = 0;
    expect(botDecision(buena, 0)).toEqual({ action: 'cortar' });
  });

  it('una partida entera entre cuatro bots termina', () => {
    let s = newGame({ names: ['A', 'B', 'C', 'D'], bots: [true, true, true, true], rng: rng(11) });
    let vueltas = 0;
    while (s.phase !== 'vaca-end' && vueltas < 4000) {
      vueltas++;
      const seat = turnoActual(s);
      if (seat === null) {
        s = nextHand(s, rng(vueltas));
        continue;
      }
      const d = botDecision(s, seat);
      if (!d) {
        s = nextHand(s, rng(vueltas));
        continue;
      }
      if (d.action === 'mus') s = decirMus(s, seat);
      else if (d.action === 'cortar') s = cortarMus(s, seat);
      else if (d.action === 'descartar') s = descartar(s, seat, d.cardIds, rng(vueltas));
      else if (d.action === 'pasar') s = pasar(s, seat);
      else if (d.action === 'envidar') s = envidar(s, seat, d.cuantas);
      else if (d.action === 'ordago') s = ordago(s, seat);
      else if (d.action === 'quiero') s = quiero(s, seat);
      else if (d.action === 'no_quiero') s = noQuiero(s, seat);
    }
    expect(s.phase).toBe('vaca-end');
    expect(vueltas).toBeLessThan(4000);
    // Alguien ha ganado la vaca con tres juegos.
    expect(Math.max(s.teams[0].juegos, s.teams[1].juegos)).toBe(3);
  });
});

describe('Mus · lo que ve cada uno', () => {
  it('cada uno ve su mano y la de su compañero, pero no la de los rivales', () => {
    const s = partida();
    const vista = viewFor(s, 0);
    expect(vista.myHand).toHaveLength(4);
    expect(vista.companero?.id).toBe(2); // el 0 y el 2 son pareja
    expect(vista.players[1]).not.toHaveProperty('hand');
    expect(vista.players[1]).not.toHaveProperty('jugada');
  });

  it('las parejas son 0 y 2 contra 1 y 3', () => {
    expect(parejaDe(0)).toBe(parejaDe(2));
    expect(parejaDe(1)).toBe(parejaDe(3));
    expect(parejaDe(0)).not.toBe(parejaDe(1));
    expect(JUGADORES).toBe(4);
  });
});
