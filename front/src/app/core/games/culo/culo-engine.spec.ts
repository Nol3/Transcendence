/**
 * Reglas del Culo.
 *
 * Estas pruebas son el sitio donde vive el juego: si el motor se equivoca aquí, la mesa
 * enseña jugadas que no se pueden hacer. Se prueban los valores de las cartas, las
 * respuestas válidas, el cierre de baza, el reparto de roles y el intercambio entre
 * rondas, y al final una partida entera jugada por bots para comprobar que siempre
 * termina y que nunca se pierde ni se inventa una carta.
 */
import { Card, SpanishRank, SpanishSuit, buildDeck, strength } from './culo-deck';
import {
  GameState,
  applySwaps,
  assignRoles,
  canBeat,
  canPlay,
  comboOf,
  exchangeSwaps,
  legalCombos,
  newGame,
  nextRound,
  nextRoundWithSwaps,
  pass,
  play,
  standings,
} from './culo-engine';
import { botDecision } from './culo-bots';

function carta(rank: SpanishRank, suit: SpanishSuit, copy = 0): Card {
  return { id: `${rank}${suit}-${copy}`, suit, rank, copy };
}

function estado(
  manos: { name: string; cards: Card[]; isBot?: boolean; place?: number | null }[],
  turn = 0,
): GameState {
  return {
    players: manos.map((m, i) => ({
      id: i,
      name: m.name,
      isBot: m.isBot ?? false,
      hand: m.cards,
      role: null,
      place: m.place ?? null,
    })),
    turn,
    table: null,
    passed: [],
    round: 1,
    decks: 1,
    events: [],
    phase: 'playing',
  };
}

describe('valor de las cartas', () => {
  it('ordena de menor a mayor como manda el juego', () => {
    const orden = [2, 3, 4, 5, 6, 7, 10, 11, 12, 1] as SpanishRank[];
    const fuerzas = orden.map((r) => strength(carta(r, 'c')));
    expect(fuerzas).toEqual([...fuerzas].sort((a, b) => a - b));
    expect(new Set(fuerzas).size).toBe(fuerzas.length);
  });

  it('el 5 de oros es la carta más alta', () => {
    const cincoOros = carta(5, 'o');
    expect(strength(cincoOros)).toBeGreaterThan(strength(carta(1, 'e'))); // por encima del As
    for (const suit of ['c', 'e', 'b'] as SpanishSuit[]) {
      expect(strength(cincoOros)).toBeGreaterThan(strength(carta(12, suit)));
    }
  });

  it('el 5 de oros no vale lo mismo que los otros cincos', () => {
    expect(strength(carta(5, 'o'))).not.toBe(strength(carta(5, 'c')));
  });
});

describe('jugadas', () => {
  it('son del mismo valor o no son jugada', () => {
    expect(comboOf([carta(3, 'o'), carta(3, 'c')])).not.toBeNull();
    expect(comboOf([carta(3, 'o'), carta(4, 'c')])).toBeNull();
    expect(comboOf([])).toBeNull();
  });

  it('el 5 de oros no se puede jugar junto a otro 5', () => {
    expect(comboOf([carta(5, 'o'), carta(5, 'c')])).toBeNull();
  });

  it('con dos barajas, dos cartas iguales sí son pareja', () => {
    expect(comboOf([carta(7, 'e', 0), carta(7, 'e', 1)])).not.toBeNull();
  });
});

