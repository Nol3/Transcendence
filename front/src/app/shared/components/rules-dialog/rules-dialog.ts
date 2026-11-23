import { DOCUMENT } from '@angular/common';
import { Component, EventEmitter, HostListener, Input, OnDestroy, Output, inject } from '@angular/core';

import { TranslatePipe } from '../../../i18n';
import { FocoDialogoDirective } from '../../directives/foco-dialogo.directive';
import { ButtonComponent } from '../button/button';
import { GameAccent } from '../game-shell/game-shell';

/**
 * Diálogo de reglas compartido.
 *
 * Los cinco juegos tenían su propia copia del overlay y del cierre. Ahora el
 * componente se encarga de lo que se olvidaba en unas y en otras: Escape, clic
 * en el fondo, bloqueo del scroll de la página y foco atrapado.
 */
@Component({
  selector: 'app-rules-dialog',
  standalone: true,
  imports: [FocoDialogoDirective, TranslatePipe, ButtonComponent],
  templateUrl: './rules-dialog.html',
  styleUrl: './rules-dialog.scss',
})
export class RulesDialog implements OnDestroy {
  private readonly doc = inject(DOCUMENT);
  private readonly overflowPrevio = this.doc.body.style.overflow;

  @Input({ required: true }) title = '';
  @Input() accent: GameAccent = 'cyan';
  @Output() closed = new EventEmitter<void>();

  constructor() {
    this.doc.body.style.overflow = 'hidden';
  }

  ngOnDestroy(): void {
    this.doc.body.style.overflow = this.overflowPrevio;
  }

  @HostListener('document:keydown.escape')
  cerrarConEscape(): void {
    this.close();
  }

  close(): void {
    this.closed.emit();
  }

  alPulsarFondo(evento: MouseEvent): void {
    if (evento.target === evento.currentTarget) this.close();
  }
}
