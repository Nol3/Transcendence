import {
  ChangeDetectionStrategy,
  Component,
  OnDestroy,
  computed,
  effect,
  inject,
  signal,
} from '@angular/core';

import { RouterLink } from '@angular/router';

import { TranslatePipe } from '../../../i18n';
import { Card } from '../../../core/games/baraja';
import { Baza, fuerza, ordenarMano, puntos } from '../../../core/games/bazas';
import {
  BriscaState,
  cambiarTriunfo,
  newGame,
  nextGame,
  play,
  puedeCambiarTriunfo,
} from '../../../core/games/brisca/brisca-engine';
import { botDecision } from '../../../core/games/brisca/brisca-bots';
import { ButtonComponent } from '../../../shared/components/button/button';
import { FocoDialogoDirective } from '../../../shared/directives/foco-dialogo.directive';
import { PlayingCard } from '../../../shared/components/playing-card/playing-card';
import { GameSound } from '../../../core/audio/game-sound';
import { BriscaVista, estadoDesdeVista } from '../../../core/games/brisca/brisca-online';
import { SalaOnlineService } from '../../../core/services/sala-online.service';
import { SalaLobby } from '../../../shared/components/sala-lobby/sala-lobby';

interface LogLine {
  kind: 'trick' | 'swap' | 'game-end' | 'match-end';
  key: string;
  params: Record<string, string | number>;
}

/**
 * Mesa de la Brisca.
 *
 * El componente no sabe de reglas: se las pide al motor (`core/games/brisca`) y pinta el estado
 * que le devuelve. El bot juega solo, con una pausa entre bazas para que se pueda seguir.
 */
