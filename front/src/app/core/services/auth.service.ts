import { Injectable, inject, signal, computed, PLATFORM_ID } from '@angular/core';
import { Router } from '@angular/router';
import { tap, map, of, catchError } from 'rxjs';
import { ApiService } from './api.service';
import { User, AuthTokens } from '../models/user.model';

const ACCESS_TOKEN_KEY = 'access_token';
const REFRESH_TOKEN_KEY = 'refresh_token';

@Injectable({ providedIn: 'root' })
export class AuthService {
  private readonly platformId = inject(PLATFORM_ID);
  private readonly api = inject(ApiService);
  private readonly router = inject(Router);

  private readonly _user = signal<User | null>(null);
  private readonly _loading = signal(false);

  readonly user = this._user.asReadonly();
  readonly loading = this._loading.asReadonly();
  readonly isAuthenticated = computed(() => this._user() !== null);

  constructor() {
    this.initAuth();
  }

  private initAuth(): void {
    const token = this.getToken();
    if (token) {
      this.fetchCurrentUser().subscribe({
        error: () => this.clearTokens(),
      });
    }
  }

  login(email: string, password: string) {
    this._loading.set(true);
    return this.api.post<{ user: User; tokens: AuthTokens }>('/auth/login', { email, password }).pipe(
      tap({
        next: (res) => {
          if (res.data) {
            this._user.set(res.data.user);
            this.setTokens(res.data.tokens);
          }
          this._loading.set(false);
        },
        error: () => {
          this._loading.set(false);
        },
      }),
      map((res) => res.data)
    );
  }

  register(username: string, email: string, password: string) {
    this._loading.set(true);
    return this.api.post<{ user: User; tokens: AuthTokens }>('/auth/register', { username, email, password }).pipe(
      tap({
        next: (res) => {
          if (res.data) {
            this._user.set(res.data.user);
            this.setTokens(res.data.tokens);
          }
          this._loading.set(false);
        },
        error: () => {
          this._loading.set(false);
        },
      }),
      map((res) => res.data)
    );
  }

  logout(): void {
    this.api.post('/auth/logout', {}).subscribe({
      complete: () => {
        this._user.set(null);
        this.clearTokens();
        this.router.navigate(['/login']);
      },
      error: () => {
        this._user.set(null);
        this.clearTokens();
        this.router.navigate(['/login']);
      },
    });
  }

  refreshToken() {
    const refreshToken = localStorage.getItem(REFRESH_TOKEN_KEY);
    if (!refreshToken) {
      return of(null);
    }

    return this.api.post<{ tokens: AuthTokens }>('/auth/refresh', { refreshToken }).pipe(
      tap((res) => {
        if (res.data) {
          this.setTokens(res.data.tokens);
        }
      }),
      map((res) => res.data?.tokens ?? null),
      catchError(() => {
        this.clearTokens();
        return of(null);
      })
    );
  }

  fetchCurrentUser() {
    return this.api.get<{ user: User }>('/auth/me').pipe(
      tap((res) => {
        if (res.data) {
          this._user.set(res.data.user);
        }
      }),
      map((res) => res.data?.user)
    );
  }

  updateProfile(updates: Partial<User>) {
    return this.api.patch<{ user: User }>('/users/me', updates).pipe(
      tap((res) => {
        if (res.data) {
          this._user.set(res.data.user);
        }
      }),
      map((res) => res.data?.user)
    );
  }

  uploadAvatar(file: File) {
    const formData = new FormData();
    formData.append('avatar', file);
    
    return this.api.post<{ avatarUrl: string }>('/users/me/avatar', formData).pipe(
      tap((res) => {
        if (res.data && this._user()) {
          this._user.set({ ...this._user()!, avatar: res.data.avatarUrl });
        }
      }),
      map((res) => res.data?.avatarUrl)
    );
  }

  getToken(): string | null {
    if (this.platformId && typeof window !== 'undefined') {
      return localStorage.getItem(ACCESS_TOKEN_KEY);
    }
    return null;
  }

  private setTokens(tokens: AuthTokens): void {
    if (typeof window !== 'undefined') {
      localStorage.setItem(ACCESS_TOKEN_KEY, tokens.accessToken);
      localStorage.setItem(REFRESH_TOKEN_KEY, tokens.refreshToken);
    }
  }

  private clearTokens(): void {
    if (typeof window !== 'undefined') {
      localStorage.removeItem(ACCESS_TOKEN_KEY);
      localStorage.removeItem(REFRESH_TOKEN_KEY);
    }
  }
}
