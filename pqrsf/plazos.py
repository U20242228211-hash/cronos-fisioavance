"""Cálculo de los términos de respuesta de una PQRSF.

La norma usa dos formas de contar:

* **Horas corridas**: se suman horas de reloj sin mirar fines de semana ni festivos. Es como se cuentan los
  reclamos en salud según su riesgo (24, 48 o 72 horas).
* **Días hábiles**: de lunes a viernes, sin festivos (Ley 1755 de 2015). El término empieza a correr el día
  siguiente a la recepción y vence al terminar el último día hábil.

Los festivos salen de la librería ``holidays``, que ya trae la Ley Emiliani de Colombia y los de otros países
para cuando Cronos se use fuera.
"""

from datetime import datetime, time, timedelta
from functools import lru_cache

import holidays
from django.utils import timezone

HORAS = "horas"
DIAS_HABILES = "dias_habiles"

UMBRAL_AMARILLO = 50
UMBRAL_ROJO = 80


@lru_cache(maxsize=128)
def _festivos(pais, anio):
    return frozenset(holidays.country_holidays(pais, years=anio).keys())


def es_festivo(dia, pais="CO"):
    return dia in _festivos(pais, dia.year)


def es_habil(dia, pais="CO"):
    return dia.weekday() < 5 and not es_festivo(dia, pais)


def sumar_dias_habiles(inicio, dias, pais="CO"):
    local = timezone.localtime(inicio)
    dia = local.date()
    contados = 0
    while contados < dias:
        dia += timedelta(days=1)
        if es_habil(dia, pais):
            contados += 1
    return timezone.make_aware(datetime.combine(dia, time(23, 59, 59)), local.tzinfo)


def calcular_vencimiento(inicio, cantidad, unidad, pais="CO"):
    if unidad == HORAS:
        return inicio + timedelta(hours=cantidad)
    if unidad == DIAS_HABILES:
        return sumar_dias_habiles(inicio, cantidad, pais)
    raise ValueError(f"Unidad de plazo desconocida: {unidad}")


def dias_habiles_entre(inicio, fin, pais="CO"):
    """Días hábiles que pasaron desde el día siguiente a ``inicio`` hasta el día de ``fin``, incluido."""
    dia = timezone.localtime(inicio).date()
    ultimo = timezone.localtime(fin).date()
    contados = 0
    while dia < ultimo:
        dia += timedelta(days=1)
        if es_habil(dia, pais):
            contados += 1
    return contados


def porcentaje_transcurrido(inicio, vence, ahora):
    total = (vence - inicio).total_seconds()
    if total <= 0:
        return 100.0
    return max(0.0, (ahora - inicio).total_seconds() * 100 / total)


def semaforo(porcentaje):
    """verde, amarillo, rojo o vencida según cuánto del plazo ya pasó."""
    if porcentaje >= 100:
        return "vencida"
    if porcentaje >= UMBRAL_ROJO:
        return "rojo"
    if porcentaje >= UMBRAL_AMARILLO:
        return "amarillo"
    return "verde"
