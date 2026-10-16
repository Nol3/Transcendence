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
    this.poker.loadPreferences();
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
