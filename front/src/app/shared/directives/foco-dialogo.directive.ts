import { DOCUMENT } from '@angular/common';
import { Directive, ElementRef, OnDestroy, afterNextRender, inject } from '@angular/core';

/** Lo que puede recibir el foco dentro de un diálogo. */
const FOCALIZABLES =
  'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])';

/**
 * Manejo de foco de un diálogo modal.
 *
 * Los diálogos de los juegos (fin de partida y reglas) se abrían sin mover el foco, así que
 * quien navega con teclado seguía en el botón de detrás: el primer tabulador se iba a la
 * página de fondo y el diálogo quedaba, en la práctica, fuera de alcance. Esto hace lo mínimo
 * que se le pide a un modal:
 *
 *  - al abrirse, recuerda dónde estaba el foco y lo lleva dentro;
 *  - mientras está abierto, el tabulador no se escapa (da la vuelta dentro);
 *  - al cerrarse, devuelve el foco a donde estaba.
 *
 * Se engancha al diálogo con `@if` en la plantilla, así que se crea al abrirlo y se destruye
 * al cerrarlo: el ciclo de vida del componente ya marca cuándo empieza y acaba.
 */
@Directive({
  selector: '[appFocoDialogo]',
})
export class FocoDialogoDirective implements OnDestroy {
  private readonly host = inject<ElementRef<HTMLElement>>(ElementRef);
  private readonly doc = inject(DOCUMENT);
  /** Dónde estaba el foco antes de abrirse (normalmente, el botón que lo abrió). */
  private readonly anterior = this.doc.activeElement as HTMLElement | null;

  private readonly alTeclear = (evento: KeyboardEvent) => this.atraparTabulador(evento);

  constructor() {
    // `afterNextRender` y no `ngOnInit`: hace falta que el diálogo esté ya en el DOM (y solo
    // corre en el navegador, así que el prerender no se entera).
    afterNextRender(() => {
      this.doc.addEventListener('keydown', this.alTeclear, true);
      this.primero()?.focus();
    });
  }

  ngOnDestroy(): void {
    this.doc.removeEventListener('keydown', this.alTeclear, true);
    // Sin esto, al cerrarse el diálogo el foco se queda en el `body` y hay que tabular desde
    // el principio de la página otra vez.
    this.anterior?.focus?.();
  }

  private focalizables(): HTMLElement[] {
    return Array.from(this.host.nativeElement.querySelectorAll<HTMLElement>(FOCALIZABLES)).filter(
      (el) => !el.hasAttribute('disabled') && el.offsetParent !== null,
    );
  }

  private primero(): HTMLElement | null {
    return this.focalizables()[0] ?? null;
  }

  private atraparTabulador(evento: KeyboardEvent): void {
    if (evento.key !== 'Tab') return;
    const dentro = this.focalizables();
    if (dentro.length === 0) return;

    const activo = this.doc.activeElement;
    const primero = dentro[0];
    const ultimo = dentro[dentro.length - 1];

    // Si el foco se ha escapado (por ejemplo, porque algo de fuera se lo llevó), se devuelve.
    if (!activo || !this.host.nativeElement.contains(activo)) {
      evento.preventDefault();
      primero.focus();
      return;
    }
    if (evento.shiftKey && activo === primero) {
      evento.preventDefault();
      ultimo.focus();
    } else if (!evento.shiftKey && activo === ultimo) {
      evento.preventDefault();
      primero.focus();
    }
  }
}
