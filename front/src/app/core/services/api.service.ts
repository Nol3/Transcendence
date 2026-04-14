import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpHeaders, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';
import { ApiResponse, PaginatedResponse } from '../models/api-response.model';

@Injectable({ providedIn: 'root' })
export class ApiService {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = environment.apiUrl;

  get<T>(endpoint: string, params?: Record<string, string>): Observable<ApiResponse<T>> {
    const httpParams = params ? new HttpParams({ fromObject: params }) : undefined;
    return this.http.get<ApiResponse<T>>(`${this.baseUrl}${endpoint}`, { params: httpParams });
  }

  getFullUrl<T>(url: string): Observable<ApiResponse<T>> {
    return this.http.get<ApiResponse<T>>(url);
  }

  getPaginated<T>(endpoint: string, params?: Record<string, string>): Observable<PaginatedResponse<T>> {
    const httpParams = params ? new HttpParams({ fromObject: params }) : undefined;
    return this.http.get<PaginatedResponse<T>>(`${this.baseUrl}${endpoint}`, { params: httpParams });
  }

  post<T>(endpoint: string, body: unknown): Observable<ApiResponse<T>> {
    return this.http.post<ApiResponse<T>>(`${this.baseUrl}${endpoint}`, body);
  }

  put<T>(endpoint: string, body: unknown): Observable<ApiResponse<T>> {
    return this.http.put<ApiResponse<T>>(`${this.baseUrl}${endpoint}`, body);
  }

  patch<T>(endpoint: string, body: unknown): Observable<ApiResponse<T>> {
    return this.http.patch<ApiResponse<T>>(`${this.baseUrl}${endpoint}`, body);
  }

  delete<T>(endpoint: string): Observable<ApiResponse<T>> {
    return this.http.delete<ApiResponse<T>>(`${this.baseUrl}${endpoint}`);
  }

  withApiKey(key: string): HttpHeaders {
    return new HttpHeaders({ 'X-API-Key': key });
  }
}
