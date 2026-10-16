import { Injectable, computed, inject, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, map, tap } from 'rxjs';

import { environment } from '../../../environments/environment';

export interface ChatUser {
  id: number;
  username: string;
  avatar?: string | null;
}

export interface ChatMessage {
  id: number;
  sender: ChatUser;
  recipient: ChatUser;
  content: string;
  created_at: string;
  is_read: boolean;
}

/** Una conversación: el otro usuario, el último mensaje y cuántos sin leer. */
export interface Conversation {
  user: ChatUser;
  lastMessage: ChatMessage;
  unread: number;
}

/** El backend pagina con el formato de DRF: {count, next, previous, results}. */
interface DrfPage<T> {
  results?: T[];
}

function unwrap<T>(body: T[] | DrfPage<T>): T[] {
  return Array.isArray(body) ? body : (body.results ?? []);
}

@Injectable({ providedIn: 'root' })
export class ChatService {
  private readonly http = inject(HttpClient);
  private readonly base = `${environment.apiUrl}/chat/messages`;

  /** Todos mis mensajes (entrantes y salientes). */
  readonly messages = signal<ChatMessage[]>([]);
  /** Conversación abierta. */
  readonly activeUserId = signal<number | null>(null);
  /** Directorio de usuarios para empezar una conversación nueva. */
  readonly users = signal<ChatUser[]>([]);
  readonly loading = signal(false);
  readonly error = signal<string | null>(null);
  readonly sending = signal(false);

  /** Id del usuario con sesión: distingue lo que envío de lo que recibo. */
  private readonly myId = signal<number | null>(null);

  readonly conversations = computed<Conversation[]>(() => {
    const me = this.myId();
    const byUser = new Map<number, Conversation>();

    for (const msg of this.messages()) {
      const other = msg.sender.id === me ? msg.recipient : msg.sender;
      const previa = byUser.get(other.id);
      const sinLeer = msg.recipient.id === me && !msg.is_read ? 1 : 0;
      if (!previa) {
        byUser.set(other.id, { user: other, lastMessage: msg, unread: sinLeer });
      } else {
        previa.unread += sinLeer;
        if (new Date(msg.created_at) > new Date(previa.lastMessage.created_at)) {
          previa.lastMessage = msg;
        }
      }
    }
    return [...byUser.values()].sort(
      (a, b) =>
        new Date(b.lastMessage.created_at).getTime() -
        new Date(a.lastMessage.created_at).getTime(),
    );
  });

  /** Mensajes de la conversación abierta, del más antiguo al más nuevo. */
  readonly thread = computed<ChatMessage[]>(() => {
    const other = this.activeUserId();
    const me = this.myId();
    if (other == null) return [];
    return this.messages()
      .filter(
        (m) =>
          (m.sender.id === me && m.recipient.id === other) ||
          (m.sender.id === other && m.recipient.id === me),
      )
      .sort(
        (a, b) =>
          new Date(a.created_at).getTime() - new Date(b.created_at).getTime(),
      );
  });

  readonly activeUser = computed<ChatUser | null>(() => {
    const other = this.activeUserId();
    if (other == null) return null;
    const conv = this.conversations().find((c) => c.user.id === other);
    return conv?.user ?? this.users().find((u) => u.id === other) ?? null;
  });

  /** Guarda quién soy (lo lee el componente del usuario en sesión). */
  setMyId(id: number | null): void {
    this.myId.set(id);
  }

  loadMessages(): void {
    this.loading.set(true);
    this.http
      .get<ChatMessage[] | DrfPage<ChatMessage>>(`${this.base}/`)
      .pipe(map(unwrap))
      .subscribe({
        next: (lista) => {
          this.messages.set(lista);
          this.loading.set(false);
        },
        error: () => {
          this.error.set('chat.error.load');
          this.loading.set(false);
        },
      });
  }

  /** Directorio de usuarios para elegir con quién hablar (sin bots ni yo). */
  loadUsers(): void {
    this.http
      .get<ChatUser[] | DrfPage<ChatUser>>(`${environment.apiUrl}/users/`)
      .pipe(map(unwrap))
      .subscribe({
        next: (lista) => this.users.set(lista.filter((u) => u.id !== this.myId())),
        error: () => this.users.set([]),
      });
  }

  openConversation(userId: number): void {
    this.activeUserId.set(userId);
    this.markRead(userId);
  }

  closeConversation(): void {
    this.activeUserId.set(null);
  }

  send(content: string): void {
    const other = this.activeUserId();
    const texto = content.trim();
    if (other == null || !texto) return;

    this.sending.set(true);
    this.http
      .post<ChatMessage>(`${this.base}/send_message/`, {
        recipient_id: other,
        content: texto,
      })
      .subscribe({
        next: (msg) => {
          this.messages.update((lista) => [msg, ...lista]);
          this.sending.set(false);
        },
        error: (err) => {
          const detalle = err?.error?.content?.[0] ?? err?.error?.detail;
          this.error.set(typeof detalle === 'string' ? detalle : 'chat.error.send');
          this.sending.set(false);
        },
      });
  }

  /** Marca como leídos los mensajes que me ha enviado ese usuario. */
  markRead(userId: number): void {
    this.http.post<{ marked_read: number }>(`${this.base}/mark_read/`, { user_id: userId }).subscribe({
      next: () => {
        this.messages.update((lista) =>
          lista.map((m) =>
            m.sender.id === userId && m.recipient.id === this.myId()
              ? { ...m, is_read: true }
              : m,
          ),
        );
      },
      // Marcar como leído es cosmético: si falla, no se molesta al usuario.
      error: () => undefined,
    });
  }

  clearError(): void {
    this.error.set(null);
  }

  /** Recarga para refrescar la conversación (lo llama el sondeo periódico). */
  refresh(): Observable<ChatMessage[]> {
    return this.http
      .get<ChatMessage[] | DrfPage<ChatMessage>>(`${this.base}/`)
      .pipe(
        map(unwrap),
        tap((lista) => this.messages.set(lista)),
      );
  }
}
