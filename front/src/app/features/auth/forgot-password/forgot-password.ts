import { Component, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { AuthService } from '../../../core/services/auth.service';
import { I18nService } from '../../../i18n/i18n.service';
import { TranslatePipe } from '../../../i18n/translate.pipe';
import { ButtonComponent } from '../../../shared/components/button/button';
import { InputComponent } from '../../../shared/components/input/input';
import { PixelTitleComponent } from '../../../shared/components/pixel-title/pixel-title';

@Component({
  selector: 'app-forgot-password',
  standalone: true,
  imports: [
    RouterLink,
    ReactiveFormsModule,
    ButtonComponent,
    InputComponent,
    PixelTitleComponent,
    TranslatePipe,
  ],
  templateUrl: './forgot-password.html',
  // Estilos compartidos con la pantalla de canjear el enlace (misma tarjeta).
  styleUrl: '../auth-card.scss',
})
export class ForgotPassword {
  private readonly fb = inject(FormBuilder);
  private readonly auth = inject(AuthService);
  private readonly i18n = inject(I18nService);

  readonly loading = signal(false);
  readonly enviado = signal(false);
  readonly error = signal('');

  readonly form = this.fb.nonNullable.group({
    email: ['', [Validators.required, Validators.email]],
  });

  fieldError(): string {
    const ctrl = this.form.get('email');
    if (!ctrl || !ctrl.touched || !ctrl.errors) return '';
    if (ctrl.errors['required']) return this.i18n.t('auth.errors.required');
    if (ctrl.errors['email']) return this.i18n.t('auth.errors.email');
    return '';
  }

  onSubmit() {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }
    this.error.set('');
    this.loading.set(true);
    // La respuesta es siempre la misma, exista o no la cuenta: sirve para no poder averiguar
    // qué correos están registrados. Por eso, pase lo que pase, se enseña el mismo mensaje.
    this.auth.requestPasswordReset(this.form.getRawValue().email).subscribe({
      next: () => {
        this.loading.set(false);
        this.enviado.set(true);
      },
      error: (err) => {
        this.loading.set(false);
        this.error.set(err?.error?.error ?? this.i18n.t('auth.errors.generic'));
      },
    });
  }
}
