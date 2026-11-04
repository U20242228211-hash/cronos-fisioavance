"""Descargas en Excel: el detalle de las PQRSF, el de las encuestas y el informe de indicadores."""

import io

from django.http import Http404, HttpResponse
from django.utils import timezone
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from encuestas import indicadores
from encuestas.models import Pregunta, RespuestaEncuesta, RespuestaItem
from instituciones.models import Servicio
from pqrsf import plazos
from pqrsf.models import PQRSF

ENCABEZADO = PatternFill("solid", fgColor="0F766E")
LETRA_ENCABEZADO = Font(bold=True, color="FFFFFF")


def _hoja(libro, titulo, columnas, filas, primera=False):
    hoja = libro.active if primera else libro.create_sheet()
    hoja.title = titulo[:31]
    hoja.append(columnas)
    for celda in hoja[1]:
        celda.fill = ENCABEZADO
        celda.font = LETRA_ENCABEZADO
        celda.alignment = Alignment(vertical="center", wrap_text=True)
    for fila in filas:
        hoja.append(fila)
    for i, columna in enumerate(columnas, 1):
        largo = max([len(str(columna))] + [len(str(f[i - 1])) for f in filas if f[i - 1] is not None] or [10])
        hoja.column_dimensions[get_column_letter(i)].width = min(max(12, largo + 2), 60)
    hoja.freeze_panes = "A2"
    if filas:
        hoja.auto_filter.ref = hoja.dimensions
    return hoja


def _fecha(valor):
    return timezone.localtime(valor).replace(tzinfo=None) if valor else None


