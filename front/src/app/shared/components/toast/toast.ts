import { Component, inject } from '@angular/core';
import { NotificationService, Notification } from '../../../core/services/notification.service';

@Component({
  selector: 'app-toast',
  standalone: true,
  templateUrl: './toast.html',
  styleUrl: './toast.scss',
})
export class ToastComponent {
  readonly notif = inject(NotificationService);

  trackById(_: number, n: Notification) { return n.id; }

  iconFor(type: Notification['type']): string {
    const icons: Record<Notification['type'], string> = {
      success: '✓',
      error:   '✕',
      warning: '⚠',
      info:    'ℹ',
    };
    return icons[type];
  }
}
