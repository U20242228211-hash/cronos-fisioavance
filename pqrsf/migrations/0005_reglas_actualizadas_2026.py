"""Términos actualizados con la norma vigente a noviembre de 2026.

* Supersalud, Circular Externa 2026151000000007-5 (6 de junio de 2026): los reclamos de riesgo vital de niños,
  niñas y adolescentes se resuelven en máximo 8 horas corridas desde la radicación, e incluye a las IPS.
* Circular Única, Título VII, num. 3.3.2.4 c): las copias se entregan en 3 días hábiles.
* Una queja relacionada con la atención se trata como reclamo según su riesgo (num. 3.3: prevalece lo más
  favorable al usuario).
* Sugerencias y felicitaciones no tienen término legal: se deja el general de la Ley 1755 como buena práctica.
"""

from django.db import migrations

CU = "Circular Única Supersalud, Título VII, num. 3.3.2 (CE 2023151000000010-5 de 2023)"
NNA = "Supersalud, CE 2026151000000007-5 de 2026, instrucción 3ª"
FAVORABLE = "Circular Única, Título VII, num. 3.3: se aplica lo más favorable al usuario"

REGLAS = [
    ("R", "vital_nna", 8, "horas", NNA),
    ("R", "vital", 24, "horas", f"{CU}.3"),
    ("R", "priorizado", 48, "horas", f"{CU}.2"),
    ("R", "simple", 72, "horas", f"{CU}.1"),
    ("Q", "vital_nna", 8, "horas", f"{NNA}; {FAVORABLE}"),
    ("Q", "vital", 24, "horas", FAVORABLE),
    ("Q", "priorizado", 48, "horas", FAVORABLE),
    ("Q", "simple", 72, "horas", FAVORABLE),
    ("Q", "general", 15, "dias_habiles", "Ley 1755 de 2015, art. 14 (queja que no tiene que ver con la atención)"),
    ("P", "general", 15, "dias_habiles", "Ley 1755 de 2015, art. 14; Circular Única num. 3.3.2.4 a)"),
    ("P", "informacion", 10, "dias_habiles", "Ley 1755 de 2015, art. 14 num. 1; Circular Única num. 3.3.2.4 b)"),
    ("P", "copias", 3, "dias_habiles", "Circular Única, Título VII, num. 3.3.2.4 c)"),
    ("P", "consulta", 30, "dias_habiles", "Ley 1755 de 2015, art. 14 num. 2"),
    ("S", "general", 15, "dias_habiles", "Sin término legal: buena práctica con el término general de la Ley 1755"),
    ("F", "general", 15, "dias_habiles", "Sin término legal: buena práctica con el término general de la Ley 1755"),
]


def actualizar(apps, schema_editor):
    ReglaPlazo = apps.get_model("pqrsf", "ReglaPlazo")
    for tipo, clasificacion, cantidad, unidad, norma in REGLAS:
        ReglaPlazo.objects.update_or_create(
            institucion=None, tipo=tipo, clasificacion=clasificacion,
            defaults={"cantidad": cantidad, "unidad": unidad, "norma": norma},
        )


class Migration(migrations.Migration):
    dependencies = [("pqrsf", "0004_pqrsf_accion_realizada_pqrsf_departamento_and_more")]

    operations = [migrations.RunPython(actualizar, migrations.RunPython.noop)]
