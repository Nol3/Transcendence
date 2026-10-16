import { ChangeDetectionStrategy, Component, OnDestroy, computed, effect, inject, signal } from '@angular/core';

import { RouterLink } from '@angular/router';

import { TranslatePipe } from '../../../i18n';
import { Card } from '../../../core/games/baraja';
import {
  JUGADORES,
  LANCES,
  Lance,
  MusState,
  cortarMus,
  decirMus,
  descartar,
  envidar,
  newGame,
  nextHand,
  noQuiero,
  ordago,
  parejaDe,
  pasar,
  quiero,
  turnoActual,
} from '../../../core/games/mus/mus-engine';
import { botDecision } from '../../../core/games/mus/mus-bots';
import { ButtonComponent } from '../../../shared/components/button/button';
import { FocoDialogoDirective } from '../../../shared/directives/foco-dialogo.directive';
import { PlayingCard } from '../../../shared/components/playing-card/playing-card';
import { GameSound } from '../../../core/audio/game-sound';
import { MusVista, estadoDesdeVista } from '../../../core/games/mus/mus-online';
import { SalaOnlineService } from '../../../core/services/sala-online.service';
import { SalaLobby } from '../../../shared/components/sala-lobby/sala-lobby';

interface LogLine {
  kind: string;
  key: string;
  params: Record<string, string | number>;
}

/**
 * Mesa del Mus.
 *
 * Es la más distinta de las cuatro: aquí no se juega una carta contra otra, sino que se **apuesta**
 * sobre lo que cada pareja tiene en la mano. Por eso la mesa enseña tu jugada (y la de tu
 * compañero, que es lo que en la mesa real se dicen por señas) y los botones de envite.
 */
