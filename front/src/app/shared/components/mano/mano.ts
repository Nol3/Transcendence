import { ChangeDetectionStrategy, Component, input, output } from '@angular/core';

import { TranslatePipe } from '../../../i18n';
import { CardDeck, CardSize, PlayingCard } from '../playing-card/playing-card';

/** Una carta de la mano: su id (para el `track` y el estado) y el código del mazo ("5o", "As"). */
export interface CartaMano {
  id: string;
  card: string;
  /** Esta carta, en concreto, no se puede tocar (en el tute solo valen algunas). */
  deshabilitada?: boolean;
  /** Está en la mano pero no se puede jugar: se ve apagada para que se entienda el porqué. */
  ilegal?: boolean;
}

/**
 * La mano, como un abanico: las cartas se reparten a lo ancho, con una rotación cada vez mayor
 * hacia los extremos y un arco suave. Una carta se levanta al pasar por encima (o al enfocarla con
 * el teclado) y se queda levantada cuando está elegida.
 *
 * La geometría se calcula en CSS a partir de dos números por carta (`--i`, `--n`), no en
 * TypeScript: así el abanico se recoloca solo cuando entran o salen cartas, sin recalcular nada.
 */
@Component({
  selector: 'app-mano',
  imports: [PlayingCard, TranslatePipe],
  templateUrl: './mano.html',
  styleUrl: './mano.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class Mano {
  readonly cartas = input.required<readonly CartaMano[]>();
  /** Ids de las cartas elegidas. */
  readonly elegidas = input<readonly string[]>([]);
  readonly baraja = input<CardDeck>('spanish');
  readonly tamano = input<CardSize>('lg');
  /** De dónde salen los nombres accesibles: `culo` y `baraja` tienen sus propias claves. */
  readonly clave = input<'culo' | 'baraja'>('baraja');
  /** Mano bloqueada (no es tu turno). */
  readonly deshabilitada = input(false);
  /** Le toca a este jugador: se ilumina el borde. */
  readonly turno = input(false);

  readonly alTocar = output<string>();

  estaElegida(id: string): boolean {
    return this.elegidas().includes(id);
  }

  /** "5o" → "5"; "12b" → "12". */
  rango(codigo: string): string {
    return codigo.slice(0, -1);
  }

  /** "5o" → "o". */
  palo(codigo: string): string {
    return codigo.slice(-1);
  }
}
