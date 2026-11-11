import { expect, test } from '@playwright/test';

/**
 * Ninguna baraja puede quedarse con una carta sin arte.
 *
 * El fallo sería silencioso: una imagen que no existe no rompe nada, solo deja un hueco en blanco en
 * la mesa. Aquí se piden las 92 cartas (40 españolas + 52 francesas) y el dorso de cada baraja.
 */
const ESPANOLA = {
  carpeta: 'cards/es8bit',
  rangos: ['1', '2', '3', '4', '5', '6', '7', '10', '11', '12'],
  palos: ['o', 'c', 'e', 'b'],
};

const FRANCESA = {
  carpeta: 'cards/8bit',
  rangos: ['A', '2', '3', '4', '5', '6', '7', '8', '9', 'T', 'J', 'Q', 'K'],
  palos: ['c', 'd', 'h', 's'],
};

for (const [nombre, baraja] of [
  ['española', ESPANOLA],
  ['francesa', FRANCESA],
] as const) {
  test(`la baraja ${nombre} tiene todas sus cartas`, async ({ request }) => {
    const codigos: string[] = [];
    for (const rango of baraja.rangos) {
      for (const palo of baraja.palos) codigos.push(`${rango}${palo}`);
    }
    expect(codigos.length).toBe(baraja.rangos.length * baraja.palos.length);

    const fallos: string[] = [];
    for (const codigo of codigos) {
      const respuesta = await request.get(`/${baraja.carpeta}/${codigo}.webp`);
      if (respuesta.status() !== 200) fallos.push(`${codigo} (${respuesta.status()})`);
    }
    expect(fallos, `cartas sin arte en la baraja ${nombre}`).toEqual([]);

    const dorso = await request.get(`/${baraja.carpeta}/back.webp`);
    expect(dorso.status(), `falta el dorso de la baraja ${nombre}`).toBe(200);
  });
}
