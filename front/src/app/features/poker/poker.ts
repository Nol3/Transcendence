import { Component, OnDestroy, computed, effect, inject, signal, untracked } from '@angular/core';
import { ActivatedRoute, ParamMap, Router, RouterLink } from '@angular/router';
import { Subscription } from 'rxjs';
import { PokerService, StakeKey } from '../../core/services/poker.service';
import { BadgeComponent } from '../../shared/components/badge/badge';
import { ButtonComponent } from '../../shared/components/button/button';
import { CardComponent } from '../../shared/components/card/card';
import { PixelTitleComponent } from '../../shared/components/pixel-title/pixel-title';
import { PlayingCard } from '../../shared/components/playing-card/playing-card';
import { TranslatePipe } from '../../i18n';
import { I18nService } from '../../i18n';

const STAKE_KEYS: StakeKey[] = ['micro', 'low', 'mid'];

@Component({
  selector: 'app-poker',
  standalone: true,
  imports: [BadgeComponent, ButtonComponent, CardComponent, PixelTitleComponent, PlayingCard,
            RouterLink, TranslatePipe],
  templateUrl: './poker.html',
  styleUrl: './poker.scss',
})
export class Poker implements OnDestroy {
  readonly poker = inject(PokerService);
  readonly stakes = STAKE_KEYS;
  private readonly i18n = inject(I18nService);
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private routeSub?: Subscription;

  /** ¿Estamos jugando un match de torneo (no la cola libre)? */
  readonly tournamentMatch = computed(() => this.poker.tournamentMatch());
  readonly isTournamentMatch = computed(() => this.tournamentMatch() !== null);

  /** Importe al que se subiría con el slider. */
  readonly raiseAmount = signal(0);
  /** Borrador del chat de mesa. */
  readonly chatDraft = signal('');

  readonly isSpectating = computed(() => this.poker.spectating());

  readonly streetLabel = computed(() => {
    const street = this.poker.state()?.game?.street;
    return street ? `poker.street.${street}` : '';
  });

  readonly resultTitle = computed(() => {
    const s = this.poker.state();
    if (!s?.game?.result) return '';
    const iWon = s.game.result.pots.some((p) => p.winners.some((w) => w.seat === s.you));
    if (s.game.result.showdown) return iWon ? 'poker.result.won' : 'poker.result.lost';
    return iWon ? 'poker.result.wonFold' : 'poker.result.lostFold';
  });

  /** Ganancias netas de la mano para mí (para el resumen). */
  readonly myWinnings = computed(() => {
    const s = this.poker.state();
    if (!s?.game?.result) return 0;
    return s.game.result.pots
      .flatMap((p) => p.winners)
      .filter((w) => w.seat === s.you)
      .reduce((sum, w) => sum + w.amount, 0);
  });

  readonly lastEvents = computed(() => (this.poker.state()?.log ?? []).slice(-4).reverse());

  /**
   * Cuota del bote al igualar: cuánto hay que poner sobre el bote final. Es el dato que
   * convierte «igualar 40» en una decisión (40 / (bote + 40)). Null si no hay nada que igualar.
   */
  readonly callOdds = computed(() => {
    const call = this.poker.callAction();
    const amount = call?.amount ?? 0;
    const pot = this.poker.state()?.game?.pot ?? 0;
    if (!call || pot <= 0 || amount <= 0) return null;
    return Math.round((amount / (pot + amount)) * 100);
  });

  /** Qué parte del reloj de turno queda (1 = recién empezado, 0 = agotado). */
  readonly turnFraction = computed(() => {
    const left = this.poker.turnSeconds();
    const total = this.poker.state()?.table?.turn_timeout ?? 0;
    if (left == null || total <= 0) return null;
    return Math.max(0, Math.min(1, left / total));
  });

