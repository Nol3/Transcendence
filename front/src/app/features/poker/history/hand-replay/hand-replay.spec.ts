import { TestBed } from '@angular/core/testing';

import { PokerHandReplay } from '../../../../core/services/poker-history.service';
import { HandReplay } from './hand-replay';

/**
 * Replay de manos (roadmap 7.2).
 *
 * Lo que se prueba es la **reconstrucción**: el componente no guarda estado del juego,
 * deduce tablero, bote y retirados recorriendo el registro de acciones hasta el paso
 * actual. Si eso falla, el replay enseña una partida que no pasó.
 */
const MANO: PokerHandReplay = {
  id: 7,
  hand_number: 3,
  board: '7c 2s Ad 9d',
  pot: 300,
  showdown: false,
  winner_names: 'ana',
  created_at: '2026-10-13T10:00:00Z',
  players: [
    { seat: 0, name: 'ana', is_bot: false, hole: 'Ah Kh', hand_name: 'Pareja', stack_after: 1100, won: 300, folded: false },
    { seat: 1, name: 'Bot Test', is_bot: true, hole: '', hand_name: '', stack_after: 900, won: 0, folded: true },
  ],
  actions: [
    { event: 'hand_start', button: 0, sb: 10, bb: 20, stacks: [1000, 1000] },
    { event: 'blind', seat: 0, kind: 'small', amount: 10 },
    { event: 'blind', seat: 1, kind: 'big', amount: 20 },
    { event: 'action', seat: 0, action: 'raise', amount: 60, committed: 60, street: 'preflop' },
    { event: 'action', seat: 1, action: 'fold', amount: 0, committed: 20, street: 'preflop' },
    { event: 'uncalled_return', seat: 0, amount: 40 },
    { event: 'hand_end', winner: 0, amount: 90, showdown: false },
  ],
};

describe('HandReplay', () => {
  function montar(mano: PokerHandReplay = MANO) {
    const fixture = TestBed.createComponent(HandReplay);
    fixture.componentRef.setInput('hand', mano);
    fixture.detectChanges();
    return fixture.componentInstance;
  }

  it('empieza en el primer paso', () => {
    const c = montar();
    expect(c.actual()).toBe(0);
    expect(c.total()).toBe(7);
  });

  it('no enseña cartas comunitarias antes del flop', () => {
    const c = montar();
    c.siguiente();
    c.siguiente();
    expect(c.vista().board).toEqual([]);
    expect(c.vista().calle).toBe('preflop');
  });

  it('acumula el bote con ciegas y apuestas', () => {
    const c = montar();
    c.siguiente();          // ciega pequeña
    c.siguiente();          // ciega grande
    expect(c.vista().bote).toBe(30);
    c.siguiente();          // sube a 60
    expect(c.vista().bote).toBe(90);
  });

  it('devuelve lo no igualado (el bote no se infla)', () => {
    const c = montar();
    c.ultimo();
    // 10 + 20 + 60 - 40 devueltos = 50
    expect(c.vista().bote).toBe(50);
  });

  it('marca a quien se retira', () => {
    const c = montar();
    c.siguiente();
    c.siguiente();
    c.siguiente();
    expect(c.vista().retirados.has(1)).toBe(false);
    c.siguiente();          // el bot se retira
    expect(c.vista().retirados.has(1)).toBe(true);
  });

  it('dice a quién le tocaba actuar', () => {
    const c = montar();
    c.siguiente();
    c.siguiente();
    c.siguiente();          // ana sube
    expect(c.vista().turno).toBe(0);
    c.siguiente();          // el bot se retira
    expect(c.vista().turno).toBe(1);
  });

  it('el registro va creciendo con los pasos', () => {
    const c = montar();
    const alPrincipio = c.vista().lineas.length;
    c.siguiente();
    c.siguiente();
    expect(c.vista().lineas.length).toBeGreaterThan(alPrincipio);
  });

  it('no se sale del último paso', () => {
    const c = montar();
    c.ultimo();
    c.siguiente();
    expect(c.actual()).toBe(6);
    c.primero();
    c.anterior();
    expect(c.actual()).toBe(0);
  });

  it('una mano sin registro lo dice en vez de romperse', () => {
    const c = montar({ ...MANO, actions: [] });
    expect(c.total()).toBe(0);
    expect(c.vista().lineas).toEqual([]);
    expect(c.vista().board).toEqual([]);
  });

  it('avisa al cerrarse', () => {
    const c = montar();
    let cerrado = false;
    c.closed.subscribe(() => (cerrado = true));
    c.cerrar();
    expect(cerrado).toBe(true);
  });
});
