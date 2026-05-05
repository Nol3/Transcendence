import { HttpInterceptorFn, HttpErrorResponse } from '@angular/common/http';
import { inject } from '@angular/core';
import { catchError, switchMap, throwError, finalize } from 'rxjs';
import { AuthService } from '../services/auth.service';

let isRefreshing = false;

export const authInterceptor: HttpInterceptorFn = (req, next) => {
  const auth = inject(AuthService);
  const token = auth.getToken();

  // No agregar header si es refresh o logout
  if (req.url.includes('/auth/refresh') || req.url.includes('/auth/logout')) {
    return next(req);
  }

  const authReq = token
    ? req.clone({ setHeaders: { Authorization: `Bearer ${token}` } })
    : req;

  return next(authReq).pipe(
    catchError((error: HttpErrorResponse) => {
      // Solo hacer refresh una vez
      if (error.status === 401 && !isRefreshing && token) {
        isRefreshing = true;
        return auth.refreshToken().pipe(
          switchMap((tokens) => {
            isRefreshing = false;
            if (tokens) {
              const retryReq = req.clone({
                setHeaders: { Authorization: `Bearer ${tokens.accessToken}` },
              });
              return next(retryReq);
            }
            // Si el refresh falló silenciosamente, no hacer nada
            return throwError(() => error);
          }),
          catchError((err) => {
            isRefreshing = false;
            // Al fallar refresh, logout y rechazar la petición
            auth.logout();
            return throwError(() => err);
          })
        );
      }
      return throwError(() => error);
    })
  );
};
