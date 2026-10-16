import { ChangeDetectionStrategy, Component, computed, input } from '@angular/core';

import { TranslatePipe } from '../../../i18n';

/**
 * Códigos de carta, por baraja. En las dos el patrón es el mismo —valor + palo— pero
 * cada una tiene sus valores y sus palos:
 *   - póker: 2..9, T, J, Q, K, A con c, d, h, s  →  "As", "7c", "Td"
 *   - española: 1..7, 10, 11, 12 con o, c, e, b  →  "5o", "1e", "12b"
 */
const BARAJA = {
  poker: {
    rangos: ['2', '3', '4', '5', '6', '7', '8', '9', 'T', 'J', 'Q', 'K', 'A'],
    palos: ['c', 'd', 'h', 's'],
    carpeta: 'cards',
  },
  spanish: {
    rangos: ['1', '2', '3', '4', '5', '6', '7', '10', '11', '12'],
    palos: ['o', 'c', 'e', 'b'],
    carpeta: 'cards/es',
  },
} as const;

export type CardDeck = keyof typeof BARAJA;

export type CardSize = 'sm' | 'md' | 'lg' | 'xl';
export type CardState = 'idle' | 'turn' | 'winner' | 'folded' | 'dim';

/**
 * Una carta de la baraja, con el arte del proyecto (los PNG del mazo 8-bit que usa el
 * juego) y el acabado de Balatro: pixel art nítido, entrada escalonada, se levanta al
 * pasar por encima y se hunde al pulsarla.
 *
 * El dibujo lo pone el PNG, así que aquí no hay texto de rango ni de palo: solo la
 * carta. El nombre accesible sí se compone (rango + palo traducidos), porque una
 * imagen sin nombre no dice nada a quien no la ve.
 */
@Component({
  selector: 'app-playing-card',
  imports: [TranslatePipe],
  templateUrl: './playing-card.html',
  styleUrl: './playing-card.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class PlayingCard {
  /** Código de la carta, p. ej. "As" (póker) o "5o" (española). */
  readonly card = input<string>('');
  /** De qué baraja es: cambia los valores válidos y de dónde sale el PNG. */
  readonly deck = input<CardDeck>('poker');
  /** Si se enseña el dorso (cartas del rival, o antes del showdown). */
  readonly faceDown = input(false);
  readonly size = input<CardSize>('md');
  readonly state = input<CardState>('idle');
  /** Posición en el reparto, para escalonar la entrada de las cartas. */
  readonly order = input(0);

  readonly esValida = computed(() => this.partes() !== null);
  readonly src = computed(() => {
    const p = this.partes();
    if (this.faceDown() || !p) return 'cards/back.png';
    return `${BARAJA[this.deck()].carpeta}/${this.card()}.png`;
  });

  /** Rango y palo por separado, para componer el nombre accesible traducido. */
  readonly rango = computed(() => this.partes()?.rango ?? '');
  readonly palo = computed(() => this.partes()?.palo ?? '');

  private partes(): { rango: string; palo: string } | null {
    const c = (this.card() || '').trim().toLowerCase();
    if (c.length < 2) return null;
    const palo = c.slice(-1);
    const rango = c.slice(0, -1);
    const { rangos, palos } = BARAJA[this.deck()];
    // La comparación no distingue mayúsculas: "as" y "As" son la misma carta.
    const rangoValido = (rangos as readonly string[]).find((r) => r.toLowerCase() === rango);
    if (!rangoValido) return null;
    if (!(palos as readonly string[]).includes(palo)) return null;
    // Se devuelve como se escribe en cada baraja: en el póker el As es "A", en la
    // española los valores son números.
    return { rango: rangoValido, palo };
  }
}
