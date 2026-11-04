"""Indicadores de satisfacción (Resolución 256 de 2016).

* Satisfacción global = usuarios que respondieron «muy buena» o «buena» ÷ usuarios que respondieron la
  pregunta de satisfacción global × 100.
* Recomendación = usuarios que respondieron «definitivamente sí» o «probablemente sí» ÷ usuarios que
  respondieron la pregunta de recomendación × 100.
"""

from datetime import date, datetime

from django.db.models import Q
from django.utils import timezone

from .models import Pregunta, RespuestaEncuesta, RespuestaItem

POSITIVA = Q(pregunta__escala=Pregunta.Escala.RECOMENDACION, valor__gte=3) | Q(
    pregunta__escala=Pregunta.Escala.CARITAS, valor__gte=4
)


def porcentaje(numerador, denominador):
    return round(numerador * 100 / denominador, 1) if denominador else None


def _rango(qs, campo, desde, hasta):
    if desde:
        qs = qs.filter(**{f"{campo}__gte": desde})
    if hasta:
        qs = qs.filter(**{f"{campo}__lt": hasta})
    return qs


def calcular(institucion, desde=None, hasta=None, servicio=None):
    items = RespuestaItem.objects.filter(respuesta__institucion=institucion, valor__isnull=False)
    items = _rango(items, "respuesta__respondida_en", desde, hasta)
    respuestas = _rango(RespuestaEncuesta.objects.filter(institucion=institucion), "respondida_en", desde, hasta)
    if servicio:
        items = items.filter(respuesta__servicio=servicio)
        respuestas = respuestas.filter(servicio=servicio)
    resultado = {"encuestas": respuestas.count(), "malas": respuestas.filter(requiere_atencion=True).count()}
    for indicador in (Pregunta.Indicador.SATISFACCION, Pregunta.Indicador.RECOMENDACION):
        del_indicador = items.filter(pregunta__indicador=indicador)
        total = del_indicador.count()
        positivas = del_indicador.filter(POSITIVA).count()
        resultado[indicador] = porcentaje(positivas, total)
        resultado[f"{indicador}_numerador"] = positivas
        resultado[f"{indicador}_denominador"] = total
    return resultado


def inicio_de_mes(dia):
    return dia.replace(day=1)


def sumar_meses(dia, meses):
    total = dia.year * 12 + dia.month - 1 + meses
    return date(total // 12, total % 12 + 1, 1)


def a_fecha_hora(dia):
    return timezone.make_aware(datetime(dia.year, dia.month, dia.day))


MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]


def etiqueta_mes(dia):
    return f"{MESES[dia.month - 1]} {dia.year}"


def serie_mensual(institucion, meses=6, hoy=None):
    hoy = hoy or timezone.localdate()
    primero = sumar_meses(inicio_de_mes(hoy), -(meses - 1))
    serie = []
    for i in range(meses):
        desde = sumar_meses(primero, i)
        hasta = sumar_meses(desde, 1)
        datos = calcular(institucion, a_fecha_hora(desde), a_fecha_hora(hasta))
        serie.append({"mes": desde, "etiqueta": etiqueta_mes(desde), **datos})
    return serie
