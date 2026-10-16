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
import { Card, SpanishSuit } from '../../../core/games/baraja';
import { Baza, puntos } from '../../../core/games/bazas';
import {
  TuteState,
  acusesDisponibles,
  cantar,
  cantarTute,
  jugadasLegales,
  newGame,
  nextGame,
  play,
  tieneTute,
} from '../../../core/games/tute/tute-engine';
import { botDecision } from '../../../core/games/tute/tute-bots';
import { ButtonComponent } from '../../../shared/components/button/button';
import { FocoDialogoDirective } from '../../../shared/directives/foco-dialogo.directive';
import { PlayingCard } from '../../../shared/components/playing-card/playing-card';
import { GameSound } from '../../../core/audio/game-sound';
import { TuteVista, estadoDesdeVista } from '../../../core/games/tute/tute-online';
import { SalaOnlineService } from '../../../core/services/sala-online.service';
import { SalaLobby } from '../../../shared/components/sala-lobby/sala-lobby';

interface LogLine {
  kind: 'trick' | 'acuse' | 'tute' | 'game-end' | 'match-end';
  key: string;
  params: Record<string, string | number>;
}

/**
 * Mesa del Tute.
 *
 * Lo que la distingue de la brisca: aquí **estás obligado** a jugar de una manera concreta, así que
 * las cartas que no puedes jugar se ven apagadas. El motor dice cuáles son legales y la mesa lo
 * enseña, en vez de dejar que el jugador se equivoque y le salte un error.
 */
@Component({
  selector: 'app-tute',
  imports: [ButtonComponent, PlayingCard, RouterLink, SalaLobby, TranslatePipe, FocoDialogoDirective],
  templateUrl: './tute.html',
  styleUrl: './tute.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class Tute implements OnDestroy {
  private readonly sonido = inject(GameSound);

  readonly salas = inject(SalaOnlineService);

  /** Cómo se está jugando: contra bots o con amigos. */
  readonly modo = signal<'menu' | 'local' | 'online'>('menu');
  /** La partida de contra bots. */
  private readonly estadoLocal = signal<TuteState | null>(null);

  /** Lo que pinta la mesa: la partida local o la del servidor, adaptada a la misma forma. */
  readonly estado = computed(() => {
    if (this.modo() === 'online') {
      const vista = this.salas.sala()?.game as TuteVista | undefined;
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

  private temporizador: ReturnType<typeof setTimeout> | null = null;

  /** Mi asiento: en local es el 0; con amigos, el que me da el servidor. */
  readonly yo = computed(() => (this.modo() === 'online' ? (this.salas.seat() ?? 0) : 0));

  private ultimaBazaSonada: number | null = null;
  private finSonado = false;

  private readonly _sonidoBazas = effect(() => {
    const ganador = this.estado()?.lastWinner ?? null;
    if (ganador === null || ganador === this.ultimaBazaSonada) return;
    this.ultimaBazaSonada = ganador;
    if (ganador === this.yo()) this.sonido.baza();
    else this.sonido.tic();
  });

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

  /** Las cartas que la obligación de turno permite jugar ahora mismo. */
  readonly legales = computed<Card[]>(() => {
    const s = this.estado();
    return s ? jugadasLegales(s, this.yo()) : [];
  });

  readonly puedoJugar = computed(
    () => this.miTurno() && this.seleccion() !== null && this.esLegal(this.seleccion()!),
  );

  /** Acuses que puedo cantar ahora (rey y caballo del mismo palo, tras ganar una baza). */
  readonly acuses = computed<SpanishSuit[]>(() => {
    const s = this.estado();
    return s ? acusesDisponibles(s, this.yo()) : [];
  });

  readonly puedoTute = computed(() => {
    const s = this.estado();
    return !!s && tieneTute(s, this.yo());
  });

  /** Cuando ya no queda baceta, la obligación es más dura: hay que montar. */
  readonly obligaMontar = computed(() => (this.estado()?.baceta.length ?? 0) === 0);

  readonly marcador = computed(() =>
    (this.estado()?.players ?? []).map((p) => ({
      id: p.id,
      name: p.name,
      tantos: p.tantos ?? p.won.reduce((n, c) => n + puntos(c), 0),
      cantados: p.cantados,
      total: (this.estado()!.scores[p.id] ?? 0),
    })),
  );

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
        if (e.kind === 'acuse') {
          return {
            kind: 'acuse',
            key: e.cuarenta ? 'tute.log.cuarenta' : 'tute.log.veinte',
            params: { name: nombre(e.player) },
          };
        }
        if (e.kind === 'tute') {
          return { kind: 'tute', key: 'tute.log.tute', params: { name: nombre(e.player) } };
        }
        if (e.kind === 'game-end') {
          return {
            kind: 'game-end',
            key: 'tute.log.gameEnd',
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

  constructor() {
    effect(() => {
      const s = this.estado();
      // Con amigos los bots los lleva el servidor: aquí solo se juega en local.
      if (this.modo() !== 'local') return;
      if (!s || s.phase !== 'playing') return;
      if (!s.players.some((p) => p.isBot)) return;
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
      newGame({ names: nombres, bots: nombres.map((_, i) => i !== 0) }),
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

  esLegal(carta: Card): boolean {
    return this.legales().some((c) => c.id === carta.id);
  }

  toca(carta: Card): void {
    if (!this.miTurno() || !this.esLegal(carta)) return;
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

  cantarAcuse(suit: SpanishSuit): void {
    const s = this.estado();
    if (!s) return;
    this.sonido.tocar();
    if (this.modo() === 'online') this.salas.accion({ action: 'sing', suit });
    else this.estadoLocal.set(cantar(s, this.yo(), suit));
  }

  cantarElTute(): void {
    const s = this.estado();
    if (!s) return;
    this.sonido.finDeRonda();
    if (this.modo() === 'online') this.salas.accion({ action: 'tute' });
    else this.estadoLocal.set(cantarTute(s, this.yo()));
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
      if (!s || s.phase !== 'playing') return;
      // Se busca un bot con algo que hacer (puede cantar fuera de su turno).
      const asiento = s.players.findIndex((p, i) => p.isBot && botDecision(s, i) !== null);
      if (asiento === -1) return;
      const decision = botDecision(s, asiento);
      if (!decision) return;
      if (decision.action === 'tute') {
        this.sonido.finDeRonda();
        this.estadoLocal.set(cantarTute(s, asiento));
      } else if (decision.action === 'sing') {
        this.sonido.tocar();
        this.estadoLocal.set(cantar(s, asiento, decision.suit as SpanishSuit));
      } else {
        this.sonido.soltar();
        this.estadoLocal.set(play(s, asiento, decision.cardId));
      }
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

  puntosDe(carta: Card): number {
    return puntos(carta);
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
