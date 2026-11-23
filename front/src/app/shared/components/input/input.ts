import { Component, Input, forwardRef, inject } from '@angular/core';
import { ControlValueAccessor, NG_VALUE_ACCESSOR, ReactiveFormsModule } from '@angular/forms';
import { I18nService } from '../../../i18n/i18n.service';

@Component({
  selector: 'app-input',
  standalone: true,
  imports: [ReactiveFormsModule],
  templateUrl: './input.html',
  styleUrl: './input.scss',
  providers: [
    {
      provide: NG_VALUE_ACCESSOR,
      useExisting: forwardRef(() => InputComponent),
      multi: true,
    },
  ],
})
export class InputComponent implements ControlValueAccessor {
  private readonly i18n = inject(I18nService);

  @Input() label = '';
  @Input() type: 'text' | 'email' | 'password' | 'number' = 'text';
  @Input() placeholder = '';
  @Input() error = '';
  @Input() hint = '';
  @Input() id = `input-${Math.random().toString(36).slice(2, 9)}`;
  @Input() autocomplete = 'off';

  value = '';
  disabled = false;
  showPassword = false;

  private onChange: (v: string) => void = () => {};
  private onTouched: () => void = () => {};

  get inputType(): string {
    if (this.type === 'password') return this.showPassword ? 'text' : 'password';
    return this.type;
  }

  get toggleLabel(): string {
    return this.showPassword ? this.i18n.t('common.hidePassword') : this.i18n.t('common.showPassword');
  }

  get describedBy(): string | null {
    if (this.error) return `${this.id}-error`;
    if (this.hint) return `${this.id}-hint`;
    return null;
  }

  onInput(event: Event) {
    this.value = (event.target as HTMLInputElement).value;
    this.onChange(this.value);
  }

  onBlur() { this.onTouched(); }

  togglePassword() { this.showPassword = !this.showPassword; }

  writeValue(v: string)           { this.value = v ?? ''; }
  registerOnChange(fn: (v: string) => void) { this.onChange = fn; }
  registerOnTouched(fn: () => void)         { this.onTouched = fn; }
  setDisabledState(isDisabled: boolean)     { this.disabled = isDisabled; }
}