  constructor() {
    // Si venimos del bracket de un torneo, la mesa ya existe en el servidor: se
    // entra directo a ella, sin pasar por la cola ni por un bot.
    // Se escuchan los parámetros de la URL, no solo el snapshot inicial: al pulsar
    // «Ver» en el lobby se navega a la MISMA ruta con `?table=…` y Angular reutiliza
    // el componente, así que el constructor no vuelve a ejecutarse.
    this.routeSub = this.route.queryParamMap.subscribe((qp) => this.applyRoute(qp));

    // Al empezar mi turno con opción de subir, colocar el slider en el mínimo legal.
    effect(() => {
      const raise = this.poker.raiseAction();
      if (!raise || raise.min == null) return;
      untracked(() => {
        const current = this.raiseAmount();
        const max = raise.max ?? raise.min!;
        if (current < raise.min! || current > max) this.raiseAmount.set(raise.min!);
      });
    });
  }

  ngOnDestroy(): void {
    this.routeSub?.unsubscribe();
    this.poker.reset();
  }

  /** Aplica lo que pide la URL: match de torneo, mirar una mesa o el lobby. */
  private applyRoute(qp: ParamMap): void {
    const tournamentId = qp.get('tournament');
    const matchId = qp.get('match');
    const spectate = qp.get('table');

    if (tournamentId && matchId) {
      this.poker.startTournamentMatch(tournamentId, matchId);
      return;
    }
    if (spectate) {
      // Mirar una mesa: solo lectura, sin cola ni asiento. Si ya se está mirando
      // esa misma mesa, no se reconecta.
      if (!(this.poker.spectating() && this.poker.tableId() === spectate)) {
        this.poker.spectateTable(spectate);
      }
      return;
    }
    this.poker.loadLiveTables();
    // «Jugar ahora» (?quick=1): se esperan las preferencias guardadas y se entra
    // directo a la cola. Es el quick seat de PokerStars: una decisión, cero ajustes.
    const quick = qp.get('quick') === '1';
    this.poker.loadPreferences(() => {
      if (quick && this.poker.status() === 'idle' && !this.poker.inTable()) {
        this.startQueue();
      }
    });
  }

  // ── Cola ────────────────────────────────────────────────────────────────
  stakeLabel(key: StakeKey): string {
    const level = this.poker.stakes()[key];
    return level ? `${level.small_blind}/${level.big_blind}` : key;
  }

  startQueue(): void {
    this.poker.clearError();
    this.poker.startQueue();
  }

  chooseStake(key: StakeKey): void {
    this.poker.chooseStake(key);
  }

  leave(): void {
    this.poker.reset();
  }

  refreshLiveTables(): void {
    this.poker.loadLiveTables();
  }

  /** Mirar una mesa: se refleja en la URL para poder compartirla. */
  watch(tableId: string): void {
    this.router.navigate(['/poker'], { queryParams: { table: tableId } });
  }

  sendChat(): void {
    const texto = this.chatDraft();
    if (!texto.trim()) return;
    this.poker.sendChat(texto);
    this.chatDraft.set('');
  }

