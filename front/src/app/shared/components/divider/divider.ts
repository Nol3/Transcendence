import { Component, Input } from '@angular/core';

@Component({
  selector: 'app-divider',
  standalone: true,
  template: `
    <div [class]="'divider divider--' + color">
      @if (label) {
        <span class="divider__label font-mono">{{ label }}</span>
      }
    </div>
  `,
  styleUrl: './divider.scss',
})
export class DividerComponent {
  @Input() label = '';
  @Input() color: 'cyan' | 'magenta' | 'muted' = 'muted';
}
