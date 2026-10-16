import { Injectable, inject, signal } from '@angular/core';

import { environment } from '../../../environments/environment';
import { AuthService } from './auth.service';
import { Card } from '../games/culo/culo-deck';
import { GameEvent, GameState, PlayerState, Role, Trick } from '../games/culo/culo-engine';

/** Jugador tal y como lo manda el servidor: su mano solo si es la tuya. */
interface ServerPlayer {
  id: number;
  name: string;
  isBot: boolean;
  handCount: number;
  hand: Card[];
  role: Role | null;
  place: number | null;
  connected: boolean;
}

interface ServerState {
  players: ServerPlayer[];
  turn: number;
  table: Trick | null;
  passed: number[];
  round: number;
  decks: number;
  events: GameEvent[];
  phase: 'playing' | 'round-end';
}

export interface RoomView {
  code: string;
  hostId: number;
  status: 'lobby' | 'playing' | 'finished';
  decks: number;
  isHost: boolean;
  players: { userId: number | null; username: string; isBot: boolean; connected: boolean }[];
  game?: ServerState;
}

/** Los códigos de error del servidor que sabemos traducir. */
const ERRORES_CONOCIDOS = new Set([
  'already_started',
  'room_full',
  'host_only',
  'min_players',
  'no_codes',
  'not_your_turn',
  'round_not_over',
  'unknown_action',
]);

/** Cómo va la conexión, para poder decirlo en pantalla. */
export type ConnectionState = 'idle' | 'connecting' | 'open' | 'closed' | 'error';

/**
 * Cliente de las salas online del Culo.
 *
 * El servidor es el que decide: aquí solo se manda lo que el jugador pide (`jugar`,
 * `pasar`…) y se pinta lo que llega. Cada conexión recibe **su** vista, así que las
 * cartas de los demás no pasan por aquí hasta que toca enseñarlas.
 */
@Injectable({ providedIn: 'root' })
export class CuloOnlineService {
  private readonly auth = inject(AuthService);
  private socket: WebSocket | null = null;

  readonly connection = signal<ConnectionState>('idle');
  readonly room = signal<RoomView | null>(null);
  readonly estado = signal<GameState | null>(null);
  /** Error como clave de traducción (lo normal). */
  readonly error = signal<string | null>(null);
  /** Texto tal cual lo mandó el servidor, para códigos que no conocemos. */
  readonly errorTexto = signal<string | null>(null);
  /** Mi asiento en la partida, para saber qué mano es la mía. */
  readonly seat = signal<number | null>(null);

  // ── Sala ──────────────────────────────────────────────────────────────────

  /** Crea una sala y devuelve su código para pasárselo a los amigos. */
  async crear(barajas: 1 | 2): Promise<string> {
    const res = await fetch(`${environment.apiUrl}/culo/rooms/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...this.authHeaders() },
      body: JSON.stringify({ decks: barajas }),
    });
    if (!res.ok) throw new Error('no se pudo crear la sala');
    const datos = (await res.json()) as { code: string };
    return datos.code;
  }

  /** ¿Existe esa sala? Se comprueba antes de conectar, para dar un error claro. */
  async mirar(codigo: string): Promise<RoomView> {
    const res = await fetch(`${environment.apiUrl}/culo/rooms/${codigo.toUpperCase()}/`, {
      headers: this.authHeaders(),
    });
    if (res.status === 404) throw new Error('sala no encontrada');
    if (!res.ok) throw new Error('no se pudo consultar la sala');
    return (await res.json()) as RoomView;
  }

  /** Entra en la sala por WebSocket. */
  conectar(codigo: string): void {
    this.desconectar();
    const token = this.auth.getToken() ?? '';
    const url = `${environment.wsUrl}/culo/room/${codigo.toUpperCase()}/?token=${encodeURIComponent(token)}`;

    this.connection.set('connecting');
    this.error.set(null);
    const socket = new WebSocket(url);
    this.socket = socket;

    socket.onopen = () => this.connection.set('open');
    socket.onclose = (evento) => {
      this.connection.set('closed');
      // Los códigos propios del servidor dicen qué ha pasado.
      if (evento.code === 4401) this.error.set('culo.online.sinSesion');
      else if (evento.code === 4404) this.error.set('culo.online.salaNoExiste');
      else if (evento.code === 4409) this.error.set('culo.online.salaLlena');
    };
    socket.onerror = () => this.connection.set('error');
    socket.onmessage = (evento) => this.recibir(evento.data);
  }

  desconectar(): void {
    if (this.socket) {
      this.socket.onclose = null;
      this.socket.close();
      this.socket = null;
    }
    this.connection.set('idle');
    this.room.set(null);
    this.estado.set(null);
    this.seat.set(null);
  }

  // ── Acciones ──────────────────────────────────────────────────────────────

  repartir(): void { this.enviar({ action: 'start' }); }
  anadirBot(): void { this.enviar({ action: 'add_bot' }); }
  quitarBot(): void { this.enviar({ action: 'remove_bot' }); }
  pasar(): void { this.enviar({ action: 'pass' }); }
  siguienteRonda(): void { this.enviar({ action: 'next_round' }); }
  salir(): void { this.enviar({ action: 'leave' }); }
  jugar(cartas: Card[]): void {
    this.enviar({ action: 'play', cards: cartas.map((c) => c.id) });
  }

  limpiarError(): void {
    this.error.set(null);
    this.errorTexto.set(null);
  }

  // ── Interno ───────────────────────────────────────────────────────────────

  private recibir(texto: string): void {
    let mensaje: Record<string, unknown>;
    try {
      mensaje = JSON.parse(texto) as Record<string, unknown>;
    } catch {
      return;
    }

    if (mensaje['type'] === 'error') {
      // El servidor manda un código corto; el texto español solo se usa si el código es
      // nuevo para nosotros (versión más vieja o más nueva del backend).
      const codigo = typeof mensaje['code'] === 'string' ? mensaje['code'] : '';
      const texto = typeof mensaje['message'] === 'string' ? mensaje['message'] : null;
      if (ERRORES_CONOCIDOS.has(codigo)) {
        this.error.set(`culo.online.error.${codigo}`);
        this.errorTexto.set(null);
      } else {
        this.error.set(null);
        this.errorTexto.set(texto);
      }
      return;
    }
    if (mensaje['type'] !== 'state') return;

    const sala = mensaje as unknown as RoomView;
    this.room.set(sala);
    const asiento = mensaje['seat'];
    if (typeof asiento === 'number') this.seat.set(asiento);
    // El estado del juego se normaliza al mismo tipo que usa el modo local, para que la
    // mesa se pinte igual venga de donde venga.
    this.estado.set(sala.game ? this.normalizar(sala.game) : null);
  }

  private normalizar(juego: ServerState): GameState {
    return {
      players: juego.players.map(
        (p): PlayerState => ({
          id: p.id,
          name: p.name,
          isBot: p.isBot,
          hand: p.hand ?? [],
          handCount: p.handCount,
          role: p.role,
          place: p.place,
          connected: p.connected,
        }),
      ),
      turn: juego.turn,
      table: juego.table,
      passed: juego.passed ?? [],
      round: juego.round,
      decks: juego.decks === 2 ? 2 : 1,
      events: juego.events ?? [],
      phase: juego.phase,
    };
  }

  private enviar(cuerpo: Record<string, unknown>): void {
    if (this.socket?.readyState === WebSocket.OPEN) {
      this.socket.send(JSON.stringify(cuerpo));
    }
  }

  private authHeaders(): Record<string, string> {
    const token = this.auth.getToken();
    return token ? { Authorization: `Bearer ${token}` } : {};
  }
}
