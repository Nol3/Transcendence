import { Component, Input } from '@angular/core';
import { TranslatePipe } from '../../../i18n/translate.pipe';

export type SpinnerSize = 'sm' | 'md' | 'lg';

@Component({
  selector: 'app-spinner',
  standalone: true,
  imports: [TranslatePipe],
  template: `<span [class]="'spinner spinner--' + size" role="status"
                  [attr.aria-label]="'common.loading' | translate"></span>`,
  styleUrl: './spinner.scss',
})
export class SpinnerComponent {
  @Input() size: SpinnerSize = 'md';
}