@Component({
  selector: 'app-brisca',
  imports: [ButtonComponent, PlayingCard, RouterLink, SalaLobby, TranslatePipe, FocoDialogoDirective],
  templateUrl: './brisca.html',
  styleUrl: './brisca.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class Brisca implements OnDestroy {
  private readonly sonido = inject(GameSound);

  readonly salas = inject(SalaOnlineService);

  /** Cómo se está jugando: contra bots o con amigos. */
  readonly modo = signal<'menu' | 'local' | 'online'>('menu');
  /** La partida de contra bots. */
  private readonly estadoLocal = signal<BriscaState | null>(null);

  /** Lo que pinta la mesa: la partida local o la del servidor, adaptada a la misma forma. */
  readonly estado = computed(() => {
    if (this.modo() === 'online') {
      const vista = this.salas.sala()?.game as BriscaVista | undefined;
      const seat = this.salas.seat();
      return vista && seat !== null ? estadoDesdeVista(vista, seat) : null;
    }
    return this.estadoLocal();
  });

  readonly seleccion = signal<Card | null>(null);
  readonly reglasAbiertas = signal(false);
  /** Arranca como lo dejara el jugador: el silencio se recuerda. */
  readonly sonidoActivo = signal(this.sonido.encendido);
  readonly jugadores = signal(2);
  readonly juegosObjetivo = signal(3);

  private temporizador: ReturnType<typeof setTimeout> | null = null;

  /** Mi asiento: en local es el 0; con amigos, el que me da el servidor. */
  readonly yo = computed(() => (this.modo() === 'online' ? (this.salas.seat() ?? 0) : 0));

  /** Cuándo sonó la última baza, para no repetir el sonido en cada repintado. */
  private ultimaBazaSonada: number | null = null;
  private finSonado = false;

  /** Cada vez que se cierra una baza suena algo: golpe si la gano yo, un tic si no. */
  private readonly _sonidoBazas = effect(() => {
    const ganador = this.estado()?.lastWinner ?? null;
    if (ganador === null || ganador === this.ultimaBazaSonada) return;
    this.ultimaBazaSonada = ganador;
    if (ganador === this.yo()) this.sonido.baza();
    else this.sonido.tic();
  });

  /** Al acabar la partida: fanfarria si gano yo, algo más apagado si no. */
  private readonly _sonidoFinal = effect(() => {
    const s = this.estado();
    if (!s || s.phase !== 'match-end' || this.finSonado) return;
    this.finSonado = true;
    if (s.winner === this.yo()) this.sonido.victoria();
    else this.sonido.derrota();
  });

  readonly miTurno = computed(() => {
    const s = this.estado();
    return !!s && s.phase === 'playing' && s.turn === this.yo();
  });

  readonly miMano = computed(() => this.estado()?.players[this.yo()]?.hand ?? []);
  readonly rivales = computed(() => (this.estado()?.players ?? []).filter((p) => p.id !== this.yo()));
  readonly triunfo = computed(() => this.estado()?.trumpSuit ?? null);
  readonly baza = computed<Baza[]>(() => this.estado()?.trick ?? []);

  /** Los tantos de cada uno, para la mesa. */
  readonly marcador = computed(() =>
    (this.estado()?.players ?? []).map((p) => ({
      id: p.id,
      name: p.name,
      tantos: p.tantos ?? p.won.reduce((n, c) => n + puntos(c), 0),
      bazas: p.tricks,
      juegos: this.estado()!.gamesWon[p.id] ?? 0,
    })),
  );

  readonly puedoCambiar = computed(() => {
    const s = this.estado();
    return !!s && this.miTurno() && puedeCambiarTriunfo(s, this.yo());
  });

  /** ¿Puedo jugar la carta elegida? (Aquí cualquier carta vale: no hay obligación de asistir.) */
  readonly puedoJugar = computed(() => this.miTurno() && this.seleccion() !== null);

  readonly registro = computed<LogLine[]>(() => {
    const s = this.estado();
    if (!s) return [];
    const nombre = (id: number) => s.players[id]?.name ?? '';
    return s.events
      .filter((e) => e.kind !== 'deal' && e.kind !== 'play')
      .map((e): LogLine => {
        if (e.kind === 'trick') {
          return {
            kind: 'trick',
            key: 'brisca.log.trick',
            params: { name: nombre(e.winner), tantos: e.tantos },
          };
        }
        if (e.kind === 'swap') {
          return { kind: 'swap', key: 'brisca.log.swap', params: { name: nombre(e.player) } };
        }
        if (e.kind === 'game-end') {
          return e.anulado
            ? { kind: 'game-end', key: 'brisca.log.void', params: {} }
            : {
                kind: 'game-end',
                key: 'brisca.log.gameEnd',
                params: { a: e.scores[0], b: e.scores[1] ?? 0 },
              };
        }
        return { kind: 'match-end', key: 'brisca.log.matchEnd', params: { name: nombre(e.winner) } };
      })
      .slice(-10)
      .reverse();
  });

  readonly ganador = computed(() => {
    const s = this.estado();
    return s && s.winner !== null ? (s.players[s.winner]?.name ?? '') : '';
  });

  /** El resultado del juego que acaba de terminar (o `null` si sigue en marcha). */
  readonly resultado = computed(() => {
    const s = this.estado();
    if (!s || s.phase !== 'game-end') return null;
    const ultimo = [...s.events].reverse().find((e) => e.kind === 'game-end');
    return ultimo && ultimo.kind === 'game-end' ? ultimo : null;
  });

  constructor() {
    effect(() => {
      const s = this.estado();
      if (!s || s.phase !== 'playing') return;
      if (!s.players[s.turn]?.isBot) return;
      this.programarBot();
    });
  }

  ngOnDestroy(): void {
    this.limpiarTemporizador();
    // Al salir de la página hay que cerrar la sala: el servicio es único para toda la app,
    // así que si no se cierra, el servidor sigue contando a este jugador como conectado.
    if (this.modo() === 'online') this.salas.desconectar();
  }

  empezar(): void {
    this.modo.set('local');
    const n = this.jugadores();
    const nombres = ['Tú', ...Array.from({ length: n - 1 }, (_, i) => `Bot ${i + 1}`)];
    this.sonido.activar(this.sonidoActivo());
    this.sonido.repartir();
    this.estadoLocal.set(
      newGame({
        names: nombres,
        bots: nombres.map((_, i) => i !== 0),
        targetGames: this.juegosObjetivo(),
      }),
    );
    this.seleccion.set(null);
  }

  salir(): void {
    this.limpiarTemporizador();
    if (this.modo() === 'online') this.salas.desconectar();
    this.modo.set('menu');
    this.estadoLocal.set(null);
    this.seleccion.set(null);
  }

  toca(carta: Card): void {
    if (!this.miTurno()) return;
    this.sonido.tocar();
    this.seleccion.set(this.seleccion()?.id === carta.id ? null : carta);
  }

  estaSeleccionada(carta: Card): boolean {
    return this.seleccion()?.id === carta.id;
  }

  jugar(): void {
    const s = this.estado();
    const carta = this.seleccion();
    if (!s || !carta || !this.puedoJugar()) return;
    this.sonido.soltar();
    if (this.modo() === 'online') this.salas.accion({ action: 'play', card: carta.id });
    else this.estadoLocal.set(play(s, this.yo(), carta.id));
    this.seleccion.set(null);
  }

  cambiar(): void {
    const s = this.estado();
    if (!s || !this.puedoCambiar()) return;
    this.sonido.tocar();
    if (this.modo() === 'online') this.salas.accion({ action: 'swap' });
    else this.estadoLocal.set(cambiarTriunfo(s, this.yo()));
  }

  siguienteJuego(): void {
    const s = this.estado();
    if (!s) return;
    this.sonido.repartir();
    if (this.modo() === 'online') this.salas.accion({ action: 'next_game' });
    else this.estadoLocal.set(nextGame(s));
    this.seleccion.set(null);
  }

  // ── Bot ───────────────────────────────────────────────────────────────────

  private programarBot(): void {
    this.limpiarTemporizador();
    this.temporizador = setTimeout(() => {
      const s = this.estado();
      if (!s || s.phase !== 'playing' || !s.players[s.turn]?.isBot) return;
      const cartaId = botDecision(s, s.turn);
      if (!cartaId) return;
      // El bot, si puede, cambia el triunfo antes de jugar.
      let siguiente = s;
      if (puedeCambiarTriunfo(siguiente, s.turn)) siguiente = cambiarTriunfo(siguiente, s.turn);
      this.sonido.soltar();
      this.estadoLocal.set(play(siguiente, s.turn, cartaId));
    }, 900);
  }

  private limpiarTemporizador(): void {
    if (this.temporizador !== null) {
      clearTimeout(this.temporizador);
      this.temporizador = null;
    }
  }

  // ── Presentación ──────────────────────────────────────────────────────────

  codigo(carta: Card): string {
    return `${carta.rank}${carta.suit}`;
  }

  /** Fuerza de una carta, para ordenar o marcar la que va ganando. */
  fuerzaDe(carta: Card): number {
    return fuerza(carta);
  }

  puntosDe(carta: Card): number {
    return puntos(carta);
  }

  manoOrdenada(mano: Card[]): Card[] {
    return ordenarMano(mano);
  }

  alternarSonido(): void {
    const activo = !this.sonidoActivo();
    this.sonidoActivo.set(activo);
    this.sonido.activar(activo);
  }

  cerrarReglas(): void {
    this.reglasAbiertas.set(false);
  }
}
