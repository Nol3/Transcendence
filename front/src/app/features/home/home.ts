import { Component, inject, OnInit, OnDestroy, signal, computed } from '@angular/core';
import { RouterLink } from '@angular/router';
import { DecimalPipe } from '@angular/common';
import { AuthService } from '../../core/services/auth.service';
import { UserService, LeaderboardEntry, UserStats } from '../../core/services/user.service';
import { BadgeComponent } from '../../shared/components/badge/badge';
import { CardComponent } from '../../shared/components/card/card';
import { PixelTitleComponent } from '../../shared/components/pixel-title/pixel-title';
import { ButtonComponent } from '../../shared/components/button/button';
import { SpinnerComponent } from '../../shared/components/spinner/spinner';
import { TranslatePipe } from '../../i18n/translate.pipe';

@Component({
  selector: 'app-home',
  standalone: true,
  imports: [
    RouterLink,
    DecimalPipe,
    BadgeComponent,
    CardComponent,
    PixelTitleComponent,
    ButtonComponent,
    SpinnerComponent,
    TranslatePipe,
  ],
  templateUrl: './home.html',
  styleUrl: './home.scss',
})
export class Home implements OnInit, OnDestroy {
  readonly auth = inject(AuthService);
  private readonly userService = inject(UserService);

  readonly leaderboard = signal<LeaderboardEntry[]>([]);
  readonly leaderboardLoading = signal(true);
  readonly time = signal('');
  readonly totalPlayers = signal(0);
  readonly gamesPlayed = signal(0);
  readonly userStats = signal<UserStats | null>(null);
  readonly userOnlineStatus = signal(true);

  readonly homeRankLabel = computed(() => {
    const rank = this.userStats()?.rank ?? 0;
    if (rank === 1) return 'CHAMPION';
    if (rank === 2) return 'MASTER';
    if (rank <= 5) return 'EXPERT';
    if (rank <= 10) return 'SKILLED';
    return 'ROOKIE';
  });

  readonly homeRankVariant = computed((): 'warning' | 'info' | 'default' => {
    const rank = this.userStats()?.rank ?? 0;
    if (rank === 1) return 'warning';
    if (rank <= 5) return 'info';
    return 'default';
  });

  private timer?: ReturnType<typeof setInterval>;

  ngOnInit() {
    this.loadLeaderboard();
    if (this.auth.isAuthenticated()) {
      this.loadUserStats();
    }
    this.updateTime();
    this.timer = setInterval(() => this.updateTime(), 1000);
  }

  ngOnDestroy() {
    if (this.timer) {
      clearInterval(this.timer);
    }
  }

  private loadLeaderboard() {
    this.userService.getLeaderboard(1, 10).subscribe({
      next: ({ entries, total }) => {
        this.leaderboard.set(entries);
        this.totalPlayers.set(total);
        this.gamesPlayed.set(entries.reduce((sum, e) => sum + e.wins + e.losses, 0));
        this.leaderboardLoading.set(false);
      },
      error: () => {
        this.leaderboardLoading.set(false);
      },
    });
  }

  private loadUserStats() {
    this.userService.getUserStats().subscribe({
      next: (stats) => this.userStats.set(stats),
      error: () => {},
    });
  }

  private updateTime() {
    const now = new Date();
    const h = String(now.getHours()).padStart(2, '0');
    const m = String(now.getMinutes()).padStart(2, '0');
    const s = String(now.getSeconds()).padStart(2, '0');
    this.time.set(`${h}:${m}:${s}`);
  }

  rankBadge(rank: number): 'warning' | 'default' | 'info' {
    if (rank === 1) return 'warning';
    if (rank === 2) return 'info';
    return 'default';
  }

  rankIcon(rank: number): string {
    if (rank === 1) return '▲';
    if (rank === 2) return '●';
    if (rank === 3) return '■';
    return `${rank}`;
  }

  winRate(entry: LeaderboardEntry): number {
    const total = entry.wins + entry.losses;
    return total === 0 ? 0 : Math.round((entry.wins / total) * 100);
  }

  trackByEntry(_: number, entry: LeaderboardEntry): string {
    return entry.user?.id?.toString() ?? String(entry.rank);
  }
}
