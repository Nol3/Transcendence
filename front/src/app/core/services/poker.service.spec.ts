import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';

import { PokerService, cardParts } from './poker.service';

/**
 * WebSocket de mentira: guarda lo que se envía y permite empujar mensajes del
 * servidor, que es justo lo que hace el servidor real.
 */
class FakeWebSocket {
  static OPEN = 1;
  static CLOSED = 3;
  static created: FakeWebSocket[] = [];

  readyState = FakeWebSocket.OPEN;
  sent: string[] = [];
  onmessage: ((ev: { data: string }) => void) | null = null;
  onerror: (() => void) | null = null;
  onclose: ((ev: { code: number }) => void) | null = null;

  constructor(public url: string) {
    FakeWebSocket.created.push(this);
  }

  send(data: string): void {
    this.sent.push(data);
  }

  close(): void {
    this.readyState = FakeWebSocket.CLOSED;
  }

  /** Simula un mensaje del servidor. */
  server(data: unknown): void {
    this.onmessage?.({ data: JSON.stringify(data) });
  }
}

const estadoMesa = {
  type: 'table_state',
  you: 0,
  table: { id: 't1', hand_number: 3, finished: false, small_blind: 5, big_blind: 10, turn_timeout: 25, winner: null },
  game: {
    street: 'flop',
    board: ['7c', '2s', 'Ad'],
    pot: 60,
    current_bet: 20,
    actor: 0,
    complete: false,
    seats: [
      { index: 0, name: 'ana', stack: 900, committed: 20, folded: false, all_in: false, is_bot: false, hole: ['8c', 'Ts'], hole_count: 2 },
      { index: 1, name: 'rival', stack: 940, committed: 20, folded: false, all_in: false, is_bot: false, hole: null, hole_count: 2 },
    ],
    legal_actions: [
      { action: 'fold' },
      { action: 'call', amount: 20 },
      { action: 'raise', min: 40, max: 900 },
    ],
    result: null,
  },
  log: [],
};

