import { Injectable, inject } from '@angular/core';
import { Observable, map } from 'rxjs';
import { ApiService } from './api.service';
import { User } from '../models/user.model';

export interface LeaderboardEntry {
  rank: number;
  user: User;
  wins: number;
  losses: number;
  winRate: number;
}

export interface UserStats {
  wins: number;
  losses: number;
  rank: number;
  winRate: number;
  gamesPlayed: number;
  currentStreak: number;
  longestStreak: number;
}

export interface GameHistoryEntry {
  id: string;
  opponent: User;
  result: 'win' | 'loss';
  score: string;
  playedAt: string;
}

/** Respuesta de `POST /api/users/me/checkin/`. */
export interface DailyCheckin {
  streak: number;
  best: number;
  already: boolean;
  milestone?: boolean;
  today: string;
}

@Injectable({ providedIn: 'root' })
export class UserService {
  private readonly api = inject(ApiService);

  getLeaderboard(page = 1, limit = 10): Observable<{ entries: LeaderboardEntry[]; total: number }> {
    return this.api
      .getPaginated<LeaderboardEntry>('/leaderboard', { page: String(page), limit: String(limit) })
      .pipe(map((res) => ({ entries: res.data, total: res.meta.total })));
  }

  getUserById(id: number): Observable<User> {
    return this.api.get<{ user: User }>(`/users/${id}`).pipe(map((res) => res.data!.user));
  }

  getUserStats(userId?: number): Observable<UserStats> {
    const endpoint = userId ? `/users/${userId}/stats/` : '/users/me/stats/';
    return this.api.get<UserStats>(endpoint).pipe(map((res) => res.data!));
  }

  /** Ficha la visita del día y devuelve la racha (idempotente dentro del día). */
  checkin(): Observable<DailyCheckin> {
    return this.api.post<DailyCheckin>('/users/me/checkin/', {}).pipe(map((res) => res.data!));
  }

  getUserHistory(userId?: number, page = 1, limit = 20): Observable<GameHistoryEntry[]> {
    const endpoint = userId ? `/users/${userId}/history/` : '/users/me/history/';
    return this.api
      .getPaginated<GameHistoryEntry>(endpoint, { page: String(page), limit: String(limit) })
      .pipe(map((res) => res.data));
  }

  searchUsers(query: string): Observable<User[]> {
    return this.api
      .get<{ users: User[] }>('/users/search', { q: query })
      .pipe(map((res) => res.data?.users ?? []));
  }
}
