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
import { Card, SpanishRank } from '../../../core/games/baraja';
import {
  MentirosoState,
  desconfiar,
  newGame,
  nextHand,
  play,
  retirar,
} from '../../../core/games/mentiroso/mentiroso-engine';
import { botDecision } from '../../../core/games/mentiroso/mentiroso-bots';
import {
  MentirosoVista,
  estadoDesdeVista,
} from '../../../core/games/mentiroso/mentiroso-online';
import { SalaOnlineService } from '../../../core/services/sala-online.service';
import { ButtonComponent } from '../../../shared/components/button/button';
import { FocoDialogoDirective } from '../../../shared/directives/foco-dialogo.directive';
import { SalaLobby } from '../../../shared/components/sala-lobby/sala-lobby';
import { PlayingCard } from '../../../shared/components/playing-card/playing-card';
import { GameSound } from '../../../core/audio/game-sound';

/** Una línea del registro de la mesa, ya resuelta para pintarla. */
interface LogLine {
  kind: 'play' | 'challenge' | 'take' | 'retire' | 'out';
  key: string;
  params: Record<string, string | number>;
  /** Clave de traducción del valor de la carta, cuando la línea habla de uno. */
  rankKey?: string;
}

/**
 * Mesa del Mentiroso.
 *
 * El componente no sabe de reglas: se las pide al motor (`core/games/mentiroso`) y pinta el
 * estado que le devuelve. Los bots juegan solos, con una pausa entre turnos para que se
 * pueda seguir la partida.
 */
