import {
  ChangeDetectionStrategy,
  Component,
  OnDestroy,
  computed,
  effect,
  inject,
  signal,
} from '@angular/core';

import { Router, RouterLink } from '@angular/router';

import { TranslatePipe } from '../../../i18n';
import { Card, SpanishRank, sortHand, strength } from '../../../core/games/culo/culo-deck';
import {
  GameState,
  comboOf,
  canBeat,
  exchangeSwaps,
  legalCombos,
  nextRoundWithSwaps,
  newGame,
  pass,
  play,
  roleKey,
  standings,
} from '../../../core/games/culo/culo-engine';
import { botDecision } from '../../../core/games/culo/culo-bots';
import { CuloOnlineService } from '../../../core/services/culo-online.service';
import { ButtonComponent } from '../../../shared/components/button/button';
import { FocoDialogoDirective } from '../../../shared/directives/foco-dialogo.directive';
import { PixelTitleComponent } from '../../../shared/components/pixel-title/pixel-title';
import { PlayingCard } from '../../../shared/components/playing-card/playing-card';
import { GameSound } from '../../../core/audio/game-sound';

/** Lo que se ve en el registro de la mesa. */
interface LogLine {
  kind: 'play' | 'pass' | 'trick' | 'out';
  player: string;
  count?: number;
  strength?: number;
  place?: number;
}

/** Cómo se está jugando: en local contra bots o en una sala con amigos. */
export type ModoCulo = 'menu' | 'local' | 'online';

/**
 * Mesa del Culo (Presidente), en sus dos formas.
 *
 * En **local** las reglas las aplica el motor del navegador y los bots juegan aquí. En
 * **online** manda el servidor: se manda lo que el jugador pide y se pinta lo que llega.
 * La mesa es la misma en los dos casos porque el estado se normaliza a la misma forma,
 * así que no hay dos interfaces que mantener.
 */
