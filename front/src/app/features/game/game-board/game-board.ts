import {
  Component,
  computed,
  effect,
  ElementRef,
  inject,
  OnInit,
  signal,
  ViewChild,
} from '@angular/core';
import { DomSanitizer, SafeResourceUrl } from '@angular/platform-browser';
import { AuthService } from '../../../core/services/auth.service';
import { UserService, UserStats } from '../../../core/services/user.service';
import { BadgeComponent } from '../../../shared/components/badge/badge';
import { CardComponent } from '../../../shared/components/card/card';
import { PixelTitleComponent } from '../../../shared/components/pixel-title/pixel-title';
import { environment } from '../../../../environments/environment';
import { TranslatePipe } from '../../../i18n';
import { I18nService } from '../../../i18n';

@Component({
  selector: 'app-game-board',
  standalone: true,
  imports: [BadgeComponent, CardComponent, PixelTitleComponent, TranslatePipe],
  templateUrl: './game-board.html',
  styleUrl: './game-board.scss',
})
export class GameBoard implements OnInit {
  readonly auth = inject(AuthService);
  private readonly sanitizer = inject(DomSanitizer);
  private readonly userService = inject(UserService);
  private readonly i18n = inject(I18nService);

  @ViewChild('gameFrame') private readonly gameFrame!: ElementRef<HTMLIFrameElement>;
  // gameUrl is absolute in dev (http://localhost:8000/game/) and relative in
  // prod (/game/). Resolve against the current origin so both yield a valid origin.
  private readonly gameOrigin = new URL(environment.gameUrl, window.location.origin).origin;

  readonly gameSrc: SafeResourceUrl = this.sanitizer.bypassSecurityTrustResourceUrl(
    environment.gameUrl,
  );

  readonly userStats = signal<UserStats | null>(null);

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
    if (this.auth.isAuthenticated()) {
      this.userService.getUserStats().subscribe({
        next: (stats) => this.userStats.set(stats),
        error: () => {},
      });
    }
  }

  readonly rules = ['lobby.rule1', 'lobby.rule2', 'lobby.rule3', 'lobby.rule4', 'lobby.rule5'];

  onGameFrameLoad(): void {
    const user = this.auth.user();
    if (user?.username) this.sendUsernameToGame(user.username);
    this.sendLangToGame(this.i18n.currentLang());
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
