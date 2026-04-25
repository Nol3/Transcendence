import { Component, computed, inject } from '@angular/core';
import { DomSanitizer, SafeResourceUrl } from '@angular/platform-browser';
import { AuthService } from '../../../core/services/auth.service';
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
export class GameBoard {
  readonly auth = inject(AuthService);
  private readonly sanitizer = inject(DomSanitizer);

  readonly gameSrc: SafeResourceUrl = this.sanitizer.bypassSecurityTrustResourceUrl(
    environment.gameUrl,
  );

  readonly stats = computed(() => [
    { label: 'RANK', value: '#42', color: 'neon-text-yellow' },
    { label: 'WINS', value: '12', color: 'neon-text-green' },
    { label: 'LOSSES', value: '4', color: 'text-secondary' },
    { label: 'W-RATE', value: '75%', color: 'neon-text-cyan' },
  ]);

  readonly rules = [
    'Each player starts with 5 cards',
    'Draw 1 card per turn',
    'Play cards to attack or defend',
    'Reduce opponent HP to 0 to win',
    'Special cards have unique effects',
  ];
}
