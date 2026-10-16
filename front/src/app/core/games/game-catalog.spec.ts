import { routes } from '../../app.routes';
import { AVAILABLE_GAMES, GAME_CATALOG, UPCOMING_GAMES, modeKey } from './game-catalog';

/**
 * Catálogo de juegos.
 *
 * Este fichero es la única declaración de un juego, así que si se rompe, el apartado
 * «Juegos» enseña algo que no existe: un botón que lleva a ninguna parte o un juego
 * repetido. Los tests comprueban justo eso.
 */
describe('catálogo de juegos', () => {
  const rutasDeclaradas = routes.map((r) => `/${r.path ?? ''}`);

  it('no repite identificadores', () => {
    const ids = GAME_CATALOG.map((j) => j.id);
    expect(new Set(ids).size).toBe(ids.length);
  });

  it('cada juego apunta a una ruta que existe de verdad', () => {
    for (const juego of GAME_CATALOG) {
      expect(rutasDeclaradas, `${juego.id} apunta a ${juego.route}`).toContain(juego.route);
    }
  });

  it('cada juego tiene icono, modo y etiquetas', () => {
    for (const juego of GAME_CATALOG) {
      expect(juego.icon, `${juego.id} sin icono`).toBeTruthy();
      expect(juego.tags.length, `${juego.id} sin etiquetas`).toBeGreaterThan(0);
      expect(['local', 'bots', 'online']).toContain(juego.mode);
    }
  });

  it('los jugables llevan a un juego y los anunciados no', () => {
    expect(AVAILABLE_GAMES.length).toBeGreaterThan(0);
    expect(AVAILABLE_GAMES.length + UPCOMING_GAMES.length).toBe(GAME_CATALOG.length);
    // Un juego anunciado no debe llevar a una pantalla sin terminar.
    for (const juego of UPCOMING_GAMES) {
      expect(juego.available).toBe(false);
    }
  });

  it('el modo se traduce con una clave', () => {
    expect(modeKey('online')).toBe('games.mode.online');
    expect(modeKey('local')).toBe('games.mode.local');
    expect(modeKey('bots')).toBe('games.mode.bots');
  });
});
