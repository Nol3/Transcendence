/**
 * Catálogo de juegos de la plataforma.
 *
 * Este fichero es **el único sitio donde se declara un juego**: de aquí salen la lista
 * del apartado «Juegos», sus etiquetas y a dónde lleva su botón. Añadir uno nuevo es
 * añadir una entrada aquí y su ruta en `app.routes.ts` (ver `docs/JUEGOS.md`).
 *
 * Los textos no van aquí: cada juego tiene su clave de traducción (`game.<id>.name`,
 * `game.<id>.desc`, `game.<id>.how`) en los tres idiomas.
 */

/** Cómo se juega. Manda en lo que se le promete al jugador, así que se dice siempre. */
export type GameMode = 'local' | 'bots' | 'online';

/** Color de acento, para que cada juego tenga su sitio visual en la parrilla. */
export type GameAccent = 'cyan' | 'pink' | 'yellow' | 'green';

export interface GameEntry {
  /** Identificador estable: da la ruta y las claves de traducción. */
  id: string;
  /** A dónde lleva «Jugar». */
  route: string;
  mode: GameMode;
  /** Cuántos juegan, en texto ya traducido por clave (`players.one`, `players.many`…). */
  playersKey: string;
  /** Presentación: emoji, como en los logros del póker. */
  icon: string;
  accent: GameAccent;
  /** Claves de i18n de las etiquetas («cartas», «arcade»…). */
  tags: string[];
  /**
   * Si ya se puede jugar. Un juego anunciado pero sin terminar aparece apagado y sin
   * botón: es mejor que enseñarlo roto.
   */
  available: boolean;
}

export const GAME_CATALOG: GameEntry[] = [
  {
    id: 'arcade',
    route: '/game',
    mode: 'local',
    playersKey: 'games.players.one',
    icon: '👾',
    accent: 'pink',
    tags: ['games.tag.arcade', 'games.tag.cards'],
    available: true,
  },
  {
    id: 'culo',
    route: '/culo',
    mode: 'online',
    playersKey: 'games.players.threeToSix',
    icon: '🂡',
    accent: 'green',
    tags: ['games.tag.cards', 'games.tag.shedding'],
    available: true,
  },
  {
    id: 'brisca',
    route: '/brisca',
    mode: 'bots',
    playersKey: 'games.players.twoToThree',
    icon: '🂢',
    accent: 'cyan',
    tags: ['games.tag.cards', 'games.tag.tricks'],
    available: true,
  },
  {
    id: 'tute',
    route: '/tute',
    mode: 'bots',
    playersKey: 'games.players.twoToThree',
    icon: '🂮',
    accent: 'yellow',
    tags: ['games.tag.cards', 'games.tag.tricks'],
    available: true,
  },
  {
    id: 'mus',
    route: '/mus',
    mode: 'bots',
    playersKey: 'games.players.four',
    icon: '🂺',
    accent: 'pink',
    tags: ['games.tag.cards', 'games.tag.betting'],
    available: true,
  },
  {
    id: 'mentiroso',
    route: '/mentiroso',
    mode: 'bots',
    playersKey: 'games.players.threeToSix',
    icon: '🤥',
    accent: 'yellow',
    tags: ['games.tag.cards', 'games.tag.shedding'],
    available: true,
  },
  {
    id: 'poker',
    route: '/poker',
    mode: 'online',
    playersKey: 'games.players.twoToSix',
    icon: '🃏',
    accent: 'cyan',
    tags: ['games.tag.cards', 'games.tag.betting'],
    available: true,
  },
];

/** Los que ya se pueden jugar. */
export const AVAILABLE_GAMES = GAME_CATALOG.filter((g) => g.available);

/** Los anunciados, para la sección de «próximamente». */
export const UPCOMING_GAMES = GAME_CATALOG.filter((g) => !g.available);

/** Clave de traducción del modo, para el distintivo de cada tarjeta. */
export function modeKey(mode: GameMode): string {
  return `games.mode.${mode}`;
}
