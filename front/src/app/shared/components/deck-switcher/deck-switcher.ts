import { Component, ElementRef, HostListener, computed, inject, signal } from '@angular/core';

import { Baraja } from '../../../core/baraja';
import { TranslatePipe } from '../../../i18n';
import { CardDeck } from '../playing-card/decks';

/**
 * Selector de baraja, calcado del de idioma: botón con desplegable, cierra al hacer clic fuera y
 * usa las mismas clases de estilo para que se vean iguales en la cabecera.
 *
 * La elección la guarda el servicio `Baraja` y afecta a todas las mesas a la vez.
 */
@Component({
  selector: 'app-deck-switcher',
  imports: [TranslatePipe],
  templateUrl: './deck-switcher.html',
  styleUrls: ['../language-switcher/language-switcher.scss'],
})
export class DeckSwitcher {
  private readonly servicio = inject(Baraja);
  private readonly el = inject(ElementRef);

  readonly barajas = computed(() =>
    this.servicio.disponibles().map((b) => ({
      code: b.clave,
      label: b.nombre,
      flag: b.clave === 'spanish' ? '\u{1F0CB}' : '\u{1F0CF}',
    })),
  );

  readonly isOpen = signal(false);

  get actual() {
    return this.barajas().find((b) => b.code === this.servicio.baraja()) ?? this.barajas()[0];
  }

  toggle(): void {
    this.isOpen.update((v) => !v);
  }

  select(code: CardDeck): void {
    this.servicio.elegir(code);
    this.isOpen.set(false);
  }

  @HostListener('document:click', ['$event'])
  alClicFuera(ev: Event): void {
    if (!this.el.nativeElement.contains(ev.target)) this.isOpen.set(false);
  }

  @HostListener('document:keydown.escape')
  alEscape(): void {
    this.isOpen.set(false);
  }
}
