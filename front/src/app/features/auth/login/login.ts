import { Component, ElementRef, ViewChild, AfterViewInit, inject, signal } from '@angular/core';
import { Router, RouterLink } from '@angular/router';
import { FormBuilder, Validators, ReactiveFormsModule } from '@angular/forms';
import { AuthService } from '../../../core/services/auth.service';
import { NotificationService } from '../../../core/services/notification.service';
import { ButtonComponent } from '../../../shared/components/button/button';
import { InputComponent } from '../../../shared/components/input/input';
import { DividerComponent } from '../../../shared/components/divider/divider';
import { PixelTitleComponent } from '../../../shared/components/pixel-title/pixel-title';
import { environment } from '../../../../environments/environment';

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [RouterLink, ReactiveFormsModule, ButtonComponent, InputComponent, DividerComponent, PixelTitleComponent],
  templateUrl: './login.html',
  styleUrl: './login.scss',
})
export class Login implements AfterViewInit {
  @ViewChild('googleBtn') googleBtnRef!: ElementRef<HTMLDivElement>;

  private readonly fb      = inject(FormBuilder);
  private readonly auth    = inject(AuthService);
  private readonly router  = inject(Router);
  private readonly notif   = inject(NotificationService);

  readonly loading        = this.auth.loading;
  readonly error          = signal('');
  readonly googleEnabled  = !!environment.googleClientId;

  readonly form = this.fb.group({
    email:    ['', [Validators.required]],
    password: ['', [Validators.required, Validators.minLength(6)]],
  });

  ngAfterViewInit(): void {
    if (this.googleEnabled && this.googleBtnRef?.nativeElement) {
      this.auth.renderGoogleButton(this.googleBtnRef.nativeElement);
    }
  }

  fieldError(field: 'email' | 'password'): string {
    const ctrl = this.form.get(field);
    if (!ctrl || !ctrl.touched || !ctrl.errors) return '';
    if (ctrl.errors['required'])  return 'Required';
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
    // Accept either username or email on the login field
    // Backend handles both cases
    this.auth.login(email!, password!).subscribe({
      next: () => {
        this.notif.success('WELCOME BACK', `Logged in as ${email}`);
        // After login, navigate to the embedded game wrapper (MVP)
        this.router.navigate(['/game-wrap']);
      },
      error: (err) => {
        const msg = err?.error?.error ?? 'Login failed. Check your credentials.';
        this.error.set(msg);
      },
    });
  }
}
