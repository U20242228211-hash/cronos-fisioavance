"""Tablero, reportes y material para imprimir (carteles con QR y avisos)."""

import json
from datetime import timedelta

from django.contrib import admin
from django.contrib.admin.views.decorators import staff_member_required
from django.core.exceptions import PermissionDenied
from django.db.models import Count
from django.shortcuts import render
from django.urls import reverse
from django.utils import timezone

from encuestas import indicadores
from encuestas.models import RespuestaEncuesta
from instituciones.admin_base import GESTION, es_plataforma, tiene_rol
from instituciones.models import Institucion, Servicio
from pqrsf import plazos
from pqrsf.models import PQRSF, Tipo

from . import exportar

ABIERTAS = [PQRSF.Estado.RADICADA, PQRSF.Estado.EN_TRAMITE]
COLORES_TIPO = {"P": "#2e90fa", "Q": "#f79009", "R": "#f04438", "S": "#7a5af8", "F": "#12b76a"}


def institucion_de(request):
    if getattr(request.user, "institucion", None):
        return request.user.institucion
    if es_plataforma(request):
        slug = request.GET.get("institucion")
        qs = Institucion.objects.filter(activa=True)
        return (qs.filter(slug=slug).first() if slug else None) or qs.first()
    return None


def requiere_gestion(vista):
    @staff_member_required
    def envoltura(request, *args, **kwargs):
        if not tiene_rol(request, GESTION):
            raise PermissionDenied
        return vista(request, *args, **kwargs)

    envoltura.__name__ = vista.__name__
    return envoltura


def resumen_pqrsf(institucion, desde=None, hasta=None):
    qs = PQRSF.objects.filter(institucion=institucion)
    if desde:
        qs = qs.filter(recibida_en__gte=desde)
    if hasta:
        qs = qs.filter(recibida_en__lt=hasta)
    respondidas = [p for p in qs.exclude(respondida_en=None).only("recibida_en", "respondida_en", "vence_en")]
    a_tiempo = sum(1 for p in respondidas if p.respondida_a_tiempo)
    dias = [plazos.dias_habiles_entre(p.recibida_en, p.respondida_en, institucion.pais) for p in respondidas]
    horas = [(p.respondida_en - p.recibida_en).total_seconds() / 3600 for p in respondidas]
    return {
        "total": qs.count(),
        "respondidas": len(respondidas),
        "a_tiempo": a_tiempo,
        "oportunidad": indicadores.porcentaje(a_tiempo, len(respondidas)),
        "dias_promedio": round(sum(dias) / len(dias), 1) if dias else None,
        "horas_promedio": round(sum(horas) / len(horas), 1) if horas else None,
        "por_tipo": _contar(qs, "tipo", Tipo.choices),
        "por_estado": _contar(qs, "estado", PQRSF.Estado.choices),
        "por_canal": _contar(qs, "canal", PQRSF.Canal.choices),
        "por_clasificacion": _contar(qs, "clasificacion", PQRSF._meta.get_field("clasificacion").choices),
        "por_servicio": list(qs.values("servicio__nombre").annotate(n=Count("id")).order_by("-n")),
    }


def _contar(qs, campo, opciones):
    conteo = dict(qs.values_list(campo).annotate(n=Count("id")))
    return [{"valor": v, "texto": t, "n": conteo.get(v, 0)} for v, t in opciones if conteo.get(v, 0)]


