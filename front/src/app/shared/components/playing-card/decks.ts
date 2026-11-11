/**
 * Las barajas del proyecto.
 *
 * Aquí vive **todo lo que distingue una baraja de otra**: la carpeta del arte, la extensión y el
 * nombre que se enseña en el selector. Los juegos no deben saber nada de ficheros: hablan de
 * **códigos canónicos** de carta ("10o" = sota de oros, "1c" = as de copas, "Ah" = as de corazones)
 * y es esta capa la que decide qué imagen corresponde.
 *
 * Las dos barajas comparten los mismos 40 códigos españoles. La francesa añade los que la española
 * no tiene (8, 9, 10, J, Q, K) y usa sus propios palos.
 */

export type CardDeck = 'spanish' | 'poker';

export interface Deck {
  /** Clave de traducción del nombre que se ve en el selector. */
  readonly nombre: string;
  /** Carpeta dentro de `public/`. */
  readonly carpeta: string;
  /** `webp` en las barajas nuevas: pesan una décima parte que en PNG. */
  readonly extension: 'webp' | 'png';
  /** Cuántas cartas tiene (sin contar el dorso). */
  readonly cartas: number;
}

export const DECKS: Record<CardDeck, Deck> = {
  spanish: {
    nombre: 'ajustes.baraja.spanish',
    carpeta: 'cards/es8bit',
    extension: 'webp',
    cartas: 40,
  },
  poker: {
    nombre: 'ajustes.baraja.poker',
    carpeta: 'cards/8bit',
    extension: 'webp',
    cartas: 52,
  },
};

/** Baraja por defecto: la de casa. */
export const BARAJA_POR_DEFECTO: CardDeck = 'spanish';

/** Ruta de la imagen de una carta (o del dorso si no se pasa código). */
export function rutaDeCarta(deck: CardDeck, codigo?: string | null): string {
  const { carpeta, extension } = DECKS[deck];
  return codigo ? `${carpeta}/${codigo}.${extension}` : `${carpeta}/back.${extension}`;
}

/**
 * Equivalencia entre la baraja española de 40 y la francesa, que es la misma **sin 8, 9 ni 10**:
 * del 1 al 7 y sota (10), caballo (11) y rey (12). Sirve para validar que ninguna baraja recibe una
 * carta que no tiene y para el día que haya que pintar una baraja con el arte de la otra.
 */
export const EQUIVALENCIA_ESPANOLA: Readonly<Record<string, string>> = {
  '1': 'A',
  '2': '2',
  '3': '3',
  '4': '4',
  '5': '5',
  '6': '6',
  '7': '7',
  '10': 'J',
  '11': 'Q',
  '12': 'K',
};

/** Palos: oros→diamantes, copas→corazones, espadas→picas, bastos→tréboles. */
export const EQUIVALENCIA_PALOS: Readonly<Record<string, string>> = {
  o: 'd',
  c: 'h',
  e: 's',
  b: 'c',
};

/** ¿Esta baraja puede pintar ese código? Evita los 404 silenciosos (una carta en blanco). */
export function barajaTiene(deck: CardDeck, codigo: string): boolean {
  const rango = codigo.slice(0, -1);
  const palo = codigo.slice(-1);
  if (deck === 'poker') {
    return /^(A|[2-9]|T|J|Q|K)$/.test(rango) && 'cdhs'.includes(palo);
  }
  return rango in EQUIVALENCIA_ESPANOLA && palo in EQUIVALENCIA_PALOS;
}
