import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { User } from '../models';

@Injectable({
  providedIn: 'root'
})
export class AuthService {
  private apiUrl = '/api/users';

  constructor(private http: HttpClient) {}

  register(username: string, email: string, password: string): Observable<User> {
    return this.http.post<User>(`${this.apiUrl}/register/`, {
      username,
      email,
      password
    });
  }

  login(username: string, password: string): Observable<any> {
    // Will be implemented - connect to backend login endpoint
    return this.http.post(`${this.apiUrl}/login/`, {
      username,
      password
    });
  }

  getCurrentUser(): Observable<User> {
    return this.http.get<User>(`${this.apiUrl}/me/`);
  }

  logout(): Observable<any> {
    // Clear auth token and return logout response
    return this.http.post(`${this.apiUrl}/logout/`, {});
  }
}
