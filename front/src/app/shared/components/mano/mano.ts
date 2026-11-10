import { DOCUMENT, isPlatformBrowser } from '@angular/common';
import {
  ChangeDetectionStrategy,
  Component,
  computed,
  HostListener,
  inject,
  input,
  OnDestroy,
  OnInit,
  output,
  PLATFORM_ID,
  signal,
} from '@angular/core';

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
export class Mano implements OnInit, OnDestroy {
  private readonly plataforma = inject(PLATFORM_ID);
  private readonly documento = inject(DOCUMENT);

  ngOnInit(): void {
    if (!isPlatformBrowser(this.plataforma)) return;
    // La mano es fija: se reserva su hueco al final de la página para que no tape los controles.
    this.documento.body.classList.add('tiene-mano');
  }

  ngOnDestroy(): void {
    if (!isPlatformBrowser(this.plataforma)) return;
    this.documento.body.classList.remove('tiene-mano');
  }

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

  /** Ancho de la ventana, para recalcular el tamaño de carta al girar el móvil. */
  private readonly anchoVentana = signal(
    typeof window === 'undefined' ? 390 : window.innerWidth,
  );

  @HostListener('window:resize')
  alRedimensionar(): void {
    this.anchoVentana.set(window.innerWidth);
  }

  /**
   * Ancho de cada carta para que la mano quepa entera.
   *
   * Las cartas se solapan un 38 %, así que N cartas ocupan `W + (N-1)·0,62·W`. Se despeja W con el
   * ancho disponible (la ventana menos un margen). Con 7 cartas salen los 64 px de siempre; con 10
   * en un móvil de 390 baja a ~54 px, en vez de salirse de la pantalla.
   */
  readonly anchoCarta = computed(() => {
    const cuantas = Math.max(this.cartas().length, 1);
    const base = this.tamano() === 'lg' ? 64 : 46;
    const disponible = this.anchoVentana() - 32;
    const calculado = disponible / (1 + 0.62 * (cuantas - 1));
    return Math.max(38, Math.min(base, Math.floor(calculado)));
  });

  /** Media anchura del abanico en cartas (para repartir el giro entre los extremos). */
  readonly mitad = computed(() => Math.max((this.cartas().length - 1) / 2, 1));

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
