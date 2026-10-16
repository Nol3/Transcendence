import { Component, OnDestroy, OnInit, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';

import { AuthService } from '../../core/services/auth.service';
import { ChatService, Conversation } from '../../core/services/chat.service';
import { AvatarComponent } from '../../shared/components/avatar/avatar';
import { ButtonComponent } from '../../shared/components/button/button';
import { CardComponent } from '../../shared/components/card/card';
import { PixelTitleComponent } from '../../shared/components/pixel-title/pixel-title';
import { TranslatePipe } from '../../i18n';

/** Cada cuánto se refresca la lista mientras la página está abierta. */
const POLL_MS = 5000;

@Component({
  selector: 'app-chat',
  standalone: true,
  imports: [AvatarComponent, ButtonComponent, CardComponent, FormsModule, PixelTitleComponent, TranslatePipe],
  templateUrl: './chat.html',
  styleUrl: './chat.scss',
})
export class Chat implements OnInit, OnDestroy {
  readonly chat = inject(ChatService);
  private readonly auth = inject(AuthService);

  readonly draft = signal('');
  readonly filter = signal('');
  readonly showPicker = signal(false);

  private poll: ReturnType<typeof setInterval> | null = null;

  /** Usuarios del directorio que no aparecen ya en una conversación. */
  readonly candidates = computed(() => {
    const yaHablo = new Set(this.chat.conversations().map((c) => c.user.id));
    const texto = this.filter().trim().toLowerCase();
    return this.chat
      .users()
      .filter((u) => !yaHablo.has(u.id))
      .filter((u) => !texto || u.username.toLowerCase().includes(texto));
  });

  ngOnInit(): void {
    this.chat.setMyId(this.auth.user()?.id ?? null);
    this.chat.loadMessages();
    this.chat.loadUsers();
    // El backend del chat no tiene WebSocket: se refresca por sondeo ligero.
    this.poll = setInterval(() => {
      this.chat.refresh().subscribe({ error: () => undefined });
    }, POLL_MS);
  }

  ngOnDestroy(): void {
    if (this.poll) clearInterval(this.poll);
  }

  open(userId: number): void {
    this.chat.clearError();
    this.showPicker.set(false);
    this.chat.openConversation(userId);
  }

  startWith(userId: number): void {
    this.open(userId);
  }

  send(): void {
    const texto = this.draft();
    if (!texto.trim()) return;
    this.chat.send(texto);
    this.draft.set('');
  }

  /** Enter envía; Mayús+Enter hace salto de línea. */
  onKeydown(event: KeyboardEvent): void {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      this.send();
    }
  }

  isMine(messageId: number): boolean {
    const msg = this.chat.messages().find((m) => m.id === messageId);
    return msg != null && msg.sender.id === this.myId();
  }

  /** Id del usuario en sesión (para pintar mi lado de la conversación). */
  readonly myId = computed(() => this.auth.user()?.id ?? null);

  trackConversation(_: number, c: Conversation): number {
    return c.user.id;
  }

  formatTime(iso: string): string {
    const d = new Date(iso);
    return Number.isNaN(d.getTime())
      ? ''
      : d.toLocaleString(undefined, {
          day: '2-digit',
          month: '2-digit',
          hour: '2-digit',
          minute: '2-digit',
        });
  }
}
