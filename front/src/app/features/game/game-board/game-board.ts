import {
  Component,
  computed,
  effect,
  ElementRef,
  inject,
  OnDestroy,
  OnInit,
  signal,
  ViewChild,
} from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { ActivatedRoute, Router } from '@angular/router';
import { DomSanitizer, SafeResourceUrl } from '@angular/platform-browser';
import { AuthService } from '../../../core/services/auth.service';
import { UserService, UserStats } from '../../../core/services/user.service';
import { RoomService } from '../../../core/services/room.service';
import { BadgeComponent } from '../../../shared/components/badge/badge';
import { CardComponent } from '../../../shared/components/card/card';
import { PixelTitleComponent } from '../../../shared/components/pixel-title/pixel-title';
import { environment } from '../../../../environments/environment';
import { TranslatePipe } from '../../../i18n';
import { I18nService } from '../../../i18n';

interface BackendGame {
  id: number;
}

interface GameFinishedMessage {
  type: 'game-finished';
  winner: string;
  score: string;
}

type GameTheme = 'classic' | 'neon' | 'crimson' | 'violet' | 'gold';

@Component({
  selector: 'app-game-board',
  standalone: true,
  imports: [BadgeComponent, CardComponent, PixelTitleComponent, TranslatePipe],
  templateUrl: './game-board.html',
  styleUrl: './game-board.scss',
})
export class GameBoard implements OnInit, OnDestroy {
  readonly auth = inject(AuthService);
  private readonly sanitizer = inject(DomSanitizer);
  private readonly userService = inject(UserService);
  private readonly roomService = inject(RoomService);
  private readonly http = inject(HttpClient);
  private readonly i18n = inject(I18nService);
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);

  // When the game is launched from a tournament bracket ("Jugar"), the result is
  // reported to the tournament match endpoint instead of the generic games one.
  private tournamentCtx: { tournamentId: string; matchId: string; p1: string; p2: string } | null =
    null;

  @ViewChild('gameFrame') private readonly gameFrame!: ElementRef<HTMLIFrameElement>;
  // gameUrl is absolute in dev (http://localhost:8000/game/) and relative in
  // prod (/game/). Resolve against the current origin so both yield a valid origin.
  private readonly gameOrigin = new URL(environment.gameUrl, window.location.origin).origin;

  readonly gameSrc: SafeResourceUrl = this.sanitizer.bypassSecurityTrustResourceUrl(
    environment.gameUrl,
  );

  readonly userStats = signal<UserStats | null>(null);
  // Live matchmaking/room presence, driven by RoomService over WebSocket.
  readonly onlineStatus = signal<'offline' | 'searching' | 'matched'>('offline');

  // ── Game Customization (Minor module) ─────────────────────────────
  // Pushed into the WASM game via postMessage('set-config'). The card game is
  // local hotseat multiplayer, so `players` (2–4) selects how many humans play
  // against each other on the same screen.
  readonly themes: readonly GameTheme[] = ['classic', 'neon', 'crimson', 'violet', 'gold'];
  readonly players = signal(2);
  readonly targetScore = signal(300);
  readonly rounds = signal(5);
  readonly theme = signal<GameTheme>('classic');

  // The Game row this session reports its result to. Created lazily on init.
  private gameId: number | null = null;
  private readonly messageListener = (event: MessageEvent) => this.onGameMessage(event);

  constructor() {
    effect(() => {
      const user = this.auth.user();
      if (user?.username) this.sendUsernameToGame(user.username);
    });
    effect(() => {
      const lang = this.i18n.currentLang();
      this.sendLangToGame(lang);
    });
  }

  readonly stats = computed(() => {
    const stats = this.userStats();
    if (!stats) {
      return [
        { label: 'lobby.rank', value: '—', color: 'neon-text-yellow' },
        { label: 'lobby.wins', value: '—', color: 'neon-text-green' },
        { label: 'lobby.losses', value: '—', color: 'text-secondary' },
        { label: 'lobby.winRate', value: '—', color: 'neon-text-cyan' },
      ];
    }
    return [
      { label: 'lobby.rank', value: `#${stats.rank}`, color: 'neon-text-yellow' },
      { label: 'lobby.wins', value: String(stats.wins), color: 'neon-text-green' },
      { label: 'lobby.losses', value: String(stats.losses), color: 'text-secondary' },
      { label: 'lobby.winRate', value: `${stats.winRate}%`, color: 'neon-text-cyan' },
    ];
  });

  ngOnInit() {
    // Listen for the result the WASM game posts when a match ends.
    window.addEventListener('message', this.messageListener);

    // Tournament context (set by the bracket's "Jugar" button).
    const qp = this.route.snapshot.queryParamMap;
    const tournamentId = qp.get('tournament');
    const matchId = qp.get('match');
    if (tournamentId && matchId) {
      this.tournamentCtx = {
        tournamentId,
        matchId,
        p1: qp.get('p1') ?? '',
        p2: qp.get('p2') ?? '',
      };
    }

    if (this.auth.isAuthenticated()) {
      this.loadStats();
      this.createGameSession();
      this.connectMatchmaking();
    }
  }

  ngOnDestroy() {
    window.removeEventListener('message', this.messageListener);
    this.roomService.disconnect();
  }

  readonly rules = ['lobby.rule1', 'lobby.rule2', 'lobby.rule3', 'lobby.rule4', 'lobby.rule5'];

  onGameFrameLoad(): void {
    const user = this.auth.user();
    if (user?.username) this.sendUsernameToGame(user.username);
    this.sendLangToGame(this.i18n.currentLang());
    this.sendConfigToGame();
  }

  // ── Customization controls ────────────────────────────────────────
  setPlayers(n: number): void {
    this.players.set(Math.min(4, Math.max(2, n)));
    this.sendConfigToGame();
  }

  setTargetScore(n: number): void {
    this.targetScore.set(Math.min(1000, Math.max(100, n)));
    this.sendConfigToGame();
  }

  setRounds(n: number): void {
    this.rounds.set(Math.min(10, Math.max(1, n)));
    this.sendConfigToGame();
  }

  setTheme(t: GameTheme): void {
    this.theme.set(t);
    this.sendConfigToGame();
  }

  private sendConfigToGame(): void {
    const iframe = this.gameFrame?.nativeElement;
    if (!iframe?.contentWindow) return;
    iframe.contentWindow.postMessage(
      {
        type: 'set-config',
        config: {
          players: this.players(),
          targetScore: this.targetScore(),
          rounds: this.rounds(),
          theme: this.theme(),
        },
      },
      this.gameOrigin,
    );
  }

  private loadStats(): void {
    this.userService.getUserStats().subscribe({
      next: (stats) => this.userStats.set(stats),
      error: () => {},
    });
  }

  /** Open a Game row so a finished match has an id to report against. */
  private createGameSession(): void {
    this.http.post<BackendGame>(`${environment.apiUrl}/games/create_game/`, {}).subscribe({
      next: (game) => {
        this.gameId = game.id;
      },
      error: () => {
        this.gameId = null;
      },
    });
  }

  /** Use RoomService to broadcast presence / find an opponent in real time. */
  private connectMatchmaking(): void {
    this.onlineStatus.set('searching');
    this.roomService.connectToMatchmaking((roomId) => {
      this.onlineStatus.set('matched');
      this.roomService.connectToRoomUpdates(roomId, () => {
        // Room state changes are reflected here as the live match progresses.
      });
    });
  }

  /** Handle the postMessage the WASM game emits when a match finishes. */
  private onGameMessage(event: MessageEvent): void {
    // Trust only messages coming from our own game iframe.
    const fromGameFrame = event.source === this.gameFrame?.nativeElement?.contentWindow;
    if (!fromGameFrame && event.origin !== this.gameOrigin) return;

    const data = event.data as Partial<GameFinishedMessage> | null;
    if (!data || data.type !== 'game-finished') return;

    this.reportResult(data.winner ?? '', data.score ?? '0-0');
  }

  private reportResult(winner: string, score: string): void {
    if (!this.auth.isAuthenticated()) return;

    const [p1Raw, p2Raw] = score.split('-');
    const player1_score = Number.parseInt(p1Raw, 10) || 0;
    const player2_score = Number.parseInt(p2Raw, 10) || 0;

    // Tournament match: report to the bracket so the round can advance.
    if (this.tournamentCtx) {
      this.reportTournamentResult(winner, player1_score, player2_score);
      return;
    }

    if (this.gameId == null) return;
    this.http
      .post(`${environment.apiUrl}/games/${this.gameId}/finish/`, {
        winner,
        player1_score,
        player2_score,
      })
      .subscribe({
        next: () => {
          // Refresh ELO/wins/losses now that the backend recorded the result,
          // and prevent double-reporting by clearing the session id.
          this.gameId = null;
          this.loadStats();
        },
        error: () => {},
      });
  }

  /** Push a tournament-match result, then return to the live bracket. */
  private reportTournamentResult(
    winner: string,
    player1_score: number,
    player2_score: number,
  ): void {
    const ctx = this.tournamentCtx;
    if (!ctx) return;

    // Resolve the winning slot: prefer matching the reported winner name to the
    // slot usernames; fall back to the higher score.
    let winner_slot: 1 | 2;
    if (winner && winner === ctx.p1) winner_slot = 1;
    else if (winner && winner === ctx.p2) winner_slot = 2;
    else winner_slot = player1_score >= player2_score ? 1 : 2;

    this.tournamentCtx = null; // guard against double reporting
    this.http
      .post(`${environment.apiUrl}/tournament/${ctx.tournamentId}/matches/${ctx.matchId}/result/`, {
        winner_slot,
        player1_score,
        player2_score,
      })
      .subscribe({
        next: () => this.router.navigate(['/tournament', ctx.tournamentId]),
        error: () => this.router.navigate(['/tournament', ctx.tournamentId]),
      });
  }

  private sendUsernameToGame(username: string): void {
    const iframe = this.gameFrame?.nativeElement;
    if (!iframe?.contentWindow) return;
    iframe.contentWindow.postMessage({ type: 'set-username', username }, this.gameOrigin);
  }

  private sendLangToGame(lang: string): void {
    const iframe = this.gameFrame?.nativeElement;
    if (!iframe?.contentWindow) return;
    iframe.contentWindow.postMessage({ type: 'set-language', lang }, this.gameOrigin);
  }
}