describe('responder a la mesa', () => {
  const mesa = { cards: [carta(5, 'c')], by: 0, strength: 5, count: 1 };

  it('sin nada en la mesa, cualquier jugada vale', () => {
    expect(canBeat(comboOf([carta(2, 'o')])!, null)).toBe(true);
  });

  it('hay que igualar la cantidad exacta', () => {
    const dosCartas = comboOf([carta(6, 'o'), carta(6, 'c')])!;
    expect(canBeat(dosCartas, mesa)).toBe(false); // dos cartas contra una
    const unaCarta = comboOf([carta(6, 'o')])!;
    expect(canBeat(unaCarta, mesa)).toBe(true);
  });

  it('hay que superar el valor', () => {
    expect(canBeat(comboOf([carta(4, 'o')])!, mesa)).toBe(false);
    expect(canBeat(comboOf([carta(5, 'e')])!, mesa)).toBe(false); // igual no basta
    expect(canBeat(comboOf([carta(6, 'o')])!, mesa)).toBe(true);
  });

  it('las jugadas legales respetan cantidad y valor', () => {
    const s = estado([{ name: 'ana', cards: [carta(6, 'o'), carta(6, 'c'), carta(11, 'o')] }]);
    s.table = mesa; // una carta de valor 5

    const jugadas = legalCombos(s, 0);
    // En la mesa hay UNA carta, así que la respuesta es UNA carta: la pareja de seises no
    // vale aunque sea más alta. Y el 6 sí vale porque supera el 5.
    expect(jugadas.map((j) => j.cards.length)).toEqual([1, 1]);
    // Ojo: la fuerza no es el nombre del rango. El Caballo (11) tiene fuerza 9.
    expect(jugadas.map((j) => j.strength).sort()).toEqual([6, 9]);
  });

  it('con dos cartas en la mesa, la respuesta tiene que ser de dos', () => {
    const s = estado([
      { name: 'ana', cards: [carta(6, 'o'), carta(6, 'c'), carta(11, 'o')] },
    ]);
    s.table = { cards: [carta(4, 'o'), carta(4, 'c')], by: 1, strength: 4, count: 2 };

    const jugadas = legalCombos(s, 0);
    // La pareja de seises vale; el Caballo solo no, porque son dos cartas.
    expect(jugadas).toHaveLength(1);
    expect(jugadas[0].cards.map((c) => c.id).sort()).toEqual(['6c-0', '6o-0']);
  });

  it('abriendo se puede jugar cualquier cantidad de un valor', () => {
    const s = estado([{ name: 'ana', cards: [carta(6, 'o'), carta(6, 'c'), carta(6, 'e')] }]);
    const jugadas = legalCombos(s, 0);
    expect(jugadas.map((j) => j.cards.length).sort()).toEqual([1, 2, 3]);
  });
});

describe('turnos y bazas', () => {
  it('jugar quita las cartas de la mano y las pone en la mesa', () => {
    const s = estado([
      { name: 'ana', cards: [carta(3, 'o'), carta(7, 'c')] },
      { name: 'luis', cards: [carta(11, 'o')] },
    ]);
    const despues = play(s, 0, [carta(3, 'o')]);
    expect(despues.players[0].hand.map((c) => c.id)).toEqual(['7c-0']);
    expect(despues.table?.cards.map((c) => c.id)).toEqual(['3o-0']);
    expect(despues.turn).toBe(1);
  });

  it('no deja jugar la misma carta dos veces', () => {
    // Sin esta comprobación, mandar el mismo id dos veces colaba como «pareja» y te
    // descartabas de una sola carta.
    const s = estado([
      { name: 'ana', cards: [carta(3, 'o'), carta(7, 'c')] },
      { name: 'luis', cards: [carta(11, 'o')] },
    ]);
    const gemela = carta(3, 'o');
    expect(canPlay(s, 0, [gemela, gemela])).toBe(false);
    expect(play(s, 0, [gemela, gemela]).players[0].hand).toHaveLength(2);
  });

  it('no deja jugar fuera de turno ni con cartas que no son tuyas', () => {
    const s = estado([
      { name: 'ana', cards: [carta(3, 'o')] },
      { name: 'luis', cards: [carta(11, 'o')] },
    ]);
    expect(canPlay(s, 1, [carta(11, 'o')])).toBe(false); // no es su turno
    expect(canPlay(s, 0, [carta(11, 'o')])).toBe(false); // esa carta no es suya
  });

  it('quien pasa no vuelve a entrar en la misma baza', () => {
    const s = estado([
      { name: 'ana', cards: [carta(3, 'o'), carta(10, 'o')] },
      { name: 'luis', cards: [carta(4, 'o'), carta(11, 'o')] },
      { name: 'eva', cards: [carta(5, 'o'), carta(10, 'o')] },
    ]);
    let g = play(s, 0, [carta(3, 'o')]); // ana abre
    g = pass(g, 1); // luis pasa
    g = play(g, 2, [carta(5, 'o')]); // eva sube
    expect(g.turn).toBe(0); // vuelve a ana: luis queda fuera de la baza
    expect(g.passed).toContain(1);
  });

  it('la baza se cierra cuando todos los demás pasan y abre el último que jugó', () => {
    const s = estado([
      { name: 'ana', cards: [carta(3, 'o'), carta(10, 'o')] },
      { name: 'luis', cards: [carta(4, 'o')] },
    ]);
    let g = play(s, 0, [carta(3, 'o')]);
    g = pass(g, 1);
    expect(g.table).toBeNull(); // se recogen las cartas
    expect(g.turn).toBe(0); // y abre otra vez quien la ganó
    expect(g.passed).toEqual([]);
  });
});