describe('PokerService', () => {
  let service: PokerService;

  beforeEach(() => {
    localStorage.setItem('access_token', 'token-de-prueba');
    FakeWebSocket.created = [];
    (globalThis as unknown as { WebSocket: unknown }).WebSocket = FakeWebSocket;

    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting()],
    });
    service = TestBed.inject(PokerService);
  });

  afterEach(() => localStorage.removeItem('access_token'));

  const ultimo = () => FakeWebSocket.created[FakeWebSocket.created.length - 1];

  // ── cartas ───────────────────────────────────────────────────────────────
  describe('cardParts', () => {
    it('traduce el 10 y los palos', () => {
      expect(cardParts('Ts')).toEqual({ rank: '10', suit: '♠', red: false });
      expect(cardParts('7c').suit).toBe('♣');
      expect(cardParts('Ad').suit).toBe('♦');
    });

    it('marca en rojo corazones y diamantes', () => {
      expect(cardParts('2h').red).toBe(true);
      expect(cardParts('2d').red).toBe(true);
      expect(cardParts('2s').red).toBe(false);
      expect(cardParts('2c').red).toBe(false);
    });

    it('con un palo desconocido no revienta', () => {
      expect(cardParts('2x').suit).toBe('?');
    });
  });

  // ── cola de espera ───────────────────────────────────────────────────────
  describe('cola de espera', () => {
    it('pide la mesa con el tamaño elegido y arranca en «buscando»', () => {
      service.chooseTableSize(6);
      service.startQueue();

      expect(ultimo().url).toContain('/ws/poker/matchmaking');
      expect(ultimo().url).toContain('size=6');
      expect(service.status()).toBe('connecting');

      ultimo().server({ type: 'ready', stakes: { low: {} }, table_size: 6, queue_timeout: 15 });
      expect(service.status()).toBe('searching');
    });

    it('al encontrar mesa se conecta a ella y guarda el rival', () => {
      service.startQueue();
      const cola = ultimo();
      cola.server({ type: 'ready', stakes: {}, table_size: 2, queue_timeout: 15 });
      cola.server({ type: 'match_found', table_id: 'abc', opponent: 'Bot Nol3', seats: 2 });

      expect(service.status()).toBe('matched');
      expect(service.tableId()).toBe('abc');
      expect(service.opponent()).toBe('Bot Nol3');
      expect(ultimo().url).toContain('/ws/poker/table/abc');
    });

    it('cancelar deja todo como al principio', () => {
      service.startQueue();
      service.cancelQueue();
      expect(service.status()).toBe('idle');
      expect(service.tableId()).toBeNull();
    });
  });

  // ── mesa ─────────────────────────────────────────────────────────────────
  describe('mesa', () => {
    beforeEach(() => {
      service.startQueue();
      const cola = ultimo();
      cola.server({ type: 'match_found', table_id: 'abc', opponent: 'rival', seats: 2 });
      ultimo().server(estadoMesa);
    });

    it('con el estado del servidor sabe quién soy y quién es el rival', () => {
      expect(service.inTable()).toBe(true);
      expect(service.me()?.name).toBe('ana');
      expect(service.others().map((s) => s.name)).toEqual(['rival']);
    });

    it('solo se ven las cartas propias', () => {
      expect(service.me()?.hole).toEqual(['8c', 'Ts']);
      expect(service.others()[0].hole).toBeNull();
    });

    it('detecta que es mi turno y las acciones legales', () => {
      expect(service.myTurn()).toBe(true);
      expect(service.canCheck()).toBe(false);
      expect(service.callAction()?.amount).toBe(20);
      expect(service.raiseAction()?.min).toBe(40);
      expect(service.canAllIn()).toBe(false);
    });

    it('enviar una acción la manda por el WebSocket de la mesa', () => {
      service.act('call', 20);
      expect(ultimo().sent).toContain(JSON.stringify({ action: 'call', amount: 20 }));
    });

    it('si no es mi turno no hay acciones disponibles', () => {
      ultimo().server({ ...estadoMesa, game: { ...estadoMesa.game, actor: 1 } });
      expect(service.myTurn()).toBe(false);
      expect(service.legal()).toEqual([]);
    });
  });

  // ── espectador y chat ────────────────────────────────────────────────────
  describe('espectador', () => {
    it('entra en modo espectador sin asiento y ve todos los asientos', () => {
      service.spectateTable('abc');
      expect(service.spectating()).toBe(true);

      ultimo().server({ ...estadoMesa, you: null });
      expect(service.me()).toBeNull();
      expect(service.tableSeats().map((s) => s.name)).toEqual(['ana', 'rival']);
    });
  });

  describe('chat de mesa', () => {
    it('guarda los mensajes que llegan, marcando los míos', () => {
      service.spectateTable('abc');
      const ws = ultimo();
      ws.server({ ...estadoMesa, you: null });
      ws.server({ type: 'chat', from: 'rival', text: 'hola', at: '10:00', spectator: false });
      ws.server({ type: 'chat', from: 'mirón', text: 'desde la grada', at: '10:01', spectator: true });

      const chat = service.chat();
      expect(chat.length).toBe(2);
      expect(chat[0].from).toBe('rival');
      expect(chat[1].spectator).toBe(true);
    });

    it('enviar un mensaje lo manda al servidor', () => {
      service.spectateTable('abc');
      const ws = ultimo();
      ws.server({ ...estadoMesa, you: null });
      service.sendChat('  hola mesa  ');
      expect(ws.sent.some((s) => s.includes('"type":"chat"') && s.includes('hola mesa'))).toBe(true);
    });

    it('no manda mensajes vacíos', () => {
      service.spectateTable('abc');
      const ws = ultimo();
      ws.server({ ...estadoMesa, you: null });
      const antes = ws.sent.length;
      service.sendChat('   ');
      expect(ws.sent.length).toBe(antes);
    });

    it('un error del servidor se muestra al usuario', () => {
      service.spectateTable('abc');
      ultimo().server({ type: 'error', error: 'no estás sentado en esta mesa' });
      expect(service.error()).toBe('no estás sentado en esta mesa');
    });
  });

  // ── reset ────────────────────────────────────────────────────────────────
  it('reset deja el servicio limpio', () => {
    service.startQueue();
    service.spectateTable('abc');
    ultimo().server(estadoMesa);

    service.reset();
    expect(service.status()).toBe('idle');
    expect(service.state()).toBeNull();
    expect(service.chat()).toEqual([]);
    expect(service.spectating()).toBe(false);
  });
});
