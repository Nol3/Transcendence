import { Component, Input } from '@angular/core';

@Component({
  selector: 'app-card',
  standalone: true,
  templateUrl: './card.html',
  styleUrl: './card.scss',
})
export class CardComponent {
  @Input() title = '';
  @Input() glowing = false;
  @Input() padding: 'sm' | 'md' | 'lg' = 'md';
}