@Component({
  selector: 'app-mus',
  imports: [ButtonComponent, PlayingCard, RouterLink, SalaLobby, TranslatePipe, FocoDialogoDirective],
  templateUrl: './mus.html',
  styleUrl: './mus.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class Mus implements OnDestroy {
  private readonly sonido = inject(GameSound);

  readonly salas = inject(SalaOnlineService);

  /** Cómo se está jugando: contra bots o con amigos. */
  readonly modo = signal<'menu' | 'local' | 'online'>('menu');
  /** La partida de contra bots. */
  private readonly estadoLocal = signal<MusState | null>(null);

  /** Lo que pinta la mesa: la partida local o la del servidor, adaptada a la misma forma. */
  readonly estado = computed(() => {
    if (this.modo() === 'online') {
      const vista = this.salas.sala()?.game as MusVista | undefined;
      const seat = this.salas.seat();
      return vista && seat !== null ? estadoDesdeVista(vista, seat) : null;
    }
    return this.estadoLocal();
  });
  readonly reglasAbiertas = signal(false);
  /** Arranca como lo dejara el jugador: el silencio se recuerda. */
  readonly sonidoActivo = signal(this.sonido.encendido);
  /** Las cartas marcadas para descartar. */
  readonly aDescartar = signal<string[]>([]);
  /** Cuántas piedras se envida. */
  readonly envite = signal(2);

  private temporizador: ReturnType<typeof setTimeout> | null = null;

  /** Mi asiento: en local es el 0; con amigos, el que me da el servidor. */
  readonly yo = computed(() => (this.modo() === 'online' ? (this.salas.seat() ?? 0) : 0));

  private finSonado = false;

  private readonly _sonidoFinal = effect(() => {
    const s = this.estado();
    if (!s || s.phase !== 'vaca-end' || this.finSonado) return;
    this.finSonado = true;
    if (s.winner === parejaDe(this.yo())) this.sonido.victoria();
    else this.sonido.derrota();
  });

  readonly turno = computed(() => (this.estado() ? turnoActual(this.estado()!) : null));
  readonly miTurno = computed(() => this.turno() === this.yo());
  readonly fase = computed(() => this.estado()?.phase ?? 'mus');
  readonly lance = computed<Lance | null>(() => this.estado()?.lance ?? null);
  readonly miMano = computed(() => this.estado()?.players[this.yo()]?.hand ?? []);
  readonly miJugada = computed(() => this.estado()?.players[this.yo()]?.jugada ?? null);

  /** La jugada de mi compañero: en la mesa real se diría por señas. */
  readonly companero = computed(() => {
    const s = this.estado();
    if (!s) return null;
    const id = s.teams[parejaDe(this.yo())].players.find((p) => p !== this.yo()) ?? null;
    return id === null ? null : { nombre: s.players[id].name, jugada: s.players[id].jugada };
  });

  readonly marcador = computed(() =>
    (this.estado()?.teams ?? []).map((t) => ({
      id: t.id,
      mia: t.id === parejaDe(this.yo()),
      piedras: t.piedras,
      juegos: t.juegos,
      nombres: t.players.map((p) => this.estado()!.players[p].name).join(' y '),
    })),
  );

  readonly enviteVivo = computed(() => this.estado()?.envite ?? null);
  readonly meTocaResponder = computed(() => this.estado()?.responde === this.yo());

  readonly registro = computed<LogLine[]>(() => {
    const s = this.estado();
    if (!s) return [];
    const nombre = (id: number) => s.players[id]?.name ?? '';
    return s.events
      .filter((e) => e.kind !== 'deal')
      .map((e): LogLine => {
        if (e.kind === 'mus') {
          return { kind: 'mus', key: 'mus.log.mus', params: { name: nombre(e.player) } };
        }
        if (e.kind === 'cortar') {
          return { kind: 'cortar', key: 'mus.log.cortar', params: { name: nombre(e.player) } };
        }
        if (e.kind === 'descartar') {
          return {
            kind: 'descartar',
            key: 'mus.log.descartar',
            params: { name: nombre(e.player), n: e.cuantas },
          };
        }
        if (e.kind === 'envite') {
          return {
            kind: 'envite',
            key: `mus.log.${e.apuesta}`,
            params: { name: nombre(e.player), n: e.cuantas },
          };
        }
        if (e.kind === 'lance') {
          return {
            kind: 'lance',
            key: `mus.log.lance.${e.lance}`,
            params: {
              team: s.teams[e.team].players.map(nombre).join(' y '),
              n: e.piedras,
            },
          };
        }
        if (e.kind === 'nadie') {
          return { kind: 'nadie', key: `mus.log.nadie.${e.lance}`, params: {} };
        }
        if (e.kind === 'game-end') {
          return { kind: 'game-end', key: 'mus.log.gameEnd', params: { team: e.team + 1 } };
        }
        return { kind: 'vaca', key: 'mus.log.vaca', params: { team: e.team + 1 } };
      })
      .slice(-12)
      .reverse();
  });

  constructor() {
    effect(() => {
      const s = this.estado();
      // Con amigos los bots los lleva el servidor: aquí solo se juega en local.
      if (this.modo() !== 'local') return;
      if (!s || s.phase === 'vaca-end') return;
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
    const nombres = ['Tú', 'Bot 1', 'Compañero', 'Bot 2'];
    // Las parejas son 0 y 2 contra 1 y 3: tú juegas con «Compañero».
    this.sonido.activar(this.sonidoActivo());
    this.sonido.repartir();
    this.estadoLocal.set(newGame({ names: nombres, bots: nombres.map((n) => n !== 'Tú' && n !== 'Compañero') }));
    this.aDescartar.set([]);
  }

  salir(): void {
    this.limpiarTemporizador();
    if (this.modo() === 'online') this.salas.desconectar();
    this.modo.set('menu');
    this.estadoLocal.set(null);
  }

  decirMus(): void {
    this.aplicar((s) => decirMus(s, this.yo()), { action: 'mus' });
  }

  cortar(): void {
    this.aplicar((s) => cortarMus(s, this.yo()), { action: 'cortar' });
  }

  toca(carta: Card): void {
    if (this.fase() !== 'descartar' || !this.miTurno()) return;
    const marcadas = this.aDescartar();
    this.sonido.tocar();
    this.aDescartar.set(
      marcadas.includes(carta.id) ? marcadas.filter((id) => id !== carta.id) : [...marcadas, carta.id],
    );
  }

  estaMarcada(carta: Card): boolean {
    return this.aDescartar().includes(carta.id);
  }

  descartarCartas(): void {
    const marcadas = this.aDescartar();
    if (marcadas.length === 0) return;
    this.sonido.repartir();
    this.aplicar((s) => descartar(s, this.yo(), marcadas), {
      action: 'descartar',
      cards: marcadas,
    });
    this.aDescartar.set([]);
  }

  pasar(): void {
    this.aplicar((s) => pasar(s, this.yo()), { action: 'pasar' });
  }

  envidar(): void {
    this.aplicar((s) => envidar(s, this.yo(), this.envite()), {
      action: 'envidar',
      cuantas: this.envite(),
    });
  }

  cantarOrdago(): void {
    this.sonido.finDeRonda();
    this.aplicar((s) => ordago(s, this.yo()), { action: 'ordago' });
  }

  querer(): void {
    this.aplicar((s) => quiero(s, this.yo()), { action: 'quiero' });
  }

  noQuerer(): void {
    this.aplicar((s) => noQuiero(s, this.yo()), { action: 'no_quiero' });
  }

  repartirMano(): void {
    this.sonido.repartir();
    this.aplicar((s) => nextHand(s), { action: 'next_hand' });
  }

  // ── Bot ───────────────────────────────────────────────────────────────────

  /**
   * Aplica un movimiento: en local lo hace el motor y con amigos lo pide al servidor (que es el
   * que manda). Cada acción trae las dos versiones para no duplicar los métodos.
   */
  private aplicar(cambio: (s: MusState) => MusState, accion?: Record<string, unknown>): void {
    const s = this.estado();
    if (!s) return;
    if (this.modo() === 'online' && accion) {
      this.salas.accion(accion);
      return;
    }
    this.estadoLocal.set(cambio(s));
  }

  private programarBot(): void {
    this.limpiarTemporizador();
    this.temporizador = setTimeout(() => {
      const s = this.estado();
      if (!s || s.phase === 'vaca-end') return;
      const asiento = s.players.findIndex((p, i) => p.isBot && botDecision(s, i) !== null);
      if (asiento === -1) return;
      const d = botDecision(s, asiento);
      if (!d) return;
      this.estadoLocal.set(this.aplicarDecision(s, asiento, d));
    }, 850);
  }

  private aplicarDecision(
    s: MusState,
    asiento: number,
    d: NonNullable<ReturnType<typeof botDecision>>,
  ): MusState {
    switch (d.action) {
      case 'mus':
        return decirMus(s, asiento);
      case 'cortar':
        return cortarMus(s, asiento);
      case 'descartar':
        return descartar(s, asiento, d.cardIds);
      case 'pasar':
        return pasar(s, asiento);
      case 'envidar':
        return envidar(s, asiento, d.cuantas);
      case 'ordago':
        return ordago(s, asiento);
      case 'quiero':
        return quiero(s, asiento);
      default:
        return noQuiero(s, asiento);
    }
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

  nombreLance(l: Lance): string {
    return `mus.lance.${l}`;
  }

  /** El valor de una carta para el juego, para enseñarlo en la mano. */
  valor(carta: Card): number {
    return carta.rank === 12 || carta.rank === 11 || carta.rank === 10 ? 10 : carta.rank;
  }

  alternarSonido(): void {
    const activo = !this.sonidoActivo();
    this.sonidoActivo.set(activo);
    this.sonido.activar(activo);
  }

  cerrarReglas(): void {
    this.reglasAbiertas.set(false);
  }

  protected readonly lances = LANCES;
  protected readonly jugadores = JUGADORES;
}