  onChatKeydown(event: KeyboardEvent): void {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      this.sendChat();
    }
  }

  // ── Mesa ────────────────────────────────────────────────────────────────
  act(action: string, amount?: number): void {
    this.poker.clearError();
    this.poker.act(action, amount);
  }

  onRaiseSlider(event: Event): void {
    this.raiseAmount.set(Number((event.target as HTMLInputElement).value));
  }

  /** Botones rápidos de subida: fracción del bote, acotado al rango legal. */
  quickRaise(fraction: number): void {
    const raise = this.poker.raiseAction();
    const game = this.poker.state()?.game;
    if (!raise || raise.min == null || !game) return;
    const target = Math.round(game.current_bet + game.pot * fraction);
    const clamped = Math.min(Math.max(target, raise.min), raise.max ?? raise.min);
    this.raiseAmount.set(clamped);
  }

  /** Emoticonos de un toque: la mesa se pica sin abrir el teclado. */
  readonly emotes = ['👍', '😂', '😱', '🔥', '👏', '💀'];

  /** Envía un emoticono por el chat de la mesa (el servidor lo reenvía tal cual). */
  sendEmote(emoji: string): void {
    this.poker.sendChat(emoji);
  }

  /**
   * Tarjeta de resultado para compartir. Se dibuja en canvas (sin dependencias) y se
   * manda por Web Share si el navegador lo admite; si no, se descarga como PNG.
   */
  async shareResult(): Promise<void> {
    const s = this.poker.state();
    const result = s?.game?.result;
    if (!s || !result) return;
    const canvas = document.createElement('canvas');
    canvas.width = 1200;
    canvas.height = 630;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    ctx.fillStyle = '#0c0c14';
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    ctx.strokeStyle = '#22d3ee';
    ctx.lineWidth = 4;
    ctx.strokeRect(28, 28, canvas.width - 56, canvas.height - 56);

    ctx.fillStyle = '#22d3ee';
    ctx.font = 'bold 54px "Courier New", monospace';
    ctx.fillText('TRANSCENDENCE', 72, 130);

    ctx.fillStyle = '#f5f5f5';
    ctx.font = 'bold 68px "Courier New", monospace';
    ctx.fillText(this.i18n.t(this.resultTitle()), 72, 260);

    ctx.fillStyle = '#facc15';
    ctx.font = 'bold 44px "Courier New", monospace';
    ctx.fillText(`${this.i18n.t('poker.result.pot')}: ${result.total ?? 0}`, 72, 350);

    const mine = this.myWinnings();
    ctx.fillStyle = mine > 0 ? '#4ade80' : '#f87171';
    ctx.fillText(`${mine > 0 ? '+' : ''}${mine}`, 72, 430);

    const hand = s.you != null ? this.handNameFor(s.you) : '';
    if (hand) {
      ctx.fillStyle = '#a1a1aa';
      ctx.font = '32px "Courier New", monospace';
      ctx.fillText(hand, 72, 500);
    }

    ctx.fillStyle = '#71717a';
    ctx.font = '28px "Courier New", monospace';
    ctx.fillText(
      `#${s.table.hand_number} · ${s.table.small_blind}/${s.table.big_blind}`,
      72,
      565,
    );

    const blob = await new Promise<Blob | null>((resolve) => canvas.toBlob(resolve, 'image/png'));
    if (!blob) return;

    const file = new File([blob], 'transcendence-poker.png', { type: 'image/png' });
    const nav = navigator as Navigator & {
      canShare?: (data: ShareData) => boolean;
      share?: (data: ShareData) => Promise<void>;
    };
    if (nav.canShare?.({ files: [file] }) && nav.share) {
      try {
        await nav.share({ files: [file], title: 'Transcendence' });
        return;
      } catch {
        // Cancelado o no permitido: se cae a la descarga, que siempre funciona.
      }
    }
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'transcendence-poker.png';
    a.click();
    URL.revokeObjectURL(url);
  }

  /**
   * Revancha: se vuelve a la cola con la misma configuración. `startQueue` ya cierra
   * la mesa anterior y reinicia el estado, así que no hace falta pasar por el lobby.
   */
  rematch(): void {
    this.poker.startQueue();
  }

  isWinner(seatIndex: number): boolean {
    const s = this.poker.state();
    return !!s?.game?.result?.pots.some((p) => p.winners.some((w) => w.seat === seatIndex));
  }

  handNameFor(seatIndex: number): string {
    const s = this.poker.state();
    const hands = s?.game?.result?.hands;
    return hands?.[String(seatIndex)]?.name ?? '';
  }

  revealedFor(seatIndex: number): string[] | null {
    const s = this.poker.state();
    return s?.game?.result?.revealed?.[String(seatIndex)] ?? null;
  }

  seatByIndex(index: number) {
    return this.poker.state()?.game?.seats.find((s) => s.index === index) ?? null;
  }
}