describe('final de ronda y roles', () => {
  it('quedarse sin cartas da puesto', () => {
    const s = estado([
      { name: 'ana', cards: [carta(3, 'o')] },
      { name: 'luis', cards: [carta(11, 'o')] },
    ]);
    const g = play(s, 0, [carta(3, 'o')]);
    expect(g.players[0].place).toBe(1);
  });

  it('la ronda termina cuando solo queda uno con cartas', () => {
    const s = estado([
      { name: 'ana', cards: [carta(3, 'o')], place: null },
      { name: 'luis', cards: [carta(11, 'o')], place: null },
      { name: 'eva', cards: [], place: 1 },
    ]);
    const g = play(s, 0, [carta(3, 'o')]);
    expect(g.phase).toBe('round-end');
    expect(g.players[1].place).toBe(3); // el que se quedó con cartas es el último
  });

  it('con 3 jugadores hay Presidente, un neutro y Culo (sin vices)', () => {
    const s = estado([
      { name: 'ana', cards: [], place: 1 },
      { name: 'luis', cards: [], place: 2 },
      { name: 'eva', cards: [], place: 3 },
    ]);
    const g = assignRoles(s);
    expect(g.players.map((p) => p.role)).toEqual(['presidente', 'neutro', 'culo']);
  });

  it('con 4 o más hay vicepresidente y viceculo', () => {
    const s = estado([
      { name: 'ana', cards: [], place: 1 },
      { name: 'luis', cards: [], place: 2 },
      { name: 'eva', cards: [], place: 3 },
      { name: 'paz', cards: [], place: 4 },
    ]);
    const g = assignRoles(s);
    expect(g.players.map((p) => p.role)).toEqual([
      'presidente',
      'vicepresidente',
      'viceculo',
      'culo',
    ]);
    expect(standings(g).map((p) => p.name)).toEqual(['ana', 'luis', 'eva', 'paz']);
  });
});

describe('intercambio entre rondas', () => {
  const reparto = () =>
    estado([
      { name: 'ana', cards: [carta(2, 'o'), carta(3, 'c')] }, // será el culo
      { name: 'luis', cards: [carta(12, 'o'), carta(1, 'e')] }, // presidente
      { name: 'eva', cards: [carta(4, 'o'), carta(5, 'c')] },
      { name: 'paz', cards: [carta(6, 'o'), carta(7, 'c')] },
    ]);

  function conRoles(): GameState {
    const s = reparto();
    s.players[0].role = 'culo';
    s.players[1].role = 'presidente';
    s.players[2].role = 'viceculo';
    s.players[3].role = 'vicepresidente';
    return s;
  }

  it('el Culo da sus 2 mejores y el Presidente sus 2 peores', () => {
    const swaps = exchangeSwaps(conRoles());
    const culoAlPresidente = swaps.find((s) => s.from === 0 && s.to === 1)!;
    const presidenteAlCulo = swaps.find((s) => s.from === 1 && s.to === 0)!;
    expect(culoAlPresidente.cards.map((c) => c.id).sort()).toEqual(['2o-0', '3c-0']);
    expect(presidenteAlCulo.cards.map((c) => c.id).sort()).toEqual(['12o-0', '1e-0']);
  });

  it('el Viceculo da su mejor al Vicepresidente, que devuelve su peor', () => {
    const swaps = exchangeSwaps(conRoles());
    const viceculoAlVice = swaps.find((s) => s.from === 2 && s.to === 3)!;
    const viceAlViceculo = swaps.find((s) => s.from === 3 && s.to === 2)!;
    expect(viceculoAlVice.cards).toHaveLength(1);
    expect(viceAlViceculo.cards).toHaveLength(1);
  });

  it('el intercambio mueve las cartas de verdad', () => {
    const g = applySwaps(conRoles(), exchangeSwaps(conRoles()));
    // El presidente se queda con las dos mejores del culo…
    expect(g.players[1].hand.map((c) => c.id)).toEqual(
      expect.arrayContaining(['2o-0', '3c-0']),
    );
    // …y el culo con las dos peores del presidente.
    expect(g.players[0].hand.map((c) => c.id)).toEqual(
      expect.arrayContaining(['12o-0', '1e-0']),
    );
  });
});

