import { Component, Input, Output, EventEmitter, HostListener } from '@angular/core';

@Component({
  selector: 'app-modal',
  standalone: true,
  templateUrl: './modal.html',
  styleUrl: './modal.scss',
})
export class ModalComponent {
  @Input() open = false;
  @Input() title = '';
  @Input() closable = true;
  @Output() closed = new EventEmitter<void>();

  close() {
    if (this.closable) this.closed.emit();
  }

  @HostListener('keydown.escape')
  onEscape() { this.close(); }
}
