"""Las acciones sobre una PQRSF. Cada una cambia el caso y deja su rastro en el histórico.

Las vistas y el panel llaman estas funciones en vez de tocar los campos a mano, así el histórico y las
alertas quedan siempre completos.
"""

from django.db import transaction
from django.utils import timezone

from . import notificaciones, plazos
from .models import PQRSF, Actuacion, Clasificacion, Tipo

PALABRAS_VITAL = (
    "no puede respirar", "no respira", "desmay", "sangr", "convuls", "dolor en el pecho", "infarto",
    "inconsciente", "riesgo de muerte", "suicid", "se cayó", "se cayo", "caída", "caida", "fractura",
)
PALABRAS_PRIORIZADO = (
    "mucho dolor", "dolor fuerte", "dolor intenso", "no puede caminar", "no puedo caminar", "empeor",
    "inflama", "embaraz", "cirugía", "cirugia", "postoperatori", "lesión", "lesion", "silla de ruedas",
    "suspendieron", "me negaron", "no me atendieron", "urgente",
)
PALABRAS_COPIAS = ("copia", "historia clínica", "historia clinica", "epicrisis")
PALABRAS_INFORMACION = ("certificado", "constancia", "factura", "documento", "incapacidad", "resultado")
# Cohortes que la CE 2026151000000007-5 trata siempre como riesgo vital cuando el paciente es menor de edad
COHORTES_NNA = (
    "trasplant", "cardiovascular", "corazón", "corazon", "cáncer", "cancer", "leucemia", "huérfana", "huerfana",
    "respiratoria crónica", "respiratoria cronica", "asma", "vih",
)
PALABRAS_CONSULTA = ("quisiera saber", "qué debo", "que debo", "cómo puedo", "como puedo", "consulta", "pregunta")
CONDICIONES_PRIORITARIAS = {
    PQRSF.Condicion.ADULTO_MAYOR, PQRSF.Condicion.DISCAPACIDAD, PQRSF.Condicion.GESTANTE, PQRSF.Condicion.MENOR,
}

CAMPOS_PERSONALES = (
    "tipo_documento", "numero_documento", "nombres", "apellidos", "sexo", "telefono", "correo", "municipio",
    "departamento", "nombre_paciente", "paciente_tipo_documento", "paciente_numero_documento",
)


MOTIVOS = [
    ("reconocimiento", ("felicit", "gracias", "excelente", "agradec")),
    ("trato", ("mala manera", "grosero", "grosera", "trato", "me gritó", "me grito", "irrespet")),
    ("acceso", ("orden", "autoriz", "suspend", "negaron", "no me dejaron", "no la dejaron", "no lo dejaron")),
    ("oportunidad", ("cita", "agenda", "sesiones", "esperando", "esperar", "tarde", "demora")),
    ("cobros", ("cobro", "factura", "pago", "precio", "valor")),
    ("informacion", ("certificado", "copia", "historia clínica", "historia clinica", "documento", "información", "informacion")),
    ("infraestructura", ("baño", "bano", "silla", "rampa", "sede", "aseo", "calor", "parqueadero", "ascensor")),
    ("atencion", ("tratamiento", "dolor", "terapia", "explic", "atendió", "atendio")),
]


def proponer_motivo(descripcion):
    texto = (descripcion or "").lower()
    for motivo, palabras in MOTIVOS:
        if any(p in texto for p in palabras):
            return motivo
    return "otro"


def proponer_clasificacion(tipo, descripcion, condicion=PQRSF.Condicion.NINGUNA, es_nna=False):
    """Propone la clasificación con reglas simples. Siempre la confirma un funcionario: no reemplaza su criterio."""
    texto = (descripcion or "").lower()
    es_nna = es_nna or condicion == PQRSF.Condicion.MENOR
    vital = any(p in texto for p in PALABRAS_VITAL)
    priorizado = any(p in texto for p in PALABRAS_PRIORIZADO) or condicion in CONDICIONES_PRIORITARIAS
    if tipo in (Tipo.RECLAMO, Tipo.QUEJA):
        if es_nna and (vital or any(p in texto for p in COHORTES_NNA)):
            return Clasificacion.VITAL_NNA
        if vital:
            return Clasificacion.VITAL
        if priorizado:
            return Clasificacion.PRIORIZADO
        return Clasificacion.SIMPLE if tipo == Tipo.RECLAMO else Clasificacion.GENERAL
    if tipo == Tipo.PETICION:
        if any(p in texto for p in PALABRAS_COPIAS):
            return Clasificacion.COPIAS
        if any(p in texto for p in PALABRAS_INFORMACION):
            return Clasificacion.INFORMACION
        if any(p in texto for p in PALABRAS_CONSULTA):
            return Clasificacion.CONSULTA
    return Clasificacion.GENERAL


