import { ChangeDetectionStrategy, Component, ElementRef, computed, inject, input } from '@angular/core';

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
    // El mazo de Balatro, recompuesto a partir de la tinta que trae el juego
    // (`scripts/generar_cartas_balatro.py`). El 8-bit sigue en `cards/` por si se quiere volver.
    carpeta: 'cards/balatro',
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
 * Una carta de la baraja. El póker usa el **mazo de Balatro** (recompuesto en
 * `scripts/generar_cartas_balatro.py`) y el resto de juegos, la baraja española en pixel art.
 * En los dos casos la carta entra escalonada, se levanta al pasar por encima y se hunde al
 * pulsarla.
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

  /**
   * Inclinación máxima, en grados. Balatro exagera más porque sus cartas ocupan media pantalla;
   * con las nuestras (46-89 px) 7° ya se nota y 10° marearía.
   */
  private static readonly INCLINACION = 7;
  /** Con el dedo el gesto es más tosco: menos inclinación, más control. */
  private static readonly INCLINACION_TACTO = 4;

  private readonly host = inject<ElementRef<HTMLElement>>(ElementRef);

  /** Si el sistema pide menos movimiento, la carta se queda quieta (no se inclina ni brilla). */
  private readonly sinMovimiento =
    typeof matchMedia === 'function' && matchMedia('(prefers-reduced-motion: reduce)').matches;

  readonly esValida = computed(() => this.partes() !== null);
  readonly src = computed(() => {
    const p = this.partes();
    // El dorso sale de la carpeta del mazo: el de Balatro y el de la española no se parecen.
    if (this.faceDown() || !p) return `${BARAJA[this.deck()].carpeta}/back.png`;
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

  /**
   * Inclina la carta hacia el puntero: la carta «mira» a donde estás, como en Balatro.
   *
   * El desplazamiento se **limita** a ±1 antes de pasarlo a grados. No es un detalle: en los
   * bordes de la pantalla (o con el dedo) el puntero se va muy lejos del centro y, sin límite, la
   * carta se deforma en un paralelogramo torcido. En el mod lo arreglaron justo así.
   */
  alMover(evento: PointerEvent): void {
    if (this.sinMovimiento) return;
    const caja = (evento.currentTarget as HTMLElement).getBoundingClientRect();
    if (!caja.width || !caja.height) return;

    const limitar = (valor: number) => Math.max(-1, Math.min(1, valor));
    const x = limitar(((evento.clientX - caja.left) / caja.width) * 2 - 1);
    const y = limitar(((evento.clientY - caja.top) / caja.height) * 2 - 1);
    const maximo =
      evento.pointerType === 'touch' ? PlayingCard.INCLINACION_TACTO : PlayingCard.INCLINACION;

    const estilo = this.host.nativeElement.style;
    estilo.setProperty('--pc-rx', `${(-y * maximo).toFixed(2)}deg`);
    estilo.setProperty('--pc-ry', `${(x * maximo).toFixed(2)}deg`);
    // El brillo sigue al dedo: es lo que convierte un rectángulo en una superficie.
    estilo.setProperty('--pc-luz-x', `${((x + 1) * 50).toFixed(1)}%`);
    estilo.setProperty('--pc-luz-y', `${((y + 1) * 50).toFixed(1)}%`);
  }

  /** La deja plana al salir (o al levantar el dedo). */
  alSalir(): void {
    const estilo = this.host.nativeElement.style;
    estilo.setProperty('--pc-rx', '0deg');
    estilo.setProperty('--pc-ry', '0deg');
    estilo.setProperty('--pc-luz-x', '50%');
    estilo.setProperty('--pc-luz-y', '50%');
  }

  /** En el móvil no hay «hover»: se inclina mientras el dedo está encima. */
  alPulsar(evento: PointerEvent): void {
    this.alMover(evento);
  }
}
