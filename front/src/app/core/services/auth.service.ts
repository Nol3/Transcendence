import { Injectable, inject, signal, computed } from '@angular/core';
import { Router } from '@angular/router';
import { tap, map } from 'rxjs/operators';
import { ApiService } from './api.service';
import { User, AuthTokens } from '../models/user.model';

@Injectable({ providedIn: 'root' })
export class AuthService {
  private readonly api = inject(ApiService);
  private readonly router = inject(Router);

  private readonly _user = signal<User | null>(null);
  private readonly _loading = signal(false);

  readonly user = this._user.asReadonly();
  readonly loading = this._loading.asReadonly();
  readonly isAuthenticated = computed(() => this._user() !== null);

  login(email: string, password: string) {
    this._loading.set(true);
    return this.api.post<{ user: User; tokens: AuthTokens }>('/auth/login', { email, password }).pipe(
      tap({
        next: (res) => {
          if (res.data) {
            this._user.set(res.data.user);
            localStorage.setItem('access_token', res.data.tokens.accessToken);
            localStorage.setItem('refresh_token', res.data.tokens.refreshToken);
          }
          this._loading.set(false);
        },
        error: () => this._loading.set(false),
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
            localStorage.setItem('access_token', res.data.tokens.accessToken);
            localStorage.setItem('refresh_token', res.data.tokens.refreshToken);
          }
          this._loading.set(false);
        },
        error: () => this._loading.set(false),
      }),
      map((res) => res.data)
    );
  }

  logout() {
    this._user.set(null);
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    this.router.navigate(['/login']);
  }

  getToken(): string | null {
    return localStorage.getItem('access_token');
  }
}
