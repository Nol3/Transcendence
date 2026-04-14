import { Component, Input } from '@angular/core';

@Component({
  selector: 'app-pixel-title',
  standalone: true,
  templateUrl: './pixel-title.html',
  styleUrl: './pixel-title.scss',
})
export class PixelTitleComponent {
  @Input() level: 1 | 2 | 3 = 1;
  @Input() color: 'cyan' | 'magenta' | 'yellow' | 'green' = 'cyan';
  @Input() flicker = false;
}
