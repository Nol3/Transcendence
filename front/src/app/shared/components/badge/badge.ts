import { Component, Input } from '@angular/core';

export type BadgeVariant = 'success' | 'error' | 'warning' | 'info' | 'default';

@Component({
  selector: 'app-badge',
  standalone: true,
  template: `<span [class]="'badge badge--' + variant"><ng-content /></span>`,
  styleUrl: './badge.scss',
})
export class BadgeComponent {
  @Input() variant: BadgeVariant = 'default';
}
