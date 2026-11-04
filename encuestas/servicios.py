from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction

from .models import Pregunta, RespuestaEncuesta, RespuestaItem


PREGUNTAS_POR_DEFECTO = [
    ("¿Cómo calificaría su experiencia global respecto a los servicios de salud que recibió en esta IPS?", Pregunta.Escala.CARITAS, Pregunta.Indicador.SATISFACCION),
    ("¿Cómo le pareció la atención del profesional que lo trató?", Pregunta.Escala.CARITAS, ""),
    ("¿Cómo le pareció la puntualidad en el inicio de sus sesiones?", Pregunta.Escala.CARITAS, ""),
    ("¿Cómo le parecieron la limpieza y la comodidad de las instalaciones?", Pregunta.Escala.CARITAS, ""),
    ("¿Recomendaría a sus familiares y amigos esta IPS?", Pregunta.Escala.RECOMENDACION, Pregunta.Indicador.RECOMENDACION),
]


def crear_preguntas_por_defecto(institucion):
    if Pregunta.objects.filter(institucion=institucion).exists():
        return
    for orden, (texto, escala, indicador) in enumerate(PREGUNTAS_POR_DEFECTO, 1):
        Pregunta.objects.create(institucion=institucion, orden=orden, texto=texto, escala=escala, indicador=indicador)


def preguntas_activas(institucion):
    return Pregunta.objects.filter(institucion=institucion, activa=True).order_by("orden", "id")


@transaction.atomic
def registrar_respuesta(institucion, valores, comentario="", servicio=None, canal=None, invitacion=None):
    """Guarda una encuesta. ``valores`` es {id de la pregunta: valor elegido}."""
    respuesta = RespuestaEncuesta.objects.create(
        institucion=institucion,
        invitacion=invitacion,
        servicio=servicio or (invitacion.servicio if invitacion else None),
        canal=canal or (RespuestaEncuesta.Canal.INVITACION if invitacion else RespuestaEncuesta.Canal.QR),
        comentario=comentario.strip(),
    )
    mala = False
    for pregunta in preguntas_activas(institucion):
        valor = valores.get(pregunta.id)
        RespuestaItem.objects.create(respuesta=respuesta, pregunta=pregunta, valor=valor)
        mala = mala or pregunta.es_mala(valor)
    if mala:
        respuesta.requiere_atencion = True
        respuesta.save(update_fields=["requiere_atencion"])
        transaction.on_commit(lambda: _avisar_mala(respuesta))
    return respuesta


def _avisar_mala(respuesta):
    from usuarios.models import Usuario

    correos = list(
        Usuario.objects.filter(institucion=respuesta.institucion, rol=Usuario.Rol.GESTOR, is_active=True)
        .exclude(email="")
        .values_list("email", flat=True)
    )
    if correos:
        send_mail(
            "[Cronos] Una encuesta llegó con mala calificación",
            f"Servicio: {respuesta.servicio or 'sin servicio'}.\nComentario: {respuesta.comentario or '—'}",
            settings.DEFAULT_FROM_EMAIL,
            correos,
            fail_silently=True,
        )


def mensaje_invitacion(invitacion, url):
    nombre = invitacion.nombre_paciente.split()[0] if invitacion.nombre_paciente else ""
    return (
        f"Hola {nombre}, gracias por terminar su servicio de {invitacion.servicio} en "
        f"{invitacion.institucion.nombre}. ¿Nos ayuda con una encuesta de un minuto? "
        f"Son 5 preguntas con caritas: {url}"
    )
