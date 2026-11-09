import { Component, inject, signal } from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';
import {
  AbstractControl,
  FormBuilder,
  ReactiveFormsModule,
  ValidationErrors,
  Validators,
} from '@angular/forms';
import { AuthService } from '../../../core/services/auth.service';
import { I18nService } from '../../../i18n/i18n.service';
import { TranslatePipe } from '../../../i18n/translate.pipe';
import { ButtonComponent } from '../../../shared/components/button/button';
import { InputComponent } from '../../../shared/components/input/input';
import { PixelTitleComponent } from '../../../shared/components/pixel-title/pixel-title';

/** Las dos contraseñas tienen que ser la misma (Angular no trae este validador). */
function coinciden(grupo: AbstractControl): ValidationErrors | null {
  const password = grupo.get('password')?.value;
  const repetida = grupo.get('password2')?.value;
  return password && repetida && password !== repetida ? { noCoinciden: true } : null;
}

@Component({
  selector: 'app-reset-password',
  standalone: true,
  imports: [
    RouterLink,
    ReactiveFormsModule,
    ButtonComponent,
    InputComponent,
    PixelTitleComponent,
    TranslatePipe,
  ],
  templateUrl: './reset-password.html',
  styleUrl: '../auth-card.scss',
})
export class ResetPassword {
  private readonly fb = inject(FormBuilder);
  private readonly auth = inject(AuthService);
  private readonly i18n = inject(I18nService);
  private readonly ruta = inject(ActivatedRoute);

  private readonly uid = this.ruta.snapshot.queryParamMap.get('uid') ?? '';
  private readonly token = this.ruta.snapshot.queryParamMap.get('token') ?? '';

  /** Sin `uid` y `token` en la URL no hay nada que canjear: se avisa en vez de enseñar el form. */
  readonly enlaceInvalido = !this.uid || !this.token;
  readonly loading = signal(false);
  readonly hecho = signal(false);
  readonly error = signal('');

  readonly form = this.fb.nonNullable.group(
    {
      password: ['', [Validators.required, Validators.minLength(8)]],
      password2: ['', [Validators.required]],
    },
    { validators: coinciden },
  );

  fieldError(field: 'password' | 'password2'): string {
    const ctrl = this.form.get(field);
    if (this.form.errors?.['noCoinciden'] && field === 'password2' && ctrl?.touched) {
      return this.i18n.t('auth.reset.mismatch');
    }
    if (!ctrl || !ctrl.touched || !ctrl.errors) return '';
    if (ctrl.errors['required']) return this.i18n.t('auth.errors.required');
    if (ctrl.errors['minlength']) {
      return this.i18n.t('auth.errors.minlength', { n: ctrl.errors['minlength'].requiredLength });
    }
    return '';
  }

  onSubmit() {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }
    this.error.set('');
    this.loading.set(true);
    this.auth.resetPassword(this.uid, this.token, this.form.getRawValue().password).subscribe({
      next: () => {
        this.loading.set(false);
        this.hecho.set(true);
      },
      error: (err) => {
        this.loading.set(false);
        // El servidor dice si el enlace caducó o ya se usó; si no, el mensaje genérico.
        this.error.set(err?.error?.error ?? this.i18n.t('auth.errors.generic'));
      },
    });
  }
}
