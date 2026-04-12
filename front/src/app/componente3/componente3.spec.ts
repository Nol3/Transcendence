import { ComponentFixture, TestBed } from '@angular/core/testing';

import { Componente3 } from './componente3';

describe('Componente3', () => {
  let component: Componente3;
  let fixture: ComponentFixture<Componente3>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [Componente3],
    }).compileComponents();

    fixture = TestBed.createComponent(Componente3);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
