import { Injectable, inject, signal } from '@angular/core';

import { environment } from '../../../environments/environment';
import { AuthService } from './auth.service';

/** Cómo va la conexión, para poder decirlo en pantalla. */
export type ConnectionState = 'idle' | 'connecting' | 'open' | 'closed' | 'error';

/** Un jugador del lobby, tal y como lo manda el servidor. */
export interface SalaPlayerView {
  userId: number | null;
  username: string;
  isBot: boolean;
  connected: boolean;
}

/** La sala: el lobby y, si ya ha empezado, la partida (cada uno recibe la suya). */
export interface SalaView<Estado = unknown> {
  code: string;
  hostId: number;
  juego: string;
  status: 'lobby' | 'playing' | 'finished';
  opciones: Record<string, unknown>;
  isHost: boolean;
  players: SalaPlayerView[];
  game?: Estado;
}

/** Los códigos de error del servidor que sabemos traducir. */
const ERRORES_CONOCIDOS = new Set([
  'already_started',
  'room_full',
  'host_only',
  'min_players',
  'no_codes',
  'not_started',
  'unknown_action',
  'not_your_turn',
  'not_your_card',
  'no_cards',
  'no_rank',
  'rank_changed',
  'nothing_to_challenge',
  'self_challenge',
  'player_out',
  'not_four',
  'not_playing',
  'not_finished',
]);

/**
 * Cliente de las salas de juego: crear una, pasar el código y jugar.
 *
 * Es **genérico**: sirve para cualquier juego que viva en una sala, porque lo único que cambia es
 * el id del juego. El servidor es el que decide, así que aquí solo se manda lo que el jugador pide
 * y se pinta lo que llega: cada conexión recibe **su** vista.
 *
 * (El Culo tiene su propio servicio, anterior a este. Cuando se migre, este lo sustituye.)
 */
@Injectable({ providedIn: 'root' })
export class SalaOnlineService {
  private readonly auth = inject(AuthService);
  private socket: WebSocket | null = null;
  private juego = '';

  readonly connection = signal<ConnectionState>('idle');
  readonly sala = signal<SalaView | null>(null);
  /** Error como clave de traducción (lo normal). */
  readonly error = signal<string | null>(null);
  /** Texto tal cual lo mandó el servidor, para códigos que no conocemos. */
  readonly errorTexto = signal<string | null>(null);
  /** Mi asiento en la partida. */
  readonly seat = signal<number | null>(null);

  // ── Sala ──────────────────────────────────────────────────────────────────

  /** Crea una sala del juego pedido y devuelve su código para pasárselo a los amigos. */
  async crear(juego: string, opciones: Record<string, unknown> = {}): Promise<string> {
    const res = await fetch(`${environment.apiUrl}/salas/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...this.authHeaders() },
      body: JSON.stringify({ juego, opciones }),
    });
    if (!res.ok) throw new Error('no se pudo crear la sala');
    const datos = (await res.json()) as { code: string };
    return datos.code;
  }

  /** ¿Existe esa sala? Se comprueba antes de conectar, para dar un error claro. */
  async mirar(codigo: string): Promise<SalaView> {
    const res = await fetch(`${environment.apiUrl}/salas/${codigo.toUpperCase()}/`, {
      headers: this.authHeaders(),
    });
    if (res.status === 404) throw new Error('sala no encontrada');
    if (!res.ok) throw new Error('no se pudo consultar la sala');
    return (await res.json()) as SalaView;
  }

  /** Entra en la sala por WebSocket. */
  conectar(juego: string, codigo: string): void {
    this.desconectar();
    this.juego = juego;
    const token = this.auth.getToken() ?? '';
    const url =
      `${environment.wsUrl}/salas/${juego}/${codigo.toUpperCase()}/` +
      `?token=${encodeURIComponent(token)}`;

    this.connection.set('connecting');
    this.error.set(null);
    const socket = new WebSocket(url);
    this.socket = socket;

    socket.onopen = () => this.connection.set('open');
    socket.onclose = (evento) => {
      this.connection.set('closed');
      // Los códigos propios del servidor dicen qué ha pasado.
      if (evento.code === 4401) this.error.set('sala.sinSesion');
      else if (evento.code === 4404) this.error.set('sala.noExiste');
      else if (evento.code === 4409) this.error.set('sala.llena');
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
    this.sala.set(null);
    this.seat.set(null);
  }

  /** Volver a entrar tras una caída, sin salir de la mesa. */
  reconectar(codigo: string): void {
    if (this.juego) this.conectar(this.juego, codigo);
  }

  // ── Acciones ──────────────────────────────────────────────────────────────

  repartir(): void { this.enviar({ action: 'start' }); }
  anadirBot(): void { this.enviar({ action: 'add_bot' }); }
  quitarBot(): void { this.enviar({ action: 'remove_bot' }); }
  salir(): void { this.enviar({ action: 'leave' }); }

  /** Cualquier acción del juego (jugar, desconfiar, pasar de mano…). */
  accion(cuerpo: Record<string, unknown>): void {
    this.enviar(cuerpo);
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
      // El servidor manda un código corto; el texto español solo se usa si el código es nuevo
      // para nosotros (versión más vieja o más nueva del backend).
      const codigo = typeof mensaje['code'] === 'string' ? mensaje['code'] : '';
      const texto2 = typeof mensaje['message'] === 'string' ? mensaje['message'] : null;
      if (ERRORES_CONOCIDOS.has(codigo)) {
        this.error.set(`sala.error.${codigo}`);
        this.errorTexto.set(null);
      } else {
        this.error.set(null);
        this.errorTexto.set(texto2);
      }
      return;
    }
    if (mensaje['type'] !== 'state') return;

    this.sala.set(mensaje as unknown as SalaView);
    const asiento = mensaje['seat'];
    if (typeof asiento === 'number') this.seat.set(asiento);
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
