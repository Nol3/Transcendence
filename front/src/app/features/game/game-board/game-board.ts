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
    if (this.gameId == null || !this.auth.isAuthenticated()) return;

    const [p1Raw, p2Raw] = score.split('-');
    const player1_score = Number.parseInt(p1Raw, 10) || 0;
    const player2_score = Number.parseInt(p2Raw, 10) || 0;

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
