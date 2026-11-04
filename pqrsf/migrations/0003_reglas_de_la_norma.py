"""Términos de respuesta de la norma colombiana, para todas las instituciones.

Cada institución puede agregar los suyos (más estrictos) desde «Términos de respuesta».
"""

from django.db import migrations

CIRCULAR = "Supersalud, Circular Externa 2023151000000010-5 de 2023"
LEY_1755 = "Ley 1755 de 2015, art. 14"

REGLAS = [
    ("R", "vital", 24, "horas", CIRCULAR),
    ("R", "priorizado", 48, "horas", CIRCULAR),
    ("R", "simple", 72, "horas", CIRCULAR),
    ("P", "general", 15, "dias_habiles", LEY_1755),
    ("P", "informacion", 10, "dias_habiles", f"{LEY_1755}, num. 1"),
    ("P", "consulta", 30, "dias_habiles", f"{LEY_1755}, num. 2"),
    ("Q", "general", 15, "dias_habiles", LEY_1755),
    ("S", "general", 15, "dias_habiles", f"{LEY_1755} (se aplica el término general)"),
    ("F", "general", 15, "dias_habiles", f"{LEY_1755} (se aplica el término general)"),
]


def crear(apps, schema_editor):
    ReglaPlazo = apps.get_model("pqrsf", "ReglaPlazo")
    for tipo, clasificacion, cantidad, unidad, norma in REGLAS:
        ReglaPlazo.objects.update_or_create(
            institucion=None,
            tipo=tipo,
            clasificacion=clasificacion,
            defaults={"cantidad": cantidad, "unidad": unidad, "norma": norma},
        )


def borrar(apps, schema_editor):
    apps.get_model("pqrsf", "ReglaPlazo").objects.filter(institucion=None).delete()


class Migration(migrations.Migration):
    dependencies = [("pqrsf", "0002_initial")]

    operations = [migrations.RunPython(crear, borrar)]
