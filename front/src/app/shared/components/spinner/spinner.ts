import { Component, Input } from '@angular/core';

export type SpinnerSize = 'sm' | 'md' | 'lg';

@Component({
  selector: 'app-spinner',
  standalone: true,
  template: `<span [class]="'spinner spinner--' + size" role="status" aria-label="Loading"></span>`,
  styleUrl: './spinner.scss',
})
export class SpinnerComponent {
  @Input() size: SpinnerSize = 'md';
}
