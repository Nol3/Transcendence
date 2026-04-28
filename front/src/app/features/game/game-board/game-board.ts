import { Component, computed, inject, OnInit, signal } from '@angular/core';
import { DomSanitizer, SafeResourceUrl } from '@angular/platform-browser';
import { AuthService } from '../../../core/services/auth.service';
import { UserService, UserStats } from '../../../core/services/user.service';
import { BadgeComponent } from '../../../shared/components/badge/badge';
import { CardComponent } from '../../../shared/components/card/card';
import { PixelTitleComponent } from '../../../shared/components/pixel-title/pixel-title';
import { environment } from '../../../../environments/environment';

@Component({
  selector: 'app-game-board',
  standalone: true,
  imports: [BadgeComponent, CardComponent, PixelTitleComponent],
  templateUrl: './game-board.html',
  styleUrl: './game-board.scss',
})
export class GameBoard implements OnInit {
  readonly auth = inject(AuthService);
  private readonly sanitizer = inject(DomSanitizer);
  private readonly userService = inject(UserService);

  readonly gameSrc: SafeResourceUrl = this.sanitizer.bypassSecurityTrustResourceUrl(
    environment.gameUrl,
  );

  readonly userStats = signal<UserStats | null>(null);

  readonly stats = computed(() => {
    const stats = this.userStats();
    if (!stats) {
      return [
        { label: 'RANK', value: '—', color: 'neon-text-yellow' },
        { label: 'WINS', value: '—', color: 'neon-text-green' },
        { label: 'LOSSES', value: '—', color: 'text-secondary' },
        { label: 'W-RATE', value: '—', color: 'neon-text-cyan' },
      ];
    }
    return [
      { label: 'RANK', value: `#${stats.rank}`, color: 'neon-text-yellow' },
      { label: 'WINS', value: String(stats.wins), color: 'neon-text-green' },
      { label: 'LOSSES', value: String(stats.losses), color: 'text-secondary' },
      { label: 'W-RATE', value: `${stats.winRate}%`, color: 'neon-text-cyan' },
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

  readonly rules = [
    'Each player starts with 5 cards',
    'Draw 1 card per turn',
    'Play cards to attack or defend',
    'Reduce opponent HP to 0 to win',
    'Special cards have unique effects',
  ];
}
