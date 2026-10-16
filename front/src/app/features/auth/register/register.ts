import { Component, inject, signal } from '@angular/core';
import { Router, RouterLink } from '@angular/router';
import { FormBuilder, Validators, ReactiveFormsModule, AbstractControl, ValidationErrors } from '@angular/forms';
import { AuthService } from '../../../core/services/auth.service';
import { NotificationService } from '../../../core/services/notification.service';
import { ButtonComponent } from '../../../shared/components/button/button';
import { InputComponent } from '../../../shared/components/input/input';
import { DividerComponent } from '../../../shared/components/divider/divider';
import { PixelTitleComponent } from '../../../shared/components/pixel-title/pixel-title';
import { TranslatePipe } from '../../../i18n/translate.pipe';
import { I18nService } from '../../../i18n/i18n.service';

function passwordsMatch(group: AbstractControl): ValidationErrors | null {
  const pw  = group.get('password')?.value;
  const cpw = group.get('confirmPassword')?.value;
  return pw && cpw && pw !== cpw ? { passwordsMismatch: true } : null;
}

@Component({
  selector: 'app-register',
  standalone: true,
  imports: [RouterLink, ReactiveFormsModule, ButtonComponent, InputComponent, DividerComponent, PixelTitleComponent, TranslatePipe],
  templateUrl: './register.html',
  styleUrl: './register.scss',
})
export class Register {
  private readonly fb     = inject(FormBuilder);
  private readonly auth   = inject(AuthService);
  private readonly router = inject(Router);
  private readonly notif  = inject(NotificationService);
  private readonly i18n   = inject(I18nService);

  readonly loading = this.auth.loading;
  readonly error   = signal('');

  readonly form = this.fb.group(
    {
      username:        ['', [Validators.required, Validators.minLength(3), Validators.maxLength(20), Validators.pattern(/^[a-zA-Z0-9_]+$/)]],
      email:           ['', [Validators.required, Validators.email]],
      password:        ['', [Validators.required, Validators.minLength(8)]],
      confirmPassword: ['', Validators.required],
    },
    { validators: passwordsMatch }
  );

  fieldError(field: 'username' | 'email' | 'password' | 'confirmPassword'): string {
    const ctrl = this.form.get(field);
    if (!ctrl || !ctrl.touched) return '';

    if (field === 'confirmPassword' && ctrl.touched && this.form.errors?.['passwordsMismatch']) {
      return 'Passwords do not match';
    }

    if (!ctrl.errors) return '';
    // Por el servicio de idioma, no a mano: ver el mismo arreglo en `login.ts`.
    if (ctrl.errors['required'])   return this.i18n.t('auth.errors.required');
    if (ctrl.errors['email'])      return 'Invalid email format';
    if (ctrl.errors['minlength']) {
      return this.i18n.t('auth.errors.minlength', { n: ctrl.errors['minlength'].requiredLength });
    }
    if (ctrl.errors['maxlength']) {
      return this.i18n.t('auth.errors.maxlength', { n: ctrl.errors['maxlength'].requiredLength });
    }
    if (ctrl.errors['pattern'])    return 'Only letters, numbers and underscore';
    return '';
  }

  onSubmit() {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }
    this.error.set('');
    const { username, email, password } = this.form.getRawValue();

    this.auth.register(username!, email!, password!).subscribe({
      next: () => {
        this.notif.success(this.i18n.t('notify.register.title'),
          this.i18n.t('notify.register.body', { username: username ?? '' }));
        this.router.navigate(['/']);
      },
      error: (err) => {
        const msg = err?.error?.error ?? this.i18n.t('auth.errors.registerFailed');
        this.error.set(msg);
      },
    });
  }
}