@Component({
  selector: 'app-culo',
  imports: [ButtonComponent, PixelTitleComponent, PlayingCard, RouterLink, TranslatePipe, FocoDialogoDirective],
  templateUrl: './culo.html',
  styleUrl: './culo.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class Culo implements OnDestroy {
  private readonly sonido = inject(GameSound);
  private readonly router = inject(Router);
  readonly online = inject(CuloOnlineService);

  readonly modo = signal<ModoCulo>('menu');
  private readonly estadoLocal = signal<GameState | null>(null);

  /** El estado de la mesa, venga del motor local o del servidor. */
  readonly estado = computed<GameState | null>(() =>
    this.modo() === 'online' ? this.online.estado() : this.estadoLocal(),
  );

  readonly seleccion = signal<Card[]>([]);
  readonly reglasAbiertas = signal(false);
  /** Arranca como lo dejara el jugador: el silencio se recuerda. */
  readonly sonidoActivo = signal(this.sonido.encendido);

  // Ajustes del modo local.
  readonly jugadores = signal(4);
  readonly barajas = signal<1 | 2>(1);

  // Sala online.
  readonly codigoSala = signal('');
  readonly codigoEntrada = signal('');
  readonly creando = signal(false);
  readonly copiado = signal(false);
  readonly sala = computed(() => this.online.room());
  readonly soyAnfitrion = computed(() =>
    this.modo() === 'online' ? !!this.online.room()?.isHost : true,
  );

  /** Mi asiento: en local soy el 0; online lo dice el servidor. */
  readonly yo = computed(() => (this.modo() === 'online' ? (this.online.seat() ?? 0) : 0));

  private temporizador: ReturnType<typeof setTimeout> | null = null;

  readonly miTurno = computed(() => {
    const s = this.estado();
    return !!s && s.phase === 'playing' && s.turn === this.yo();
  });

  readonly miMano = computed(() => this.estado()?.players[this.yo()]?.hand ?? []);

  /** ¿La selección actual es una jugada legal? */
  readonly jugadaValida = computed(() => {
    const s = this.estado();
    const cartas = this.seleccion();
    if (!s || cartas.length === 0) return false;
    const jugada = comboOf(cartas);
    return jugada !== null && canBeat(jugada, s.table);
  });

  /** Los demás jugadores, para ponerlos alrededor de la mesa. */
  readonly rivales = computed(() =>
    (this.estado()?.players ?? []).filter((p) => p.id !== this.yo()),
  );

  readonly clasificacion = computed(() => {
    const s = this.estado();
    return s && s.phase === 'round-end' ? standings(s) : [];
  });

  readonly intercambios = computed(() => {
    const s = this.estado();
    return s && s.phase === 'round-end' ? exchangeSwaps(s) : [];
  });

  readonly registro = computed<LogLine[]>(() => {
    const s = this.estado();
    if (!s) return [];
    const nombre = (id: number) => s.players[id]?.name ?? '';
    return s.events
      .map((e): LogLine => {
        if (e.kind === 'play') {
          return { kind: 'play', player: nombre(e.player), count: e.count, strength: e.strength };
        }
        if (e.kind === 'pass') return { kind: 'pass', player: nombre(e.player) };
        if (e.kind === 'out') return { kind: 'out', player: nombre(e.player), place: e.place };
        return { kind: 'trick', player: nombre(e.player) };
      })
      .slice(-14)
      .reverse();
  });

  constructor() {
    // Solo en local: si le toca a un bot, se le da un respiro y juega. Online los mueve
    // el servidor, que es quien manda.
    effect(() => {
      const s = this.estadoLocal();
      if (this.modo() !== 'local' || !s || s.phase !== 'playing') return;
      if (!s.players[s.turn]?.isBot) return;
      this.programarBot();
    });

    // Enlace compartido: /culo?codigo=ABCD entra directo en la sala.
    if (typeof window !== 'undefined') {
      const codigo = new URLSearchParams(window.location.search).get('codigo');
      if (codigo) {
        this.codigoEntrada.set(codigo.toUpperCase());
        void this.entrarSala();
      }
    }
  }

  ngOnDestroy(): void {
    this.limpiarTemporizador();
    this.online.desconectar();
  }

  // ── Partida ───────────────────────────────────────────────────────────────

  jugarLocal(): void {
    const n = this.jugadores();
    const nombres = ['Tú', ...Array.from({ length: n - 1 }, (_, i) => `Bot ${i + 1}`)];
    this.sonido.activar(this.sonidoActivo());
    this.sonido.repartir();
    this.modo.set('local');
    this.estadoLocal.set(
      newGame({ names: nombres, bots: nombres.map((_, i) => i !== 0), decks: this.barajas() }),
    );
    this.seleccion.set([]);
  }

  async crearSala(): Promise<void> {
    this.creando.set(true);
    this.online.limpiarError();
    try {
      const codigo = await this.online.crear(this.barajas());
      this.codigoSala.set(codigo);
      this.modo.set('online');
      this.sonido.activar(this.sonidoActivo());
      this.apuntarCodigoEnLaUrl(codigo);
      this.online.conectar(codigo);
    } catch {
      this.online.error.set('culo.online.errorCrear');
    } finally {
      this.creando.set(false);
    }
  }

  async entrarSala(): Promise<void> {
    const codigo = this.codigoEntrada().trim().toUpperCase();
    if (codigo.length < 4) return;
    this.online.limpiarError();
    try {
      await this.online.mirar(codigo);
      this.codigoSala.set(codigo);
      this.modo.set('online');
      this.sonido.activar(this.sonidoActivo());
      this.apuntarCodigoEnLaUrl(codigo);
      this.online.conectar(codigo);
    } catch {
      this.online.error.set('culo.online.salaNoExiste');
    }
  }

  /**
   * Deja el código en la barra de direcciones (sin recargar ni ensuciar el historial).
   *
   * Así, si el navegador recarga la página —en el móvil pasa solo, al volver de segundo
   * plano—, el jugador vuelve directo a **su** partida en vez de al menú: el arranque del
   * componente lee el código de la URL y entra solo.
   */
  private apuntarCodigoEnLaUrl(codigo: string): void {
    void this.router.navigate([], {
      queryParams: { codigo },
      queryParamsHandling: 'merge',
      replaceUrl: true,
    });
  }

  /** Volver a entrar tras una caída de la conexión, sin salir de la mesa. */
  reconectar(): void {
    if (this.codigoSala()) this.online.conectar(this.codigoSala());
  }

  /** El enlace para pasarle a un amigo (o el código, que se dicta). */
  get enlaceSala(): string {
    if (typeof window === 'undefined') return '';
    return `${window.location.origin}/culo?codigo=${this.codigoSala()}`;
  }

  async copiarEnlace(): Promise<void> {
    try {
      await navigator.clipboard.writeText(this.enlaceSala);
      this.copiado.set(true);
      setTimeout(() => this.copiado.set(false), 1800);
    } catch {
      // Sin permiso de portapapeles no pasa nada: el código se puede dictar.
    }
  }

  salir(): void {
    this.limpiarTemporizador();
    if (this.modo() === 'online') this.online.desconectar();
    this.estadoLocal.set(null);
    this.modo.set('menu');
    this.seleccion.set([]);
    this.codigoSala.set('');
    this.codigoEntrada.set('');
    void this.router.navigate([], { queryParams: {}, replaceUrl: true });
  }

  // ── Jugar cartas ──────────────────────────────────────────────────────────

  toca(carta: Card): void {
    if (!this.miTurno()) return;
    const actual = this.seleccion();
    const yaEsta = actual.some((c) => c.id === carta.id);
    if (yaEsta) {
      this.seleccion.set(actual.filter((c) => c.id !== carta.id));
      return;
    }
    // Al mezclar valores distintos, se empieza una jugada nueva con la carta tocada.
    const mismoValor =
      actual.length === 0 || actual.every((c) => strength(c) === strength(carta));
    const nueva = mismoValor ? [...actual, carta] : [carta];
    this.sonido.tocar();
    this.seleccion.set(sortHand(nueva));
  }

  estaSeleccionada(carta: Card): boolean {
    return this.seleccion().some((c) => c.id === carta.id);
  }

  jugar(): void {
    const s = this.estado();
    if (!s || !this.jugadaValida()) return;
    const cartas = this.seleccion();
    this.sonido.soltar();
    if (this.modo() === 'online') {
      this.online.jugar(cartas);
    } else {
      this.estadoLocal.set(play(s, 0, cartas));
      this.comprobarFinal();
    }
    this.seleccion.set([]);
  }

  pasar(): void {
    const s = this.estado();
    if (!s || !this.miTurno()) return;
    this.sonido.pasar();
    if (this.modo() === 'online') {
      this.online.pasar();
    } else {
      this.estadoLocal.set(pass(s, 0));
    }
    this.seleccion.set([]);
  }

  /** Pistas: cuántas jugadas distintas puede hacer ahora mismo. */
  readonly jugadasPosibles = computed(() => {
    const s = this.estado();
    return s && this.miTurno() ? legalCombos(s, this.yo()).length : 0;
  });

  // ── Rondas ────────────────────────────────────────────────────────────────

  siguienteRonda(): void {
    if (this.modo() === 'online') {
      this.online.siguienteRonda();
      return;
    }
    const s = this.estadoLocal();
    if (!s) return;
    this.sonido.repartir();
    // Reparte y después intercambia (el orden contrario dejaba el intercambio en nada).
    this.estadoLocal.set(nextRoundWithSwaps(s));
    this.seleccion.set([]);
  }

  repartir(): void {
    this.sonido.repartir();
    this.online.repartir();
  }

  anadirBot(): void {
    this.online.anadirBot();
  }

  quitarBot(): void {
    this.online.quitarBot();
  }

  // ── Bots ──────────────────────────────────────────────────────────────────

  private programarBot(): void {
    this.limpiarTemporizador();
    this.temporizador = setTimeout(() => {
      const s = this.estadoLocal();
      if (this.modo() !== 'local' || !s || s.phase !== 'playing') return;
      if (!s.players[s.turn]?.isBot) return;
      const decision = botDecision(s, s.turn);
      if (decision) this.sonido.soltar();
      else this.sonido.pasar();
      this.estadoLocal.set(decision ? play(s, s.turn, decision.cards) : pass(s, s.turn));
      this.comprobarFinal();
    }, 950);
  }

  private limpiarTemporizador(): void {
    if (this.temporizador !== null) {
      clearTimeout(this.temporizador);
      this.temporizador = null;
    }
  }

  private comprobarFinal(): void {
    if (this.estadoLocal()?.phase === 'round-end') this.sonido.finDeRonda();
  }

  // ── Presentación ──────────────────────────────────────────────────────────

  rolClave = roleKey;

  /** Los valores, de menor a mayor, para el panel de reglas. */
  readonly valores: SpanishRank[] = [2, 3, 4, 5, 6, 7, 10, 11, 12, 1];

  /** Código de la carta tal y como se llama su PNG ("5o", "1e", "12b"). */
  codigo(carta: Card): string {
    return `${carta.rank}${carta.suit}`;
  }

  /** Cuántas cartas tiene un jugador (online solo llega el número, no las cartas). */
  cartasDe(jugador: { hand: Card[]; handCount?: number }): number {
    return jugador.handCount ?? jugador.hand.length;
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
