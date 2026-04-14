import { Component, inject, OnInit, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { AuthService } from '../../core/services/auth.service';
import { BadgeComponent } from '../../shared/components/badge/badge';
import { CardComponent } from '../../shared/components/card/card';
import { PixelTitleComponent } from '../../shared/components/pixel-title/pixel-title';
import { ButtonComponent } from '../../shared/components/button/button';

interface LeaderboardEntry {
  rank: number;
  username: string;
  wins: number;
  losses: number;
}

const MOCK_LEADERBOARD: LeaderboardEntry[] = [
  { rank: 1, username: 'PLAYER_ONE',   wins: 42, losses: 3  },
  { rank: 2, username: 'SHADOW_KING',  wins: 38, losses: 7  },
  { rank: 3, username: 'NEON_GHOST',   wins: 31, losses: 10 },
  { rank: 4, username: 'VOID_WALKER',  wins: 27, losses: 12 },
  { rank: 5, username: 'CYBER_ACE',    wins: 22, losses: 15 },
];

@Component({
  selector: 'app-home',
  standalone: true,
  imports: [RouterLink, BadgeComponent, CardComponent, PixelTitleComponent, ButtonComponent],
  templateUrl: './home.html',
  styleUrl: './home.scss',
})
export class Home implements OnInit {
  readonly auth = inject(AuthService);

  readonly leaderboard = signal<LeaderboardEntry[]>([]);
  readonly time = signal('');

  private timer?: ReturnType<typeof setInterval>;

  ngOnInit() {
    this.leaderboard.set(MOCK_LEADERBOARD);
    this.updateTime();
    this.timer = setInterval(() => this.updateTime(), 1000);
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
}
