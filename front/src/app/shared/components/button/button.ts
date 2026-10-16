import { Component, Input, Output, EventEmitter, HostBinding, inject } from '@angular/core';
import { GameSound } from '../../../core/audio/game-sound';
import { SpinnerComponent } from '../spinner/spinner';

export type ButtonVariant = 'primary' | 'secondary' | 'ghost' | 'danger' | 'accent';
export type ButtonSize    = 'sm' | 'md' | 'lg';

@Component({
  selector: 'app-button',
  standalone: true,
  imports: [SpinnerComponent],
  templateUrl: './button.html',
  styleUrl: './button.scss',
})
export class ButtonComponent {
  private readonly sonido = inject(GameSound);

  @Input() variant: ButtonVariant = 'primary';
  @Input() size: ButtonSize = 'md';
  @Input() disabled = false;
  @Input() loading = false;
  @Input() type: 'button' | 'submit' | 'reset' = 'button';
  @Input() fullWidth = false;

  @Output() clicked = new EventEmitter<MouseEvent>();

  @HostBinding('style.width') get width() {
    return this.fullWidth ? '100%' : null;
  }

  onClick(event: MouseEvent) {
    if (this.disabled || this.loading) return;
    this.sonido.boton();
    this.clicked.emit(event);
  }
}