@Component({
  selector: 'app-mentiroso',
  imports: [ButtonComponent, PlayingCard, RouterLink, SalaLobby, TranslatePipe, FocoDialogoDirective],
  templateUrl: './mentiroso.html',
  styleUrl: './mentiroso.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class Mentiroso implements OnDestroy {
  private readonly sonido = inject(GameSound);

  readonly salas = inject(SalaOnlineService);

  /** Cómo se está jugando: contra bots o con amigos. */
  readonly modo = signal<'menu' | 'local' | 'online'>('menu');
  /** La partida de contra bots. */
  private readonly estadoLocal = signal<MentirosoState | null>(null);

  /**
   * Lo que pinta la mesa: la partida local o la que manda el servidor, adaptada a la misma forma.
   * Así el modo «con amigos» reutiliza la mesa en vez de tener una pantalla paralela.
   */
  readonly estado = computed(() => {
    if (this.modo() === 'online') {
      const vista = this.salas.sala()?.game as MentirosoVista | undefined;
      const seat = this.salas.seat();
      return vista && seat !== null ? estadoDesdeVista(vista, seat) : null;
    }
    return this.estadoLocal();
  });

  readonly seleccion = signal<Card[]>([]);
  readonly valorElegido = signal<SpanishRank | null>(null);
  readonly reglasAbiertas = signal(false);
  /** Arranca como lo dejara el jugador: el silencio se recuerda. */
  readonly sonidoActivo = signal(this.sonido.encendido);

  // Ajustes de la partida.
  readonly jugadores = signal(4);
  readonly manosObjetivo = signal(3);

  private temporizador: ReturnType<typeof setTimeout> | null = null;

  /** Mi asiento: en local es el 0; con amigos, el que me da el servidor. */
  readonly yo = computed(() => (this.modo() === 'online' ? (this.salas.seat() ?? 0) : 0));

  private finSonado = false;

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

  readonly rivales = computed(() =>
    (this.estado()?.players ?? []).filter((p) => p.id !== this.yo()),
  );

  /** Lo que hay que decir: el valor de la mesa, o el que yo elija si abro la ronda. */
  readonly valorEnJuego = computed(() => {
    const s = this.estado();
    if (!s) return null;
    return s.claimedRank ?? this.valorElegido();
  });

  /** ¿Puedo poner? Necesito cartas elegidas y un valor que decir. */
  readonly puedoPoner = computed(
    () => this.miTurno() && this.seleccion().length > 0 && this.valorEnJuego() !== null,
  );

  /** ¿Puedo desconfiar? Solo de lo último que puso otro que siga con cartas. */
  readonly puedoDesconfiar = computed(() => {
    const s = this.estado();
    if (!s || s.phase !== 'playing' || !s.lastPlay) return false;
    if (s.lastPlay.player === this.yo()) return false;
    return s.players[s.lastPlay.player].hand.length > 0;
  });

  /** El valor del que tengo las cuatro cartas, si es que lo tengo. */
  readonly cuatroIguales = computed<SpanishRank | null>(() => {
    const cuenta = new Map<SpanishRank, number>();
    for (const carta of this.miMano()) cuenta.set(carta.rank, (cuenta.get(carta.rank) ?? 0) + 1);
    for (const [valor, n] of cuenta) if (n === 4) return valor;
    return null;
  });

  readonly registro = computed<LogLine[]>(() => {
    const s = this.estado();
    if (!s) return [];
    const nombre = (id: number) => s.players[id]?.name ?? '';
    return s.events
      .map((e): LogLine => {
        if (e.kind === 'play') {
          return {
            kind: 'play',
            key: 'mentiroso.log.play',
            params: { name: nombre(e.player), count: e.count },
            rankKey: `baraja.rank.${e.claimedRank}`,
          };
        }
        if (e.kind === 'challenge') {
          return {
            kind: 'challenge',
            key: 'mentiroso.log.challenge',
            params: { name: nombre(e.player), other: nombre(e.against) },
          };
        }
        if (e.kind === 'take') {
          return {
            kind: 'take',
            key: e.mentira ? 'mentiroso.log.lie' : 'mentiroso.log.true',
            params: { name: nombre(e.player), count: e.count },
          };
        }
        if (e.kind === 'retire') {
          return {
            kind: 'retire',
            key: 'mentiroso.log.retire',
            params: { name: nombre(e.player) },
            rankKey: `baraja.rank.${e.rank}`,
          };
        }
        return { kind: 'out', key: 'mentiroso.log.out', params: { name: nombre(e.player) } };
      })
      .slice(-12)
      .reverse();
  });

  readonly ganador = computed(() => {
    const s = this.estado();
    return s && s.winner !== null ? (s.players[s.winner]?.name ?? '') : '';
  });

  constructor() {
    // Si le toca a un bot, se le da un respiro y juega.
    effect(() => {
      const s = this.estado();
      // Con amigos los bots los lleva el servidor: aquí solo se juega en local.
      if (this.modo() !== 'local') return;
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

  // ── Empezar y salir ───────────────────────────────────────────────────────

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
        targetWins: this.manosObjetivo(),
      }),
    );
    this.seleccion.set([]);
    this.valorElegido.set(null);
  }

  salir(): void {
    this.limpiarTemporizador();
    if (this.modo() === 'online') this.salas.desconectar();
    this.modo.set('menu');
    this.estadoLocal.set(null);
    this.seleccion.set([]);
    this.valorElegido.set(null);
  }

  // ── Jugar ─────────────────────────────────────────────────────────────────

  toca(carta: Card): void {
    if (!this.miTurno()) return;
    const actual = this.seleccion();
    this.sonido.tocar();
    if (actual.some((c) => c.id === carta.id)) {
      this.seleccion.set(actual.filter((c) => c.id !== carta.id));
      return;
    }
    this.seleccion.set([...actual, carta]);
  }

  estaSeleccionada(carta: Card): boolean {
    return this.seleccion().some((c) => c.id === carta.id);
  }

  /** Poner las cartas elegidas diciendo lo que toca. */
  poner(): void {
    const s = this.estado();
    const valor = this.valorEnJuego();
    if (!s || !this.puedoPoner() || valor === null) return;
    this.sonido.soltar();
    if (this.modo() === 'online') {
      // El servidor decide: aquí solo se pide.
      this.salas.accion({
        action: 'play',
        cards: this.seleccion().map((c) => c.id),
        claimedRank: valor,
      });
    } else {
      this.estadoLocal.set(play(s, this.yo(), this.seleccion().map((c) => c.id), valor));
    }
    this.seleccion.set([]);
    this.valorElegido.set(null);
  }

  /** Gritar «¡mentiroso!». */
  gritar(): void {
    const s = this.estado();
    if (!s || !this.puedoDesconfiar()) return;
    this.sonido.pasar();
    if (this.modo() === 'online') this.salas.accion({ action: 'challenge' });
    else this.estadoLocal.set(desconfiar(s, this.yo()));
    this.seleccion.set([]);
  }

  /** Enseñar los cuatro iguales y sacarlos del juego. */
  retirarCuatro(): void {
    const s = this.estado();
    const valor = this.cuatroIguales();
    if (!s || valor === null) return;
    this.sonido.soltar();
    if (this.modo() === 'online') this.salas.accion({ action: 'retire', rank: valor });
    else this.estadoLocal.set(retirar(s, this.yo(), valor));
    this.seleccion.set([]);
  }

  elegirValor(rank: SpanishRank): void {
    this.valorElegido.set(rank);
  }

  // ── Entre manos ───────────────────────────────────────────────────────────

  siguienteMano(): void {
    const s = this.estado();
    if (!s) return;
    this.sonido.repartir();
    if (this.modo() === 'online') this.salas.accion({ action: 'next_hand' });
    else this.estadoLocal.set(nextHand(s));
    this.seleccion.set([]);
    this.valorElegido.set(null);
  }

  // ── Bots ──────────────────────────────────────────────────────────────────

  private programarBot(): void {
    this.limpiarTemporizador();
    this.temporizador = setTimeout(() => {
      const s = this.estado();
      if (!s || s.phase !== 'playing' || !s.players[s.turn]?.isBot) return;
      const decision = botDecision(s, s.turn);
      if (!decision) return;
      if (decision.action === 'retire') {
        this.estadoLocal.set(retirar(s, s.turn, decision.rank as SpanishRank));
      } else if (decision.action === 'challenge') {
        this.sonido.pasar();
        this.estadoLocal.set(desconfiar(s, s.turn));
      } else {
        this.sonido.soltar();
        this.estadoLocal.set(
          play(s, s.turn, decision.cardIds, decision.claimedRank as SpanishRank),
        );
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

  /** Los valores, de menor a mayor, para elegir qué decir al abrir. */
  readonly valores: SpanishRank[] = [1, 2, 3, 4, 5, 6, 7, 10, 11, 12];

  /** Código de la carta tal y como se llama su PNG ("5o", "1e", "12b"). */
  codigo(carta: Card): string {
    return `${carta.rank}${carta.suit}`;
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
