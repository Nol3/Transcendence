import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';

import { ChatMessage, ChatService } from './chat.service';

const yo = { id: 1, username: 'ana', avatar: null };
const luis = { id: 2, username: 'luis', avatar: null };
const marta = { id: 3, username: 'marta', avatar: null };

function mensaje(id: number, de: typeof yo, para: typeof yo, texto: string,
                 leido = true, cuando = '2026-07-01T10:00:00Z'): ChatMessage {
  return { id, sender: de, recipient: para, content: texto, created_at: cuando, is_read: leido };
}

describe('ChatService', () => {
  let service: ChatService;
  let http: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting()],
    });
    service = TestBed.inject(ChatService);
    http = TestBed.inject(HttpTestingController);
    service.setMyId(1);
  });

  afterEach(() => {
    // «Marcar como leído» se dispara al abrir una conversación; a los tests que no
    // van de eso no les importa, así que se vacía aquí en vez de en cada uno.
    http
      .match((r) => r.url.endsWith('/mark_read/'))
      .forEach((req) => req.flush({ marked_read: 0 }));
    http.verify();
  });

  describe('agrupa los mensajes en conversaciones', () => {
    it('una conversación por persona, con el último mensaje', () => {
      service.messages.set([
        mensaje(1, yo, luis, 'hola', true, '2026-07-01T10:00:00Z'),
        mensaje(2, luis, yo, '¿jugamos?', true, '2026-07-01T10:05:00Z'),
        mensaje(3, marta, yo, 'nos vemos', true, '2026-07-01T09:00:00Z'),
      ]);

      const convs = service.conversations();
      expect(convs.length).toBe(2);
      // La más reciente primero.
      expect(convs[0].user.username).toBe('luis');
      expect(convs[0].lastMessage.content).toBe('¿jugamos?');
      expect(convs[1].user.username).toBe('marta');
    });

    it('cuenta los mensajes sin leer que he recibido', () => {
      service.messages.set([
        mensaje(1, luis, yo, 'uno', false),
        mensaje(2, luis, yo, 'dos', false),
        mensaje(3, yo, luis, 'respuesta', true),
        mensaje(4, marta, yo, 'hola', true),
      ]);

      const convs = service.conversations();
      const conLuis = convs.find((c) => c.user.id === 2)!;
      const conMarta = convs.find((c) => c.user.id === 3)!;
      expect(conLuis.unread).toBe(2);
      expect(conMarta.unread).toBe(0);
    });

    it('sin mensajes no hay conversaciones', () => {
      expect(service.conversations()).toEqual([]);
    });
  });

  describe('hilo abierto', () => {
    beforeEach(() => {
      service.messages.set([
        mensaje(2, luis, yo, 'segundo', true, '2026-07-01T10:05:00Z'),
        mensaje(1, yo, luis, 'primero', true, '2026-07-01T10:00:00Z'),
        mensaje(3, marta, yo, 'de marta', true, '2026-07-01T10:10:00Z'),
      ]);
    });

    it('solo muestra la conversación abierta y en orden cronológico', () => {
      service.activeUserId.set(2);
      expect(service.thread().map((m) => m.content)).toEqual(['primero', 'segundo']);
    });

    it('sabe con quién estoy hablando', () => {
      service.activeUserId.set(3);
      expect(service.activeUser()?.username).toBe('marta');
    });

    it('sin conversación abierta el hilo está vacío', () => {
      expect(service.thread()).toEqual([]);
      expect(service.activeUser()).toBeNull();
    });
  });

  describe('envío y marcado como leído', () => {
    it('envía el mensaje al destinatario abierto', () => {
      service.activeUserId.set(2);

      service.send('  nos vemos en la mesa  ');
      const peticion = http.expectOne((r) => r.url.endsWith('/send_message/'));
      expect(peticion.request.body).toEqual({ recipient_id: 2, content: 'nos vemos en la mesa' });
      peticion.flush(mensaje(9, yo, luis, 'nos vemos en la mesa'));

      expect(service.messages()[0].content).toBe('nos vemos en la mesa');
    });

    it('no envía nada si está vacío o no hay conversación', () => {
      service.activeUserId.set(2);
      service.send('   ');
      http.expectNone((r) => r.url.endsWith('/send_message/'));

      service.closeConversation();
      service.send('hola');
      http.expectNone((r) => r.url.endsWith('/send_message/'));
    });

    it('al abrir una conversación marca como leídos sus mensajes', () => {
      service.messages.set([mensaje(1, luis, yo, 'hola', false)]);
      service.openConversation(2);

      const peticion = http.expectOne((r) => r.url.endsWith('/mark_read/'));
      expect(peticion.request.body).toEqual({ user_id: 2 });
      peticion.flush({ marked_read: 1 });

      expect(service.messages()[0].is_read).toBe(true);
      expect(service.conversations()[0].unread).toBe(0);
    });
  });

  it('carga el directorio de usuarios sin incluirme a mí', () => {
    service.loadUsers();
    http.expectOne((r) => r.url.endsWith('/users/')).flush({
      count: 3, next: null, previous: null, results: [yo, luis, marta],
    });
    expect(service.users().map((u) => u.username)).toEqual(['luis', 'marta']);
  });

  it('carga los mensajes y acepta la respuesta paginada de DRF', () => {
    service.loadMessages();
    http.expectOne((r) => r.url.endsWith('/chat/messages/')).flush({
      count: 1, next: null, previous: null,
      results: [mensaje(1, luis, yo, 'hola')],
    });
    expect(service.messages().length).toBe(1);
    expect(service.loading()).toBe(false);
  });
});
