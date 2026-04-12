import { ComponentFixture, TestBed } from '@angular/core/testing';

import { Componente1 } from './componente1';

describe('Componente1', () => {
  let component: Componente1;
  let fixture: ComponentFixture<Componente1>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [Componente1],
    }).compileComponents();

    fixture = TestBed.createComponent(Componente1);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
