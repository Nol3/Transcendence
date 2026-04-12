import { ComponentFixture, TestBed } from '@angular/core/testing';

import { Componente2 } from './componente2';

describe('Componente2', () => {
  let component: Componente2;
  let fixture: ComponentFixture<Componente2>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [Componente2],
    }).compileComponents();

    fixture = TestBed.createComponent(Componente2);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
