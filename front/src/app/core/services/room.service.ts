import { Injectable, inject, signal } from '@angular/core';
import { Observable, tap, map, of } from 'rxjs';
import { ApiService } from './api.service';
import { environment } from '../../../environments/environment';

export type RoomStatus = 'waiting' | 'playing' | 'finished';
export type RoomVisibility = 'public' | 'private';

export interface Room {
  id: string;
  name: string;
  host: { id: number; username: string };
  players: { id: number; username: string }[];
  maxPlayers: number;
  status: RoomStatus;
  visibility: RoomVisibility;
  createdAt: string;
}

export interface CreateRoomPayload {
  name: string;
  maxPlayers: number;
  visibility: RoomVisibility;
  password?: string;
}

@Injectable({ providedIn: 'root' })
export class RoomService {
  private readonly api = inject(ApiService);
  private readonly _rooms = signal<Room[]>([]);
  private eventSource: EventSource | null = null;
  private ws: WebSocket | null = null;

  readonly rooms = this._rooms.asReadonly();

  getRooms(): Observable<Room[]> {
    return this.api.getPaginated<Room>('/rooms').pipe(
      tap((res) => {
        this._rooms.set(res.data);
      }),
      map((res) => res.data)
    );
  }

  getRoom(id: string): Observable<Room> {
    return this.api.get<{ room: Room }>(`/rooms/${id}`).pipe(
      map((res) => res.data!.room)
    );
  }

  createRoom(payload: CreateRoomPayload): Observable<Room> {
    return this.api.post<{ room: Room }>('/rooms', payload).pipe(
      map((res) => res.data!.room)
    );
  }

  joinRoom(id: string, password?: string): Observable<Room> {
    return this.api.post<{ room: Room }>(`/rooms/${id}/join`, { password }).pipe(
      map((res) => res.data!.room)
    );
  }

  leaveRoom(id: string): Observable<void> {
    return this.api.post<null>(`/rooms/${id}/leave`, {}).pipe(
      map(() => undefined)
    );
  }

  startGame(roomId: string): Observable<void> {
    return this.api.post<null>(`/rooms/${roomId}/start`, {}).pipe(
      map(() => undefined)
    );
  }

  connectToRoomUpdates(roomId: string, onUpdate: (room: Room) => void): void {
    const token = localStorage.getItem('access_token');
    if (!token) return;

    this.ws = new WebSocket(`${environment.wsUrl}/rooms/${roomId}?token=${token}`);

    this.ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.type === 'room_update') {
        onUpdate(data.room);
      }
    };

    this.ws.onerror = () => {
      console.error('WebSocket error');
    };

    this.ws.onclose = () => {
      this.ws = null;
    };
  }

  disconnect(): void {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
    if (this.eventSource) {
      this.eventSource.close();
      this.eventSource = null;
    }
  }

  connectToMatchmaking(onMatchFound: (roomId: string) => void): void {
    const token = localStorage.getItem('access_token');
    if (!token) return;

    this.ws = new WebSocket(`${environment.wsUrl}/matchmaking?token=${token}`);

    this.ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.type === 'match_found') {
        onMatchFound(data.roomId);
      }
    };

    this.ws.onerror = () => {
      console.error('Matchmaking WebSocket error');
    };
  }

  startMatchmaking(): Observable<void> {
    return this.api.post<null>('/matchmaking/start', {}).pipe(
      map(() => undefined)
    );
  }

  cancelMatchmaking(): Observable<void> {
    return this.api.post<null>('/matchmaking/cancel', {}).pipe(
      map(() => undefined)
    );
  }
}
