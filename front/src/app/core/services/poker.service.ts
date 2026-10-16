import { Injectable, computed, inject, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { AuthService } from './auth.service';
import { environment } from '../../../environments/environment';

export type QueueStatus = 'idle' | 'connecting' | 'searching' | 'matched' | 'error';
export type StakeKey = 'micro' | 'low' | 'mid';

export interface StakeLevel {
  small_blind: number;
  big_blind: number;
  starting_stack: number;
}

export interface SeatView {
  index: number;
  name: string;
  stack: number;
  committed: number;
  folded: boolean;
  all_in: boolean;
  is_bot: boolean;
  hole: string[] | null;
  hole_count: number;
}

export interface LegalAction {
  action: string;
  amount?: number;
  min?: number;
  max?: number;
}

export interface GameView {
  street: string;
  board: string[];
  pot: number;
  button: number;
  current_bet: number;
  min_raise_to: number;
  actor: number | null;
  seats: SeatView[];
  legal_actions: LegalAction[];
  complete: boolean;
  result: TableResult | null;
  history: { event: string; seat?: number; action?: string; amount?: number }[];
}

export interface TableResult {
  showdown: boolean;
  board: string[];
  pots: { amount: number; winners: { seat: number; name: string; amount: number; hand: string | null }[] }[];
  total: number;
  revealed: Record<string, string[]>;
  hands?: Record<string, { name: string; tiebreak: number[] }>;
  stacks: number[];
}

export interface TableState {
  type: 'table_state';
  table: {
    id: string;
    hand_number: number;
    finished: boolean;
    small_blind: number;
    big_blind: number;
    turn_timeout: number;
    winner: string | null;
  };
  you: number | null;
  game: GameView | null;
  log: { event: string; [key: string]: unknown }[];
}

const SUIT_SYMBOL: Record<string, string> = { c: '♣', d: '♦', h: '♥', s: '♠' };

/** Carta del servidor ("As", "Td", "9c") → piezas para pintarla. */
export function cardParts(card: string): { rank: string; suit: string; red: boolean } {
  const rank = card.slice(0, -1);
  const suit = card.slice(-1).toLowerCase();
  return {
    rank: rank === 'T' ? '10' : rank,
    suit: SUIT_SYMBOL[suit] ?? '?',
    red: suit === 'h' || suit === 'd',
  };
}

/**
 * Cliente del póker online. Habla dos WebSockets con el servidor:
 * la cola de espera y la mesa. Todo el estado viene del servidor; aquí solo se
 * guarda y se pinta (el navegador no decide nada).
 */
/** Respuesta de `POST /api/tournament/<id>/matches/<mid>/table/`. */
export interface TournamentTableResponse {
  table_id: string;
  ws_path: string;
  opponent: { id: number; username: string };
  small_blind: number;
  big_blind: number;
  starting_stack: number;
  tournament: { id: number; name: string };
  match_id: number;
}

export interface TableChatMessage {
  from: string;
  text: string;
  at: string;
  spectator: boolean;
  /** Solo en los mensajes propios, para pintarlos a un lado. */
  mine?: boolean;
}

export interface LiveTable {
  table_id: string;
  seats: number;
  players: string[];
  small_blind: number;
  big_blind: number;
  hand_number: number;
  finished: boolean;
  tournament_id: number | null;
}

export type PokerTheme = 'classic' | 'neon' | 'crimson' | 'violet' | 'gold';

export interface PokerPreferences {
  theme: PokerTheme;
  stake: StakeKey;
  table_size: number;
  themes: PokerTheme[];
  updated_at?: string;
}

export interface TournamentMatchContext {
  tournamentId: string;
  tournamentName: string;
  matchId: string;
  opponent: string;
}

@Injectable({ providedIn: 'root' })
export class PokerService {
  private readonly auth = inject(AuthService);
  private readonly http = inject(HttpClient);

  readonly status = signal<QueueStatus>('idle');
  readonly stakes = signal<Record<string, StakeLevel>>({});
  readonly stake = signal<StakeKey>('low');
  readonly queueTimeout = signal(15);
  readonly secondsWaiting = signal(0);
  readonly tableId = signal<string | null>(null);
  readonly opponent = signal('');
  readonly matchMessage = signal('');
  readonly state = signal<TableState | null>(null);
  readonly error = signal<string | null>(null);
  readonly turnSeconds = signal<number | null>(null);
  /** Asientos de la mesa (2 = heads-up … 6). Se fija antes de entrar en la cola. */
  readonly tableSize = signal(2);
  readonly tableSizes = [2, 3, 4, 5, 6];
  /** Modo espectador: se mira la mesa, no se juega. */
  readonly spectating = signal(false);
  /** Chat de mesa (efímero, sin base de datos). */
  readonly chat = signal<TableChatMessage[]>([]);
  /** Mesas vivas para poder mirarlas. */
  readonly liveTables = signal<LiveTable[]>([]);
  /** Customización guardada: tema del tapete, ciegas y tamaño de mesa. */
  readonly theme = signal<PokerTheme>('classic');
  readonly themes = signal<PokerTheme[]>(['classic', 'neon', 'crimson', 'violet', 'gold']);
  /** Si la mesa es de un match de torneo, aquí van sus datos (si no, es null). */
  readonly tournamentMatch = signal<TournamentMatchContext | null>(null);

  private queueWs: WebSocket | null = null;
  private tableWs: WebSocket | null = null;
  private waitTimer: ReturnType<typeof setInterval> | null = null;
  private turnTimer: ReturnType<typeof setInterval> | null = null;

  // ── Vistas derivadas ────────────────────────────────────────────────────
  readonly me = computed<SeatView | null>(() => {
    const s = this.state();
    if (!s?.game || s.you == null) return null;
    return s.game.seats.find((x) => x.index === s.you) ?? null;
  });

  /** Los demás asientos de la mesa (en heads-up, uno solo). */
  readonly others = computed<SeatView[]>(() => {
    const s = this.state();
    if (!s?.game || s.you == null) return [];
    return s.game.seats.filter((x) => x.index !== s.you);
  });

  /** Todos los asientos de la mesa (un espectador no tiene asiento propio). */
  readonly allSeats = computed<SeatView[]>(() => this.state()?.game?.seats ?? []);

  /** Asientos a pintar arriba: los demás si juego, todos si solo miro. */
  readonly tableSeats = computed<SeatView[]>(() =>
    this.spectating() ? this.allSeats() : this.others(),
  );

  readonly rival = computed<SeatView | null>(() => {
    const s = this.state();
    if (!s?.game || s.you == null) return null;
    return s.game.seats.find((x) => x.index !== s.you) ?? null;
  });

  readonly inTable = computed(() => this.state() !== null);
  readonly myTurn = computed(() => {
    const s = this.state();
    return !!s?.game && !s.game.complete && s.game.actor === s.you;
  });

  readonly legal = computed<LegalAction[]>(() => (this.myTurn() ? this.state()!.game!.legal_actions ?? [] : []));
  readonly canFold = computed(() => this.legal().some((a) => a.action === 'fold'));
  readonly canCheck = computed(() => this.legal().some((a) => a.action === 'check'));
  readonly callAction = computed(() => this.legal().find((a) => a.action === 'call') ?? null);
  readonly raiseAction = computed(
    () => this.legal().find((a) => a.action === 'raise' || a.action === 'bet') ?? null,
  );
  readonly canAllIn = computed(() => this.legal().some((a) => a.action === 'all_in'));
  readonly allInAmount = computed(() => {
    const me = this.me();
    return me ? me.stack + me.committed : 0;
  });

  // ── Cola de espera ──────────────────────────────────────────────────────
  startQueue(): void {
    const token = this.auth.getToken();
    if (!token) {
      this.error.set('poker.error.auth');
      return;
    }
    this.reset();
    this.status.set('connecting');
    // El tamaño de mesa viaja en la URL: el servidor lo necesita ANTES de meter al
    // jugador en la cola (si no, dos clientes de mesa de 6 se emparejarían de dos).
    const ws = new WebSocket(
      `${environment.wsUrl}/poker/matchmaking?token=${token}&size=${this.tableSize()}`,
    );
    this.queueWs = ws;

    ws.onmessage = (ev) => this.onQueueMessage(JSON.parse(ev.data));
    ws.onerror = () => {
      this.error.set('poker.error.connection');
      this.status.set('error');
    };
    ws.onclose = (ev) => {
      if (ev.code === 4401) {
        this.error.set('poker.error.auth');
        this.status.set('error');
      } else if (this.status() === 'connecting' || this.status() === 'searching') {
        this.status.set('idle');
      }
    };
  }

  /**
   * Entra en la mesa REAL de un match de torneo: el backend crea (o devuelve) la
   * mesa con los dos participantes y aquí se abre su WebSocket. No hay cola ni
   * bot: el resultado lo cierra el servidor cuando termina la partida.
   */
  startTournamentMatch(tournamentId: string, matchId: string): void {
    const token = this.auth.getToken();
    if (!token) {
      this.error.set('poker.error.auth');
      return;
    }
    this.reset();
    this.status.set('connecting');

    this.http
      .post<TournamentTableResponse>(
        `${environment.apiUrl}/tournament/${tournamentId}/matches/${matchId}/table/`,
        {},
      )
      .subscribe({
        next: (res) => {
          this.tournamentMatch.set({
            tournamentId,
            tournamentName: res.tournament?.name ?? '',
            matchId: String(res.match_id),
            opponent: res.opponent?.username ?? '',
          });
          this.opponent.set(res.opponent?.username ?? '');
          this.tableId.set(res.table_id);
          this.status.set('matched');
          this.connectTable(res.table_id);
        },
        error: (err) => {
          const detail = err?.error?.error;
          this.error.set(typeof detail === 'string' ? detail : 'poker.error.connection');
          this.status.set('error');
        },
      });
  }

  /**
   * Entra como **espectador** en una mesa concreta: solo lectura. El servidor
   * manda la vista sin asiento, así que no se ven cartas ajenas fuera del showdown
   * y cualquier acción se rechaza.
   */
  spectateTable(tableId: string): void {
    const token = this.auth.getToken();
    if (!token) {
      this.error.set('poker.error.auth');
      return;
    }
    this.reset();
    this.spectating.set(true);
    this.status.set('matched');
    this.tableId.set(tableId);
    this.connectTable(tableId);
  }

  /** Trae las preferencias guardadas (tema, ciegas, tamaño de mesa). */
  loadPreferences(): void {
    this.http
      .get<PokerPreferences>(`${environment.apiUrl}/poker/preferences/`)
      .subscribe({
        next: (p) => {
          if (p.themes?.length) this.themes.set(p.themes);
          if (p.theme) this.theme.set(p.theme);
          if (p.stake) this.stake.set(p.stake);
          if (p.table_size) this.tableSize.set(p.table_size);
        },
        // Las preferencias son una comodidad: si fallan, se sigue con las de casa.
        error: () => undefined,
      });
  }

  /** Cambia el tema del tapete y lo guarda para la próxima vez. */
  setTheme(theme: PokerTheme): void {
    this.theme.set(theme);
    this.savePreferences({ theme });
  }

  private savePreferences(cambios: Partial<PokerPreferences>): void {
    this.http
      .put<PokerPreferences>(`${environment.apiUrl}/poker/preferences/`, cambios)
      .subscribe({ next: () => undefined, error: () => undefined });
  }

  loadLiveTables(): void {
    this.http.get<{ count: number; results: LiveTable[] }>(`${environment.apiUrl}/poker/tables/`)
      .subscribe({
        next: (res) => this.liveTables.set(res.results ?? []),
        error: () => this.liveTables.set([]),
      });
  }

  /** Envía un mensaje al chat de la mesa (jugadores y espectadores). */
  sendChat(text: string): void {
    const limpio = text.trim();
    if (!limpio || !this.tableWs || this.tableWs.readyState !== WebSocket.OPEN) return;
    this.tableWs.send(JSON.stringify({ type: 'chat', text: limpio }));
  }

  cancelQueue(): void {
    try {
      this.queueWs?.send(JSON.stringify({ type: 'cancel' }));
    } catch {
      /* el socket ya puede estar cerrado */
    }
    this.reset();
  }

  /** Cambiar el tamaño de mesa: si ya se estaba buscando, se reinicia la cola. */
  chooseTableSize(size: number): void {
    if (!this.tableSizes.includes(size)) return;
    this.tableSize.set(size);
    this.savePreferences({ table_size: size });
    if (this.status() === 'searching' || this.status() === 'connecting') {
      this.startQueue();
    }
  }

  chooseStake(stake: StakeKey): void {
    this.stake.set(stake);
    this.savePreferences({ stake });
    try {
      this.queueWs?.send(JSON.stringify({ type: 'stake', stake }));
    } catch {
      /* sin conexión todavía */
    }
  }

  private onQueueMessage(msg: Record<string, any>): void {
    switch (msg['type']) {
      case 'ready':
        this.stakes.set(msg['stakes'] ?? {});
        if (typeof msg['table_size'] === 'number') this.tableSize.set(msg['table_size']);
        this.queueTimeout.set(Number(msg['queue_timeout'] ?? 15));
        this.status.set('searching');
        this.startWaitingClock();
        break;
      case 'searching':
        this.status.set('searching');
        this.queueTimeout.set(Number(msg['queue_timeout'] ?? this.queueTimeout()));
        this.startWaitingClock();
        break;
      case 'match_found':
        this.status.set('matched');
        this.tableId.set(msg['table_id']);
        this.opponent.set(msg['opponent'] ?? '');
        this.matchMessage.set(msg['message'] ?? '');
        this.stopWaitingClock();
        this.connectTable(msg['table_id']);
        break;
      case 'cancelled':
        this.status.set('idle');
        this.stopWaitingClock();
        break;
      case 'error':
        this.error.set(msg['error'] ?? 'poker.error.generic');
        break;
    }
  }

  private startWaitingClock(): void {
    this.stopWaitingClock();
    this.secondsWaiting.set(0);
    this.waitTimer = setInterval(() => this.secondsWaiting.update((s) => s + 1), 1000);
  }

  private stopWaitingClock(): void {
    if (this.waitTimer) {
      clearInterval(this.waitTimer);
      this.waitTimer = null;
    }
  }

  // ── Mesa ────────────────────────────────────────────────────────────────
  private connectTable(tableId: string): void {
    const token = this.auth.getToken();
    if (!token) {
      this.error.set('poker.error.auth');
      return;
    }
    const ws = new WebSocket(`${environment.wsUrl}/poker/table/${tableId}?token=${token}`);
    this.tableWs = ws;
    ws.onmessage = (ev) => this.onTableMessage(JSON.parse(ev.data));
    ws.onerror = () => this.error.set('poker.error.connection');
    ws.onclose = (ev) => {
      if (ev.code === 4401) this.error.set('poker.error.auth');
      else if (ev.code === 4404) this.error.set('poker.error.tableGone');
    };
  }

  private onTableMessage(msg: Record<string, any>): void {
    if (msg['type'] === 'table_state') {
      this.state.set(msg as unknown as TableState);
      this.armTurnClock();
    } else if (msg['type'] === 'chat') {
      const mio = msg['from'] === this.auth.user()?.username;
      this.chat.update((lista) => [
        ...lista.slice(-40),
        {
          from: String(msg['from'] ?? ''),
          text: String(msg['text'] ?? ''),
          at: String(msg['at'] ?? ''),
          spectator: Boolean(msg['spectator']),
          mine: mio,
        },
      ]);
    } else if (msg['type'] === 'error') {
      this.error.set(String(msg['error'] ?? 'poker.error.generic'));
    }
  }

  private armTurnClock(): void {
    if (this.turnTimer) {
      clearInterval(this.turnTimer);
      this.turnTimer = null;
    }
    const s = this.state();
    if (!s?.game || s.game.complete || s.game.actor !== s.you) {
      this.turnSeconds.set(null);
      return;
    }
    this.turnSeconds.set(Math.ceil(s.table.turn_timeout));
    this.turnTimer = setInterval(() => {
      const v = this.turnSeconds();
      if (v == null || v <= 1) {
        if (this.turnTimer) clearInterval(this.turnTimer);
        this.turnTimer = null;
        this.turnSeconds.set(null);
        return;
      }
      this.turnSeconds.set(v - 1);
    }, 1000);
  }

  act(action: string, amount?: number): void {
    if (!this.tableWs || this.tableWs.readyState !== WebSocket.OPEN) return;
    const payload: Record<string, unknown> = { action };
    if (amount != null) payload['amount'] = amount;
    this.tableWs.send(JSON.stringify(payload));
  }

  clearError(): void {
    this.error.set(null);
  }

  /** Cierra todo y vuelve al estado inicial. */
  reset(): void {
    this.stopWaitingClock();
    if (this.turnTimer) {
      clearInterval(this.turnTimer);
      this.turnTimer = null;
    }
    for (const ws of [this.queueWs, this.tableWs]) {
      if (ws && (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING)) {
        ws.close();
      }
    }
    this.queueWs = null;
    this.tableWs = null;
    this.status.set('idle');
    this.state.set(null);
    this.tableId.set(null);
    this.opponent.set('');
    this.matchMessage.set('');
    this.secondsWaiting.set(0);
    this.turnSeconds.set(null);
    this.tournamentMatch.set(null);
    this.spectating.set(false);
    this.chat.set([]);
  }
}