def dashboard_callback(request, context):
    institucion = institucion_de(request)
    if institucion is None or not tiene_rol(request, GESTION):
        context["sin_tablero"] = True
        return context
    ahora = timezone.now()
    abiertas = list(
        PQRSF.objects.filter(institucion=institucion, estado__in=ABIERTAS).select_related("servicio", "asignada_a")
    )
    for p in abiertas:
        p.pct = p.porcentaje(ahora)
        p.luz = plazos.semaforo(p.pct)
    vencidas = [p for p in abiertas if p.luz == "vencida"]
    por_vencer = [p for p in abiertas if p.luz == "rojo"]
    sin_confirmar = [p for p in abiertas if not p.clasificacion_confirmada]
    hace_90 = ahora - timedelta(days=90)
    resumen_90 = resumen_pqrsf(institucion, hace_90)
    inicio_mes = indicadores.a_fecha_hora(timezone.localdate().replace(day=1))
    del_mes = resumen_pqrsf(institucion, inicio_mes)

    serie = indicadores.serie_mensual(institucion, meses=6)
    meses = [m["etiqueta"] for m in serie]
    satisfaccion_mes = indicadores.calcular(institucion, ahora - timedelta(days=30))
    malas_sin_revisar = RespuestaEncuesta.objects.filter(
        institucion=institucion, requiere_atencion=True, atendida=False
    ).select_related("servicio")[:5]

    # PQRSF por tipo, mes a mes
    datasets = []
    for valor, texto in Tipo.choices:
        datos = []
        for m in serie:
            desde = indicadores.a_fecha_hora(m["mes"])
            hasta = indicadores.a_fecha_hora(indicadores.sumar_meses(m["mes"], 1))
            datos.append(PQRSF.objects.filter(institucion=institucion, tipo=valor, recibida_en__gte=desde, recibida_en__lt=hasta).count())
        datasets.append({"label": texto, "data": datos, "backgroundColor": COLORES_TIPO[valor], "maxBarThickness": 28})
    grafica_pqrsf = {"labels": meses, "datasets": datasets}
    grafica_satisfaccion = {
        "labels": meses,
        "datasets": [
            {"label": "Satisfacción global (%)", "data": [m["satisfaccion"] for m in serie], "borderColor": "#0f9488", "backgroundColor": "#0f948833", "fill": True, "tension": 0.35},
            {"label": "Recomendaría la IPS (%)", "data": [m["recomendacion"] for m in serie], "borderColor": "#7a5af8", "backgroundColor": "#7a5af822", "fill": False, "tension": 0.35},
        ],
    }
    opciones_barras = {"scales": {"x": {"stacked": True}, "y": {"stacked": True, "ticks": {"precision": 0}}}, "plugins": {"legend": {"display": True, "position": "bottom"}}}
    opciones_lineas = {"scales": {"y": {"min": 0, "max": 100}}, "plugins": {"legend": {"display": True, "position": "bottom"}}}

    context.update(
        {
            "institucion": institucion,
            "kpi": {
                "abiertas": len(abiertas),
                "vencidas": len(vencidas),
                "por_vencer": len(por_vencer),
                "sin_confirmar": len(sin_confirmar),
                "del_mes": del_mes["total"],
                "oportunidad": resumen_90["oportunidad"],
                "dias_promedio": resumen_90["dias_promedio"],
                "satisfaccion": satisfaccion_mes["satisfaccion"],
                "recomendacion": satisfaccion_mes["recomendacion"],
                "encuestas_mes": satisfaccion_mes["encuestas"],
                "malas": RespuestaEncuesta.objects.filter(institucion=institucion, requiere_atencion=True, atendida=False).count(),
            },
            "atender": sorted(abiertas, key=lambda p: p.vence_en or ahora)[:8],
            "malas_sin_revisar": malas_sin_revisar,
            "grafica_pqrsf": json.dumps(grafica_pqrsf),
            "grafica_satisfaccion": json.dumps(grafica_satisfaccion),
            "opciones_barras": json.dumps(opciones_barras),
            "opciones_lineas": json.dumps(opciones_lineas),
            "url_bandeja": reverse("admin:pqrsf_pqrsf_changelist"),
            "url_portal": reverse("portal:inicio", kwargs={"slug": institucion.slug}),
        }
    )
    return context


def _periodo(request):
    hoy = timezone.localdate()
    texto = request.GET.get("mes") or f"{hoy:%Y-%m}"
    try:
        anio, mes = (int(x) for x in texto.split("-"))
        primero = hoy.replace(year=anio, month=mes, day=1)
    except ValueError:
        primero = hoy.replace(day=1)
    siguiente = indicadores.sumar_meses(primero, 1)
    return primero, indicadores.a_fecha_hora(primero), indicadores.a_fecha_hora(siguiente)


@requiere_gestion
def reportes(request):
    institucion = institucion_de(request)
    primero, desde, hasta = _periodo(request)
    if request.GET.get("descargar"):
        return exportar.descargar(request.GET["descargar"], institucion, desde, hasta, primero)
    por_servicio = [
        {"servicio": s, **indicadores.calcular(institucion, desde, hasta, servicio=s)}
        for s in Servicio.objects.filter(institucion=institucion, activo=True)
    ]
    contexto = {
        **admin.site.each_context(request),
        "title": "Reportes",
        "institucion": institucion,
        "mes": f"{primero:%Y-%m}",
        "etiqueta_mes": indicadores.etiqueta_mes(primero),
        "pqrsf": resumen_pqrsf(institucion, desde, hasta),
        "satisfaccion": indicadores.calcular(institucion, desde, hasta),
        "por_servicio": [s for s in por_servicio if s["encuestas"]],
    }
    return render(request, "tablero/reportes.html", contexto)


@requiere_gestion
def carteles(request):
    institucion = institucion_de(request)
    return render(request, "tablero/carteles.html", {"institucion": institucion})


@requiere_gestion
def avisos(request):
    institucion = institucion_de(request)
    hoy = timezone.localdate()
    publicados = PQRSF.objects.filter(institucion=institucion, anonima=True, aviso_hasta__gte=hoy - timedelta(days=30)).order_by("-aviso_desde")
    return render(request, "tablero/avisos.html", {"institucion": institucion, "avisos": publicados, "hoy": hoy})
