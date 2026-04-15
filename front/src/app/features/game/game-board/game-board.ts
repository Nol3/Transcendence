import { Component, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { AuthService } from '../../../core/services/auth.service';
import { NotificationService } from '../../../core/services/notification.service';
import { BadgeComponent } from '../../../shared/components/badge/badge';
import { ButtonComponent } from '../../../shared/components/button/button';
import { CardComponent } from '../../../shared/components/card/card';
import { PixelTitleComponent } from '../../../shared/components/pixel-title/pixel-title';
import { SpinnerComponent } from '../../../shared/components/spinner/spinner';

type LobbyState = 'idle' | 'searching' | 'found';

interface RoomEntry {
  id: string;
  host: string;
  status: 'waiting' | 'in-progress';
  players: number;
  maxPlayers: number;
}

const MOCK_ROOMS: RoomEntry[] = [
  { id: 'room-001', host: 'SHADOW_KING',  status: 'waiting',     players: 1, maxPlayers: 2 },
  { id: 'room-002', host: 'NEON_GHOST',   status: 'in-progress', players: 2, maxPlayers: 2 },
  { id: 'room-003', host: 'VOID_WALKER',  status: 'waiting',     players: 1, maxPlayers: 2 },
];

@Component({
  selector: 'app-game-board',
  standalone: true,
  imports: [BadgeComponent, ButtonComponent, CardComponent, PixelTitleComponent, SpinnerComponent],
  templateUrl: './game-board.html',
  styleUrl: './game-board.scss',
})
export class GameBoard {
  readonly auth  = inject(AuthService);
  readonly notif = inject(NotificationService);

  readonly lobbyState = signal<LobbyState>('idle');
  readonly rooms      = signal<RoomEntry[]>(MOCK_ROOMS);
  readonly countdown  = signal(0);

  private searchTimer?: ReturnType<typeof setTimeout>;
  private countdownTimer?: ReturnType<typeof setInterval>;

  findMatch() {
    this.lobbyState.set('searching');
    // Simulate matchmaking for 3s
    this.searchTimer = setTimeout(() => {
      this.lobbyState.set('found');
      this.notif.success('MATCH FOUND', 'Opponent located — game starting!');
      // Game component integration point — teammate hooks here
    }, 3000);
  }

  cancelSearch() {
    clearTimeout(this.searchTimer);
    this.lobbyState.set('idle');
  }

  joinRoom(room: RoomEntry) {
    if (room.status === 'in-progress') {
      this.notif.warning('MATCH IN PROGRESS', 'This game has already started.');
      return;
    }
    this.notif.info('JOINING ROOM', `Connecting to ${room.host}'s game...`);
    // Room join logic — backend integration point
  }

  roomBadge(status: RoomEntry['status']): 'success' | 'info' {
    return status === 'waiting' ? 'success' : 'info';
  }
}
