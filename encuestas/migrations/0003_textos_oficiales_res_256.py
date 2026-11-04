"""Las dos preguntas de los indicadores quedan con el texto exacto de las fichas técnicas de la Resolución 256 de
2016 (P.3.14 y P.3.15), para que los conteos se puedan reportar tal cual."""

from django.db import migrations

SATISFACCION = "¿Cómo calificaría su experiencia global respecto a los servicios de salud que ha recibido a través de su IPS?"
RECOMENDACION = "¿Recomendaría a sus familiares y amigos esta IPS?"


def actualizar(apps, schema_editor):
    Pregunta = apps.get_model("encuestas", "Pregunta")
    Pregunta.objects.filter(indicador="satisfaccion").update(texto=SATISFACCION)
    Pregunta.objects.filter(indicador="recomendacion").update(texto=RECOMENDACION)


class Migration(migrations.Migration):
    dependencies = [("encuestas", "0002_initial")]

    operations = [migrations.RunPython(actualizar, migrations.RunPython.noop)]
