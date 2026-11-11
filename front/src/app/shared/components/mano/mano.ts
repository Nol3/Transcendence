import { DOCUMENT, isPlatformBrowser } from '@angular/common';
import {
  ChangeDetectionStrategy,
  Component,
  computed,
  HostBinding,
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
  /** Se pide jugar esa carta sin pasar por el botón (doble toque o gesto hacia arriba). */
  readonly alLanzar = output<string>();

  /** Carta que se está mirando de cerca (toque mantenido). */
  readonly vistaPrevia = signal<string | null>(null);

  private temporizador: ReturnType<typeof setTimeout> | null = null;
  private fueLarga = false;
  private inicio: { x: number; y: number; cuando: number } | null = null;
  private ultimoToque = { id: '', cuando: 0 };

  /** Umbrales del mod, en píxeles: 56 de recorrido y 60 % de desviación lateral como máximo. */
  private static readonly RECORRIDO = 56;
  private static readonly LARGA = 450;
  private static readonly DOBLE = 300;

  /** Ancho de la ventana, para recalcular el tamaño de carta al girar el móvil. */
  private readonly anchoVentana = signal(
    typeof window === 'undefined' ? 390 : window.innerWidth,
  );

  @HostBinding('class.vista-abierta')
  get conVista(): boolean {
    return this.vistaPrevia() !== null;
  }

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

  // ── Gestos ─────────────────────────────────────────────────────────────────────────────────
  // Tocar elige; tocar dos veces seguidas (o arrastrar hacia arriba) juega; mantener pulsado enseña
  // la carta de cerca. Todo con `pointer`, que en el móvil llega igual que el toque y en escritorio
  // funciona con el ratón.

  alBajar(ev: PointerEvent, c: CartaMano): void {
    this.fueLarga = false;
    this.inicio = { x: ev.clientX, y: ev.clientY, cuando: Date.now() };
    this.cancelar();
    this.temporizador = setTimeout(() => {
      this.fueLarga = true;
      this.vistaPrevia.set(c.card);
      this.vibrar(10);
    }, Mano.LARGA);
  }

  alSoltar(ev: PointerEvent, c: CartaMano): void {
    this.cancelar();
    const inicio = this.inicio;
    this.inicio = null;
    // Un toque mantenido ya ha hecho lo suyo (enseñar la carta): no elige ni juega.
    if (this.fueLarga || !inicio) return;

    const dx = ev.clientX - inicio.x;
    const dy = ev.clientY - inicio.y;
    const rapido = Date.now() - inicio.cuando <= 600;
    // Hacia arriba, con recorrido suficiente y sin torcerse: se juega la carta directamente.
    if (rapido && dy <= -Mano.RECORRIDO && Math.abs(dx) <= Math.abs(dy) * 0.6) {
      this.alLanzar.emit(c.id);
      return;
    }
    // Ni gesto ni toque mantenido: es un toque normal, y aquí se decide si es el segundo seguido.
    this.registrarToque(c);
  }

  alCancelar(): void {
    this.cancelar();
    this.inicio = null;
  }

  /**
   * El `click` solo se usa para el **teclado** (Enter y espacio llegan con `detail === 0`).
   * Con ratón o dedo manda `pointerup`: si se contara también aquí, cada toque contaría dos veces y
   * el doble toque saldría en el primero. Ese era el fallo intermitente.
   */
  alPulsar(ev: MouseEvent, c: CartaMano): void {
    if (this.fueLarga) {
      this.fueLarga = false;
      return;
    }
    if (ev.detail === 0) this.registrarToque(c);
  }

  /** Un toque: el primero elige; el segundo sobre la misma carta, en menos de `DOBLE`, juega. */
  private registrarToque(c: CartaMano): void {
    const ahora = Date.now();
    const seguido = this.ultimoToque.id === c.id && ahora - this.ultimoToque.cuando < Mano.DOBLE;
    this.ultimoToque = seguido ? { id: '', cuando: 0 } : { id: c.id, cuando: ahora };
    if (seguido) {
      this.alLanzar.emit(c.id);
      return;
    }
    this.vibrar(6);
    this.alTocar.emit(c.id);
  }

  cerrarVista(): void {
    this.vistaPrevia.set(null);
  }

  /** Un toque en cualquier sitio cierra la vista previa (más fiable que el `click` del fondo). */
  @HostListener('document:pointerdown', ['$event'])
  alTocarFuera(ev: PointerEvent): void {
    if (!this.vistaPrevia()) return;
    const dentro = (ev.target as HTMLElement | null)?.closest('.vista__caja');
    if (!dentro) this.cerrarVista();
  }

  @HostListener('document:keydown.escape')
  alEscape(): void {
    this.cerrarVista();
  }

  private cancelar(): void {
    if (this.temporizador !== null) {
      clearTimeout(this.temporizador);
      this.temporizador = null;
    }
  }

  private vibrar(ms: number): void {
    if (!isPlatformBrowser(this.plataforma)) return;
    navigator.vibrate?.(ms);
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
