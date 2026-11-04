"""Avisos por correo al equipo y enlaces de WhatsApp para responderle al paciente.

WhatsApp se usa con enlaces ``wa.me`` que abren el chat con el mensaje ya escrito: no cuesta nada y no
necesita la API de WhatsApp Business. Si algún día se contrata la API, solo cambia este archivo.
"""

import re
from urllib.parse import quote

from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone


def _correos(institucion, roles):
    from usuarios.models import Usuario

    return list(
        Usuario.objects.filter(institucion=institucion, rol__in=roles, is_active=True)
        .exclude(email="")
        .values_list("email", flat=True)
    )


def _enviar(asunto, cuerpo, destinatarios):
    if destinatarios:
        send_mail(asunto, cuerpo, settings.DEFAULT_FROM_EMAIL, destinatarios, fail_silently=True)


def _fecha(valor):
    return timezone.localtime(valor).strftime("%d/%m/%Y %I:%M %p") if valor else "sin término"


def nueva_pqrsf(pqrsf):
    from usuarios.models import Usuario

    roles = [Usuario.Rol.GESTOR]
    if pqrsf.clasificacion == "vital":
        roles.append(Usuario.Rol.DIRECCION)
    _enviar(
        f"[Cronos] Nueva {pqrsf.get_tipo_display().lower()} {pqrsf.radicado} · vence {_fecha(pqrsf.vence_en)}",
        f"Llegó la {pqrsf.get_tipo_display().lower()} {pqrsf.radicado} por {pqrsf.get_canal_display().lower()}.\n"
        f"Clasificación propuesta: {pqrsf.get_clasificacion_propuesta_display()}.\n"
        f"Vence: {_fecha(pqrsf.vence_en)}.\n\n{pqrsf.descripcion}",
        _correos(pqrsf.institucion, roles),
    )


def alerta(pqrsf, porcentaje):
    from usuarios.models import Usuario

    destinatarios = [pqrsf.asignada_a.email] if pqrsf.asignada_a and pqrsf.asignada_a.email else []
    destinatarios = destinatarios or _correos(pqrsf.institucion, [Usuario.Rol.GESTOR])
    _enviar(
        f"[Cronos] {pqrsf.radicado} va en el {porcentaje} % del término",
        f"La {pqrsf.get_tipo_display().lower()} {pqrsf.radicado} vence el {_fecha(pqrsf.vence_en)}.",
        destinatarios,
    )


def escalamiento(pqrsf):
    from usuarios.models import Usuario

    _enviar(
        f"[Cronos] Se venció {pqrsf.radicado}",
        f"La {pqrsf.get_tipo_display().lower()} {pqrsf.radicado} venció el {_fecha(pqrsf.vence_en)} sin respuesta.",
        _correos(pqrsf.institucion, [Usuario.Rol.DIRECCION, Usuario.Rol.GESTOR]),
    )


def numero_whatsapp(numero):
    """Deja solo los dígitos y agrega el indicativo de Colombia a los celulares de 10 dígitos."""
    digitos = re.sub(r"\D", "", numero or "")
    if len(digitos) == 10 and digitos.startswith("3"):
        digitos = "57" + digitos
    return digitos


def enlace_whatsapp(numero, mensaje):
    numero = numero_whatsapp(numero)
    return f"https://wa.me/{numero}?text={quote(mensaje)}" if numero else ""


def mensaje_respuesta(pqrsf, url_consulta):
    """Por WhatsApp va el aviso y el enlace, no el texto: así los datos de salud no quedan en el chat
    (Ley 1581 de 2012, art. 4, principio de seguridad). La respuesta completa, fechada y con la advertencia,
    está en el enlace."""
    return (
        f"Hola {pqrsf.nombres}, le escribimos de {pqrsf.institucion.nombre}. Ya está la respuesta a su "
        f"{pqrsf.get_tipo_display().lower()} radicada con el número {pqrsf.radicado}. "
        f"Puede leerla aquí: {url_consulta}"
    )


def enviar_respuesta_por_correo(pqrsf, url_consulta):
    if not pqrsf.correo:
        return False
    institucion = pqrsf.institucion
    lugar = f"{institucion.municipio}, " if institucion.municipio else ""
    fecha = timezone.localtime(pqrsf.respondida_en or timezone.now()).strftime("%d/%m/%Y")
    cuerpo = (
        f"{lugar}{fecha}\n\nHola {pqrsf.nombres}:\n\nEsta es la respuesta a su {pqrsf.get_tipo_display().lower()} "
        f"radicada con el número {pqrsf.radicado}.\n\n{pqrsf.respuesta}\n\n"
        f"IMPORTANTE: {institucion.advertencia_respuesta}\n\n"
        f"Puede consultar su caso aquí: {url_consulta}\n\n{institucion.nombre} · Atención al usuario"
    )
    enviados = send_mail(
        f"Respuesta a su {pqrsf.get_tipo_display().lower()} {pqrsf.radicado} · {pqrsf.institucion.nombre}",
        cuerpo,
        settings.DEFAULT_FROM_EMAIL,
        [pqrsf.correo],
        fail_silently=True,
    )
    return enviados > 0
