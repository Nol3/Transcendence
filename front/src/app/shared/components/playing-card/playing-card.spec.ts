import { TestBed } from '@angular/core/testing';

import { PlayingCard } from './playing-card';

/**
 * Cartas de la baraja (los PNG del mazo 8-bit del proyecto).
 *
 * Lo que se prueba aquí es el **mapeo**: que un código del motor ("As", "7c", "Td")
 * acabe en el PNG correcto y con un nombre accesible. Un fallo en esto enseña una
 * carta distinta a la que el motor tiene en la mano.
 */
describe('PlayingCard', () => {
  function montar(card: string, faceDown = false) {
    const fixture = TestBed.createComponent(PlayingCard);
    fixture.componentRef.setInput('card', card);
    fixture.componentRef.setInput('faceDown', faceDown);
    fixture.detectChanges();
    return fixture.componentInstance;
  }

  it('resuelve el PNG por el código de la carta', () => {
    expect(montar('As').src()).toBe('cards/As.png');
    expect(montar('7c').src()).toBe('cards/7c.png');
    expect(montar('Td').src()).toBe('cards/Td.png');
    expect(montar('Kh').src()).toBe('cards/Kh.png');
  });

  it('enseña el dorso cuando la carta está boca abajo', () => {
    const c = montar('As', true);
    expect(c.src()).toBe('cards/back.png');
  });

  it('acepta las 52 cartas de la baraja', () => {
    const rangos = ['2', '3', '4', '5', '6', '7', '8', '9', 'T', 'J', 'Q', 'K', 'A'];
    const palos = ['c', 'd', 'h', 's'];
    const codigos = rangos.flatMap((r) => palos.map((p) => r + p));
    expect(codigos.length).toBe(52);
    for (const codigo of codigos) {
      // El segundo argumento de expect es el mensaje: en vitest se pasa así.
      expect(montar(codigo).esValida(), `debería reconocer ${codigo}`).toBe(true);
    }
  });

  it('no se inventa una carta con un código que no existe', () => {
    // Código inválido: en vez de pedir un PNG que no está, cae al dorso.
    for (const malo of ['', 'X', 'Zz', '10c', 'Az', '1h']) {
      const c = montar(malo);
      expect(c.esValida(), `"${malo}" no es una carta`).toBe(false);
      expect(c.src()).toBe('cards/back.png');
    }
  });

  it('compone el nombre accesible a partir del rango y el palo', () => {
    const c = montar('As');
    expect(c.rango()).toBe('A');
    expect(c.palo()).toBe('s');
  });

  it('normaliza mayúsculas y minúsculas del código', () => {
    const c = montar('aS');
    expect(c.esValida()).toBe(true);
    expect(c.rango()).toBe('A');
    expect(c.palo()).toBe('s');
  });
});
