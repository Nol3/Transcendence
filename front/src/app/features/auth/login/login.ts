import { Component, ElementRef, ViewChild, AfterViewInit, inject, signal } from '@angular/core';
import { Router, RouterLink } from '@angular/router';
import { FormBuilder, Validators, ReactiveFormsModule } from '@angular/forms';
import { AuthService } from '../../../core/services/auth.service';
import { NotificationService } from '../../../core/services/notification.service';
import { ButtonComponent } from '../../../shared/components/button/button';
import { InputComponent } from '../../../shared/components/input/input';
import { DividerComponent } from '../../../shared/components/divider/divider';
import { PixelTitleComponent } from '../../../shared/components/pixel-title/pixel-title';
import { TranslatePipe } from '../../../i18n/translate.pipe';
import { I18nService } from '../../../i18n/i18n.service';
import { environment } from '../../../../environments/environment';

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [RouterLink, ReactiveFormsModule, ButtonComponent, InputComponent, DividerComponent, PixelTitleComponent, TranslatePipe],
  templateUrl: './login.html',
  styleUrl: './login.scss',
})
export class Login implements AfterViewInit {
  @ViewChild('googleBtn') googleBtnRef!: ElementRef<HTMLDivElement>;

  private readonly fb      = inject(FormBuilder);
  private readonly auth    = inject(AuthService);
  private readonly router  = inject(Router);
  private readonly notif   = inject(NotificationService);
  private readonly i18n    = inject(I18nService);

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
    // Los mensajes van por el servicio de idioma: estaban escritos a mano en inglés, así que
    // en la versión española o francesa el formulario avisaba en inglés.
    if (ctrl.errors['required'])  return this.i18n.t('auth.errors.required');
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
    const { email, password } = this.form.getRawValue();
    // Accept either username or email on the login field
    // Backend handles both cases
    this.auth.login(email!, password!).subscribe({
      next: () => {
        this.notif.success(this.i18n.t('notify.login.title'),
          this.i18n.t('notify.login.body', { email: email ?? '' }));
        // After login, navigate to the embedded game wrapper (MVP)
        this.router.navigate(['/']);
      },
      error: (err) => {
        const msg = err?.error?.error ?? this.i18n.t('auth.errors.loginFailed');
        this.error.set(msg);
      },
    });
  }
}