def _registrar(pqrsf, tipo, descripcion, usuario=None, anterior="", visible=False):
    return Actuacion.objects.create(
        pqrsf=pqrsf,
        tipo=tipo,
        descripcion=descripcion,
        usuario=usuario,
        estado_anterior=anterior,
        estado_nuevo=pqrsf.estado,
        visible_paciente=visible,
    )


def _fecha(valor):
    return timezone.localtime(valor).strftime("%d/%m/%Y %I:%M %p") if valor else "sin término"


@transaction.atomic
def radicar(pqrsf, usuario=None):
    """Guarda una PQRSF nueva: le da radicado, propone la clasificación y calcula el vencimiento."""
    if pqrsf.anonima:
        for campo in CAMPOS_PERSONALES:
            setattr(pqrsf, campo, "")
        pqrsf.fecha_nacimiento = None
        pqrsf.medio_respuesta = PQRSF.MedioRespuesta.AVISO
    pqrsf.clasificacion_propuesta = proponer_clasificacion(
        pqrsf.tipo, pqrsf.descripcion, pqrsf.condicion_especial, pqrsf.es_nna
    )
    if not pqrsf.clasificacion:
        pqrsf.clasificacion = pqrsf.clasificacion_propuesta
    if not pqrsf.motivo:
        pqrsf.motivo = proponer_motivo(pqrsf.descripcion)
    if pqrsf.municipio and not pqrsf.departamento:
        pqrsf.departamento = pqrsf.institucion.departamento
    if pqrsf.autoriza_datos and not pqrsf.autorizacion_en:
        pqrsf.autorizacion_en = timezone.now()
    pqrsf.estado = PQRSF.Estado.RADICADA
    pqrsf.recalcular_vencimiento()
    pqrsf.save()
    _registrar(
        pqrsf,
        Actuacion.Tipo.RADICACION,
        f"Se recibió por {pqrsf.get_canal_display().lower()}. "
        f"Clasificación propuesta: {pqrsf.get_clasificacion_propuesta_display()}. "
        f"Vence: {_fecha(pqrsf.vence_en)}.",
        usuario,
        visible=True,
    )
    transaction.on_commit(lambda: notificaciones.nueva_pqrsf(pqrsf))
    return pqrsf


@transaction.atomic
def clasificar(pqrsf, clasificacion, usuario):
    anterior = pqrsf.estado
    pqrsf.clasificacion = clasificacion
    pqrsf.clasificacion_confirmada = True
    pqrsf.recalcular_vencimiento()
    pqrsf.alerta_50 = pqrsf.alerta_80 = pqrsf.escalada = False
    if pqrsf.estado == PQRSF.Estado.RADICADA:
        pqrsf.estado = PQRSF.Estado.EN_TRAMITE
    pqrsf.save()
    _registrar(
        pqrsf,
        Actuacion.Tipo.CLASIFICACION,
        f"Clasificación confirmada: {pqrsf.get_clasificacion_display()}. Vence: {_fecha(pqrsf.vence_en)}.",
        usuario,
        anterior,
    )


@transaction.atomic
def asignar(pqrsf, responsable, usuario):
    anterior = pqrsf.estado
    pqrsf.asignada_a = responsable
    if pqrsf.estado == PQRSF.Estado.RADICADA:
        pqrsf.estado = PQRSF.Estado.EN_TRAMITE
    pqrsf.save()
    nombre = responsable or "nadie"
    _registrar(pqrsf, Actuacion.Tipo.ASIGNACION, f"Responsable: {nombre}.", usuario, anterior, visible=True)


def nota(pqrsf, texto, usuario):
    _registrar(pqrsf, Actuacion.Tipo.NOTA, texto, usuario, pqrsf.estado)


