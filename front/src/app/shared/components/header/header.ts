import { Component, inject, signal } from '@angular/core';
import { RouterLink, RouterLinkActive } from '@angular/router';
import { AuthService } from '../../../core/services/auth.service';
import { NotificationService } from '../../../core/services/notification.service';
import { LanguageSwitcherComponent } from '../language-switcher/language-switcher';
import { TranslatePipe } from '../../../i18n/translate.pipe';

@Component({
  selector: 'app-header',
  standalone: true,
  imports: [RouterLink, RouterLinkActive, LanguageSwitcherComponent, TranslatePipe],
  templateUrl: './header.html',
  styleUrl: './header.scss',
})
export class Header {
  readonly auth = inject(AuthService);
  readonly notif = inject(NotificationService);
  readonly menuOpen = signal(false);

  toggleMenu() {
    this.menuOpen.update((v) => !v);
  }

  closeMenu() {
    this.menuOpen.set(false);
  }

  toggleNotifications() {
    this.notif.togglePanel();
  }

  closeNotifications() {
    this.notif.closePanel();
  }

  markAsRead(id: string) {
    this.notif.markAsRead(id);
  }

  markAllRead() {
    this.notif.markAllAsRead();
  }

  deleteNotification(id: string, event: Event) {
    event.stopPropagation();
    this.notif.deleteNotification(id);
  }

  getNotificationIcon(type: string): string {
    switch (type) {
      case 'match_invite': return '🎮';
      case 'tournament_start': return '🏆';
      case 'opponent_found': return '👤';
      case 'game_result': return '🎯';
      case 'friend_request': return '💬';
      default: return '🔔';
    }
  }

  formatTime(date: Date): string {
    const now = new Date();
    const diff = now.getTime() - new Date(date).getTime();
    const minutes = Math.floor(diff / 60000);
    const hours = Math.floor(diff / 3600000);
    
    if (minutes < 1) return 'now';
    if (minutes < 60) return `${minutes}m`;
    if (hours < 24) return `${hours}h`;
    return new Date(date).toLocaleDateString();
  }

  trackByNotif(_: number, notif: { id: string }): string {
    return notif.id;
  }
}
