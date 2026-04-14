import { Component, inject, signal } from '@angular/core';
import { Router, RouterLink } from '@angular/router';
import { FormBuilder, Validators, ReactiveFormsModule } from '@angular/forms';
import { AuthService } from '../../../core/services/auth.service';
import { NotificationService } from '../../../core/services/notification.service';
import { ButtonComponent } from '../../../shared/components/button/button';
import { InputComponent } from '../../../shared/components/input/input';
import { DividerComponent } from '../../../shared/components/divider/divider';
import { PixelTitleComponent } from '../../../shared/components/pixel-title/pixel-title';

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [RouterLink, ReactiveFormsModule, ButtonComponent, InputComponent, DividerComponent, PixelTitleComponent],
  templateUrl: './login.html',
  styleUrl: './login.scss',
})
export class Login {
  private readonly fb      = inject(FormBuilder);
  private readonly auth    = inject(AuthService);
  private readonly router  = inject(Router);
  private readonly notif   = inject(NotificationService);

  readonly loading = this.auth.loading;
  readonly error   = signal('');

  readonly form = this.fb.group({
    email:    ['', [Validators.required, Validators.email]],
    password: ['', [Validators.required, Validators.minLength(6)]],
  });

  fieldError(field: 'email' | 'password'): string {
    const ctrl = this.form.get(field);
    if (!ctrl || !ctrl.touched || !ctrl.errors) return '';
    if (ctrl.errors['required'])  return 'Required';
    if (ctrl.errors['email'])     return 'Invalid email format';
    if (ctrl.errors['minlength']) return `Min ${ctrl.errors['minlength'].requiredLength} characters`;
    return '';
  }

  onSubmit() {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }
    this.error.set('');
    const { email, password } = this.form.getRawValue();

    this.auth.login(email!, password!).subscribe({
      next: () => {
        this.notif.success('WELCOME BACK', `Logged in as ${email}`);
        this.router.navigate(['/']);
      },
      error: (err) => {
        const msg = err?.error?.error ?? 'Login failed. Check your credentials.';
        this.error.set(msg);
      },
    });
  }
}