def _respuesta(libro, nombre):
    buffer = io.BytesIO()
    libro.save(buffer)
    respuesta = HttpResponse(
        buffer.getvalue(), content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    respuesta["Content-Disposition"] = f'attachment; filename="{nombre}"'
    return respuesta


def libro_pqrsf(institucion, desde, hasta):
    qs = PQRSF.objects.filter(institucion=institucion, recibida_en__gte=desde, recibida_en__lt=hasta).select_related(
        "servicio", "profesional", "aseguradora", "asignada_a"
    )
    # Los literales a) a s) del numeral 3.3 del Título VII de la Circular Única, más los datos del término
    columnas = [
        "Radicado", "Fecha y hora de recepción", "Canal", "Tipo", "Clasificación", "Clasificación confirmada",
        "Tema principal", "Servicio", "Profesional", "Entidad asociada", "Régimen", "Anónima",
        "Tipo de documento", "Número de documento", "Nombres", "Apellidos", "Celular", "Correo",
        "Paciente (si la presentó un acudiente)", "Documento del paciente", "Niño, niña o adolescente", "Sexo", "Edad",
        "Departamento", "Municipio", "Condición especial", "Fallo de tutela", "Negación del servicio",
        "Motivo y responsable de la negación", "Medio de respuesta", "Autorizó datos", "Descripción", "Estado",
        "Responsable", "Vence", "Fecha de solución", "Respondida a tiempo", "Días hábiles para responder",
        "Horas para responder", "Respuesta comunicada", "Acción realizada", "Cerrada",
    ]
    filas = []
    for p in qs:
        dias = plazos.dias_habiles_entre(p.recibida_en, p.respondida_en, institucion.pais) if p.respondida_en else None
        horas = round((p.respondida_en - p.recibida_en).total_seconds() / 3600, 1) if p.respondida_en else None
        filas.append([
            p.radicado, _fecha(p.recibida_en), p.get_canal_display(), p.get_tipo_display(),
            p.get_clasificacion_display(), "Sí" if p.clasificacion_confirmada else "No", p.get_motivo_display(),
            str(p.servicio or ""), str(p.profesional or ""), str(p.aseguradora or "Particular"),
            p.get_regimen_display(), "Sí" if p.anonima else "No", p.tipo_documento, p.numero_documento, p.nombres,
            p.apellidos, p.telefono, p.correo, p.nombre_paciente if p.es_acudiente else "",
            f"{p.paciente_tipo_documento} {p.paciente_numero_documento}".strip() if p.es_acudiente else "",
            "Sí" if p.es_nna else "No", p.get_sexo_display(), p.edad, p.departamento, p.municipio,
            p.get_condicion_especial_display(), "Sí" if p.tutela else "No", "Sí" if p.negacion_servicio else "No",
            p.detalle_negacion, p.get_medio_respuesta_display(), "Sí" if p.autoriza_datos else "No", p.descripcion,
            p.get_estado_display(), str(p.asignada_a or ""), _fecha(p.vence_en), _fecha(p.respondida_en),
            ("Sí" if p.respondida_a_tiempo else "No") if p.respondida_en else "",
            dias, horas, _fecha(p.comunicada_en), p.accion_realizada, _fecha(p.cerrada_en),
        ])
    libro = Workbook()
    hoja = _hoja(libro, "PQRSF", columnas, filas, primera=True)
    for fila in hoja.iter_rows(min_row=2):
        for celda in fila:
            if hasattr(celda.value, "year"):
                celda.number_format = "dd/mm/yyyy hh:mm"
    return libro


def libro_encuestas(institucion, desde, hasta):
    preguntas = list(Pregunta.objects.filter(institucion=institucion).order_by("orden", "id"))
    qs = (
        RespuestaEncuesta.objects.filter(institucion=institucion, respondida_en__gte=desde, respondida_en__lt=hasta)
        .select_related("servicio", "invitacion")
        .prefetch_related("items__pregunta")
    )
    columnas = ["Fecha", "Servicio", "Canal", "Paciente"] + [p.texto for p in preguntas] + ["Comentario", "Mala calificación", "Revisada"]
    filas = []
    for r in qs:
        valores = {i.pregunta_id: dict(i.pregunta.opciones).get(i.valor, "") for i in r.items.all()}
        filas.append(
            [_fecha(r.respondida_en), str(r.servicio or ""), r.get_canal_display(), r.invitacion.nombre_paciente if r.invitacion else "Anónima"]
            + [valores.get(p.id, "") for p in preguntas]
            + [r.comentario, "Sí" if r.requiere_atencion else "No", "Sí" if r.atendida else "No"]
        )
    libro = Workbook()
    _hoja(libro, "Encuestas", columnas, filas, primera=True)
    return libro


def libro_indicadores(institucion, primero):
    serie = indicadores.serie_mensual(institucion, meses=12, hoy=primero)
    filas = []
    for m in serie:
        desde = indicadores.a_fecha_hora(m["mes"])
        hasta = indicadores.a_fecha_hora(indicadores.sumar_meses(m["mes"], 1))
        qs = PQRSF.objects.filter(institucion=institucion, recibida_en__gte=desde, recibida_en__lt=hasta)
        respondidas = [p for p in qs if p.respondida_en]
        a_tiempo = sum(1 for p in respondidas if p.respondida_a_tiempo)
        filas.append([
            m["etiqueta"], m["encuestas"],
            m["satisfaccion_numerador"], m["satisfaccion_denominador"], m["satisfaccion"],
            m["recomendacion_numerador"], m["recomendacion_denominador"], m["recomendacion"],
            qs.count(), len(respondidas), a_tiempo, indicadores.porcentaje(a_tiempo, len(respondidas)),
        ])
    columnas = [
        "Mes", "Encuestas", "Satisfacción: muy buena o buena", "Satisfacción: respondieron", "Satisfacción global (%)",
        "Recomendación: definitivamente o probablemente sí", "Recomendación: respondieron", "Recomendaría la IPS (%)",
        "PQRSF recibidas", "PQRSF respondidas", "Respondidas a tiempo", "Oportunidad de respuesta (%)",
    ]
    libro = Workbook()
    _hoja(libro, "Indicadores por mes", columnas, filas, primera=True)
    desde = indicadores.a_fecha_hora(primero)
    hasta = indicadores.a_fecha_hora(indicadores.sumar_meses(primero, 1))
    por_servicio = []
    for s in Servicio.objects.filter(institucion=institucion):
        d = indicadores.calcular(institucion, desde, hasta, servicio=s)
        if d["encuestas"]:
            por_servicio.append([s.nombre, d["encuestas"], d["satisfaccion"], d["recomendacion"], d["malas"]])
    _hoja(
        libro,
        f"Por servicio {indicadores.etiqueta_mes(primero)}",
        ["Servicio", "Encuestas", "Satisfacción global (%)", "Recomendaría la IPS (%)", "Con mala calificación"],
        por_servicio,
    )
    nota = libro.create_sheet("Cómo se calcula")
    for linea in [
        "Satisfacción global = respuestas «muy buena» o «buena» ÷ respuestas a la pregunta de experiencia global × 100.",
        "Recomendación = respuestas «definitivamente sí» o «probablemente sí» ÷ respuestas a la pregunta de recomendación × 100.",
        "Fuente: Resolución 256 de 2016 del Ministerio de Salud y Protección Social.",
        "Oportunidad = PQRSF respondidas dentro del término ÷ PQRSF respondidas × 100.",
    ]:
        nota.append([linea])
    nota.column_dimensions["A"].width = 120
    return libro


def trimestre_de(dia):
    numero = (dia.month - 1) // 3 + 1
    inicio = dia.replace(month=3 * (numero - 1) + 1, day=1)
    return numero, inicio, indicadores.sumar_meses(inicio, 3)


def libro_res256(institucion, primero):
    """Conteos por opción de respuesta del trimestre, que es lo que la IPS reporta en PISIS (Resolución 256 de
    2016, Anexo Técnico 2, registro tipo 3; reporte trimestral por el parágrafo del art. 6)."""
    numero, inicio, fin = trimestre_de(primero)
    desde, hasta = indicadores.a_fecha_hora(inicio), indicadores.a_fecha_hora(fin)
    encuestas = RespuestaEncuesta.objects.filter(institucion=institucion, respondida_en__gte=desde, respondida_en__lt=hasta)
    filas = []
    for indicador, codigo in ((Pregunta.Indicador.SATISFACCION, "P.3.14"), (Pregunta.Indicador.RECOMENDACION, "P.3.15")):
        pregunta = Pregunta.objects.filter(institucion=institucion, indicador=indicador).first()
        if not pregunta:
            continue
        items = RespuestaItem.objects.filter(pregunta=pregunta, respuesta__in=encuestas)
        conteo = {v: items.filter(valor=v).count() for v, _ in pregunta.opciones}
        no_informa = encuestas.count() - items.exclude(valor=None).count()
        positivas = sum(n for v, n in conteo.items() if pregunta.es_positiva(v))
        respondieron = sum(conteo.values())
        for valor, texto in reversed(pregunta.opciones):
            filas.append([codigo, pregunta.texto, texto, conteo[valor]])
        filas.append([codigo, pregunta.texto, "No informa", no_informa])
        filas.append([codigo, "Indicador (calculado)", f"{positivas} de {respondieron}", indicadores.porcentaje(positivas, respondieron)])
    libro = Workbook()
    _hoja(libro, f"Trimestre {numero} de {inicio.year}", ["Indicador", "Pregunta", "Respuesta", "Usuarios"], filas, primera=True)
    vence = indicadores.sumar_meses(inicio, 3)
    nota = libro.create_sheet("Cómo se reporta")
    for linea in [
        f"{institucion.nombre} · trimestre {numero} de {inicio.year} ({inicio:%d/%m/%Y} a {indicadores.sumar_meses(inicio, 3):%d/%m/%Y}, sin incluir el último día).",
        "Se reporta en la plataforma PISIS de SISPRO, en archivo plano, dentro de los 30 días calendario siguientes al cierre del trimestre.",
        f"Para este trimestre: a más tardar 30 días después del {vence:%d/%m/%Y}.",
        "Se reportan los usuarios que eligieron cada opción; el Ministerio calcula el indicador. 'No informa' son las encuestas que no respondieron la pregunta.",
        "Fuente: Resolución 256 de 2016, art. 6 parágrafo (reporte trimestral, vigente por la Resolución 1632 de 2025, art. 19) y fichas técnicas P.3.14 y P.3.15.",
    ]:
        nota.append([linea])
    nota.column_dimensions["A"].width = 140
    return libro


def descargar(tipo, institucion, desde, hasta, primero):
    sufijo = f"{institucion.slug}-{primero:%Y-%m}"
    if tipo == "pqrsf":
        return _respuesta(libro_pqrsf(institucion, desde, hasta), f"pqrsf-{sufijo}.xlsx")
    if tipo == "encuestas":
        return _respuesta(libro_encuestas(institucion, desde, hasta), f"encuestas-{sufijo}.xlsx")
    if tipo == "indicadores":
        return _respuesta(libro_indicadores(institucion, primero), f"indicadores-{sufijo}.xlsx")
    if tipo == "res256":
        numero, inicio, _ = trimestre_de(primero)
        return _respuesta(libro_res256(institucion, primero), f"res256-{institucion.slug}-{inicio.year}-T{numero}.xlsx")
    raise Http404
