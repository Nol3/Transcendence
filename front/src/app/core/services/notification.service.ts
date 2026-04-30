import { Injectable, signal, computed, OnDestroy, PLATFORM_ID, inject } from '@angular/core';
import { isPlatformBrowser } from '@angular/common';
import { environment } from '../../../environments/environment';

export type NotificationType = 'success' | 'error' | 'warning' | 'info';
export type RealTimeNotificationType =
  | 'match_invite'
  | 'tournament_start'
  | 'opponent_found'
  | 'game_result'
  | 'friend_request';

export interface Notification {
  id: string;
  type: NotificationType;
  title: string;
  message?: string;
  duration?: number;
}

export interface RealTimeNotification {
  id: string;
  type: RealTimeNotificationType;
  title: string;
  message: string;
  timestamp: Date;
  read: boolean;
  data?: Record<string, unknown>;
}

const ACCESS_TOKEN_KEY = 'access_token';

@Injectable({ providedIn: 'root' })
export class NotificationService implements OnDestroy {
  private readonly platformId = inject(PLATFORM_ID);

  private readonly _notifications = signal<Notification[]>([]);
  private readonly _realTimeNotifications = signal<RealTimeNotification[]>([]);
  private eventSource: EventSource | null = null;

  readonly notifications = this._notifications.asReadonly();
  readonly realTimeNotifications = this._realTimeNotifications.asReadonly();

  readonly unreadCount = computed(
    () => this._realTimeNotifications().filter((n) => !n.read).length,
  );

  readonly isConnected = signal(false);
  readonly showPanel = signal(false);

  private getToken(): string | null {
    if (isPlatformBrowser(this.platformId)) {
      return localStorage.getItem(ACCESS_TOKEN_KEY);
    }
    return null;
  }

  private isAuthenticated(): boolean {
    return !!this.getToken();
  }

  connect(): void {
    if (this.eventSource) return;

    const token = this.getToken();
    if (!token) return;

    const url = `${environment.apiUrl}/notifications/sse?token=${token}`;
    this.eventSource = new EventSource(url);

    this.eventSource.onopen = () => {
      this.isConnected.set(true);
    };

    this.eventSource.onmessage = (event) => {
      try {
        const notification: RealTimeNotification = JSON.parse(event.data);
        notification.timestamp = new Date(notification.timestamp);
        this.addRealTimeNotification(notification);
        this.showToast(notification);
      } catch {
        console.warn('Failed to parse notification');
      }
    };

    this.eventSource.onerror = () => {
      this.isConnected.set(false);
      this.reconnect();
    };
  }

  disconnect(): void {
    if (this.eventSource) {
      this.eventSource.close();
      this.eventSource = null;
      this.isConnected.set(false);
    }
  }

  private reconnect(): void {
    setTimeout(() => {
      if (this.isAuthenticated() && !this.eventSource) {
        this.connect();
      }
    }, 5000);
  }

  private addRealTimeNotification(notification: RealTimeNotification): void {
    this._realTimeNotifications.update((list) => [notification, ...list]);
  }

  private showToast(notification: RealTimeNotification): void {
    const type: NotificationType =
      notification.type === 'game_result'
        ? notification.message.includes('win')
          ? 'success'
          : 'error'
        : 'info';
    this.show(type, notification.title, notification.message, 5000);
  }

  markAsRead(id: string): void {
    this._realTimeNotifications.update((list) =>
      list.map((n) => (n.id === id ? { ...n, read: true } : n)),
    );
  }

  markAllAsRead(): void {
    this._realTimeNotifications.update((list) => list.map((n) => ({ ...n, read: true })));
  }

  deleteNotification(id: string): void {
    this._realTimeNotifications.update((list) => list.filter((n) => n.id !== id));
  }

  togglePanel(): void {
    this.showPanel.update((v) => !v);
  }

  closePanel(): void {
    this.showPanel.set(false);
  }

  show(type: NotificationType, title: string, message?: string, duration = 4000): void {
    const id = crypto.randomUUID();
    const notification: Notification = { id, type, title, message, duration };

    this._notifications.update((list) => [...list, notification]);

    if (duration > 0) {
      setTimeout(() => this.dismiss(id), duration);
    }
  }

  success(title: string, message?: string) {
    this.show('success', title, message);
  }
  error(title: string, message?: string) {
    this.show('error', title, message);
  }
  warning(title: string, message?: string) {
    this.show('warning', title, message);
  }
  info(title: string, message?: string) {
    this.show('info', title, message);
  }

  dismiss(id: string): void {
    this._notifications.update((list) => list.filter((n) => n.id !== id));
  }

  clear(): void {
    this._notifications.set([]);
  }

  ngOnDestroy(): void {
    this.disconnect();
  }
}
