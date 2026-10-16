"""Borra las cuentas que dejan los tests automáticos.

Los e2e crean una cuenta por prueba (`e2e_...`, `juegos_...`, `culo_...`) y acaban llenando
el ranking de nombres que no son de nadie: en la base de desarrollo había 108 de 196.

Se usa así, **sin borrar nada por defecto** (primero enseña lo que haría):

    python manage.py limpiar_prueba              # enseña lo que borraría
    python manage.py limpiar_prueba --borrar     # lo borra de verdad

Solo toca cuentas cuyo nombre empieza por uno de los prefijos de prueba, y nunca a un
superusuario, así que no hay forma de cargarse una cuenta de verdad por accidente.
"""
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db.models import Q

# Los prefijos que usan los tests y los scripts de verificación del proyecto.
PREFIJOS = ("e2e", "juegos_", "culo_", "diseno", "verifica", "audit", "farm", "ui_", "test")


class Command(BaseCommand):
    help = "Borra las cuentas de prueba (las que crean los tests automáticos)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--borrar",
            action="store_true",
            help="Borra de verdad. Sin esta opción solo enseña lo que haría.",
        )

    def handle(self, *args, **options):
        usuarios = get_user_model()
        filtro = Q()
        for prefijo in PREFIJOS:
            filtro |= Q(username__istartswith=prefijo)
        # Nunca un superusuario: si alguien se llama «test_admin» y es el jefe, se queda.
        candidatos = usuarios.objects.filter(filtro, is_superuser=False)

        total = usuarios.objects.count()
        cuantos = candidatos.count()
        self.stdout.write(f"Cuentas en total: {total}")
        self.stdout.write(f"Cuentas de prueba: {cuantos}")

        if not cuantos:
            self.stdout.write(self.style.SUCCESS("No hay nada que limpiar."))
            return

        if not options["borrar"]:
            for nombre in candidatos.values_list("username", flat=True)[:15]:
                self.stdout.write(f"  - {nombre}")
            if cuantos > 15:
                self.stdout.write(f"  … y {cuantos - 15} más")
            self.stdout.write(
                self.style.WARNING("No se ha borrado nada. Repite con --borrar para hacerlo.")
            )
            return

        borradas, _ = candidatos.delete()
        self.stdout.write(self.style.SUCCESS(f"Borradas {cuantos} cuentas de prueba."))
        self.stdout.write(f"Quedan {usuarios.objects.count()} cuentas.")
        del borradas
