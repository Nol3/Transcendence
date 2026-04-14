import { Component } from '@angular/core';
import { CardComponent } from '../../../shared/components/card/card';
import { PixelTitleComponent } from '../../../shared/components/pixel-title/pixel-title';
import { TranslatePipe } from '../../../i18n/translate.pipe';

@Component({
  selector: 'app-terms',
  standalone: true,
  imports: [CardComponent, PixelTitleComponent, TranslatePipe],
  templateUrl: './terms.html',
  styleUrl: './terms.scss',
})
export class TermsComponent {}
