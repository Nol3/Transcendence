import { Component, EventEmitter, Input, Output } from '@angular/core';
import { RouterLink } from '@angular/router';

import { TranslatePipe } from '../../../i18n';
import { ButtonComponent } from '../button/button';

export type GameAccent = 'cyan' | 'magenta' | 'yellow' | 'green';

/**
 * Cabecera común de las mesas de cartas.
 *
 * Antes cada juego repetía título, botón de reglas, altavoz y “volver”. Eso hacía
 * que cinco pantallas se vieran parecidas pero no iguales, y que un arreglo hubiera
 * que hacerlo cinco veces. Aquí el juego solo aporta su título y su acento; las
 * acciones son las mismas para todos.
 */
@Component({
  selector: 'app-game-shell',
  standalone: true,
  imports: [RouterLink, TranslatePipe, ButtonComponent],
  templateUrl: './game-shell.html',
  styleUrl: './game-shell.scss',
})
export class GameShell {
  @Input({ required: true }) title = '';
  @Input() subtitle = '';
  @Input() accent: GameAccent = 'cyan';
  /** Clave i18n del botón de reglas (cada juego la suya). */
  @Input() rulesLabel = 'game.rules.howToPlay';
  @Input() soundOn = true;

  @Output() rules = new EventEmitter<void>();
  @Output() sound = new EventEmitter<void>();
}