describe('partida completa con bots', () => {
  it('siempre termina y no pierde ni inventa cartas', () => {
    for (let partida = 0; partida < 60; partida++) {
      const n = 3 + (partida % 4); // de 3 a 6 jugadores
      const decks = partida % 2 === 0 ? 1 : 2;
      let g = newGame({
        names: Array.from({ length: n }, (_, i) => `j${i}`),
        bots: Array.from({ length: n }, () => true),
        decks: decks as 1 | 2,
        rng: () => (partida + 1) / 97, // determinista: un reparto distinto por partida
      });

      const total = buildDeck(decks as 1 | 2).length;
      let vueltas = 0;
      while (g.phase === 'playing' && vueltas < 5000) {
        const turno = g.turn;
        const decision = botDecision(g, turno, () => 0.9);
        g = decision ? play(g, turno, decision.cards) : pass(g, turno);
        vueltas++;

        // Ninguna carta puede estar en dos manos ni duplicarse.
        const ids = g.players.flatMap((p) => p.hand.map((c) => c.id));
        expect(new Set(ids).size, 'carta duplicada').toBe(ids.length);
        expect(ids.length, 'más cartas que la baraja').toBeLessThanOrEqual(total);
      }

      expect(vueltas, 'la partida no terminó').toBeLessThan(5000);
      expect(g.phase).toBe('round-end');

      const roles = g.players.map((p) => p.role);
      expect(roles.filter((r) => r === 'presidente')).toHaveLength(1);
      expect(roles.filter((r) => r === 'culo')).toHaveLength(1);
      // Todos tienen puesto y los puestos no se repiten.
      const puestos = g.players.map((p) => p.place).sort();
      expect(puestos).toEqual(Array.from({ length: n }, (_, i) => i + 1));
    }
  });

  it('la ronda siguiente la abre el Presidente y las cartas vuelven a repartirse', () => {
    const g = nextRound(
      assignRoles(
        estado([
          { name: 'ana', cards: [], place: 1 },
          { name: 'luis', cards: [], place: 2 },
          { name: 'eva', cards: [], place: 3 },
        ]),
      ),
    );
    expect(g.turn).toBe(0); // ana es la presidenta
    expect(g.round).toBe(2);
    expect(g.phase).toBe('playing');
    expect(g.players.every((p) => p.hand.length > 0)).toBe(true);
    expect(g.players.every((p) => p.place === null)).toBe(true);
  });

  it('reparte y DESPUÉS intercambia: si no, el intercambio del Culo no ocurre', () => {
    // El fallo que fija este test: calcular los intercambios sobre la mano vieja y repartir
    // después. El reparto se llevaba por delante las cartas intercambiadas y la regla del
    // Culo (el Presidente le quita las mejores al Culo) se quedaba en nada. Como las dos
    // funciones por separado están bien, solo se ve componiéndolas.
    const base = assignRoles(
      estado([
        { name: 'ana', cards: [], place: 1 },
        { name: 'luis', cards: [], place: 2 },
        { name: 'eva', cards: [], place: 3 },
      ]),
    );
    const fijo = () => 0.5; // misma semilla: las dos formas reparten lo mismo

    const soloRepartida = nextRound(base, fijo);
    const conIntercambio = nextRoundWithSwaps(base, fijo);

    const ids = (g: typeof base) => g.players.map((p) => p.hand.map((c) => c.id).sort());
    expect(ids(conIntercambio)).not.toEqual(ids(soloRepartida));

    // Y sin perder cartas por el camino.
    const cuenta = (g: typeof base) => g.players.reduce((n, p) => n + p.hand.length, 0);
    expect(cuenta(conIntercambio)).toBe(cuenta(soloRepartida));
  });
});