@transaction.atomic
def responder(pqrsf, texto, usuario):
    anterior = pqrsf.estado
    ahora = timezone.now()
    pqrsf.respuesta = texto
    pqrsf.respondida_en = ahora
    pqrsf.respondida_por = usuario
    pqrsf.estado = PQRSF.Estado.RESPONDIDA
    if pqrsf.anonima:
        # Sin datos del peticionario la respuesta se comunica por aviso (Ley 1437 de 2011, art. 69).
        desde = timezone.localdate(ahora)
        pqrsf.aviso_desde = desde
        pqrsf.aviso_hasta = timezone.localdate(plazos.sumar_dias_habiles(ahora, 5, pqrsf.institucion.pais))
    pqrsf.save()
    a_tiempo = "dentro del término" if pqrsf.respondida_a_tiempo else "fuera del término"
    _registrar(pqrsf, Actuacion.Tipo.RESPUESTA, f"Se dio respuesta {a_tiempo}.", usuario, anterior, visible=True)
    if pqrsf.anonima:
        _registrar(
            pqrsf,
            Actuacion.Tipo.AVISO,
            f"Respuesta publicada en la cartelera y en el portal hasta el {pqrsf.aviso_hasta:%d/%m/%Y}.",
            usuario,
            visible=True,
        )


@transaction.atomic
def comunicar(pqrsf, medio, usuario):
    pqrsf.comunicada_en = timezone.now()
    pqrsf.save(update_fields=["comunicada_en", "actualizada"])
    _registrar(pqrsf, Actuacion.Tipo.COMUNICACION, f"Respuesta enviada por {medio}.", usuario, visible=True)


@transaction.atomic
def cerrar(pqrsf, usuario):
    anterior = pqrsf.estado
    pqrsf.estado = PQRSF.Estado.CERRADA
    pqrsf.cerrada_en = timezone.now()
    pqrsf.save()
    _registrar(pqrsf, Actuacion.Tipo.CIERRE, "Caso cerrado.", usuario, anterior, visible=True)


@transaction.atomic
def reabrir(pqrsf, motivo, usuario):
    anterior = pqrsf.estado
    pqrsf.estado = PQRSF.Estado.EN_TRAMITE
    pqrsf.cerrada_en = None
    pqrsf.save()
    _registrar(pqrsf, Actuacion.Tipo.REAPERTURA, f"Se reabrió: {motivo}", usuario, anterior, visible=True)


def revisar_vencimientos(ahora=None):
    """Genera las alertas del 50 % y del 80 % del plazo y escala a la dirección lo que se venció.

    Se corre cada hora con una tarea programada (cron) o con ``python manage.py revisar_vencimientos``.
    """
    ahora = ahora or timezone.now()
    resumen = {"alerta_50": 0, "alerta_80": 0, "escaladas": 0}
    abiertas = PQRSF.objects.filter(
        estado__in=[PQRSF.Estado.RADICADA, PQRSF.Estado.EN_TRAMITE], vence_en__isnull=False
    ).select_related("institucion", "asignada_a")
    for pqrsf in abiertas:
        porcentaje = pqrsf.porcentaje(ahora)
        if porcentaje >= 100 and not pqrsf.escalada:
            pqrsf.escalada = pqrsf.alerta_80 = pqrsf.alerta_50 = True
            pqrsf.save(update_fields=["escalada", "alerta_80", "alerta_50"])
            _registrar(pqrsf, Actuacion.Tipo.ESCALAMIENTO, "Se venció el término. Se avisó a la dirección.")
            notificaciones.escalamiento(pqrsf)
            resumen["escaladas"] += 1
        elif porcentaje >= plazos.UMBRAL_ROJO and not pqrsf.alerta_80:
            pqrsf.alerta_80 = pqrsf.alerta_50 = True
            pqrsf.save(update_fields=["alerta_80", "alerta_50"])
            _registrar(pqrsf, Actuacion.Tipo.ALERTA, f"Va en el 80 % del término. Vence: {_fecha(pqrsf.vence_en)}.")
            notificaciones.alerta(pqrsf, 80)
            resumen["alerta_80"] += 1
        elif porcentaje >= plazos.UMBRAL_AMARILLO and not pqrsf.alerta_50:
            pqrsf.alerta_50 = True
            pqrsf.save(update_fields=["alerta_50"])
            _registrar(pqrsf, Actuacion.Tipo.ALERTA, f"Va en el 50 % del término. Vence: {_fecha(pqrsf.vence_en)}.")
            notificaciones.alerta(pqrsf, 50)
            resumen["alerta_50"] += 1
    return resumen
