"""Encuestas de satisfacción: una por paciente, cuando termina el servicio.

Dos de las preguntas alimentan los indicadores de la Resolución 256 de 2016: la satisfacción global y si
recomendaría la IPS. Las demás las define cada institución.
"""

import secrets
from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone

from instituciones.models import DeInstitucion, Profesional, Servicio

OPCIONES_CARITAS = [
    (5, "Muy buena"),
    (4, "Buena"),
    (3, "Regular"),
    (2, "Mala"),
    (1, "Muy mala"),
]
OPCIONES_RECOMENDACION = [
    (4, "Definitivamente sí"),
    (3, "Probablemente sí"),
    (2, "Probablemente no"),
    (1, "Definitivamente no"),
]


class Pregunta(DeInstitucion):
    class Escala(models.TextChoices):
        CARITAS = "caritas", "Caritas (de muy mala a muy buena)"
        RECOMENDACION = "recomendacion", "¿Recomendaría? (cuatro opciones)"

    class Indicador(models.TextChoices):
        NINGUNO = "", "—"
        SATISFACCION = "satisfaccion", "Satisfacción global (Resolución 256 de 2016)"
        RECOMENDACION = "recomendacion", "Recomendaría la IPS (Resolución 256 de 2016)"

    orden = models.PositiveSmallIntegerField(default=0)
    texto = models.CharField(max_length=200)
    escala = models.CharField(max_length=14, choices=Escala.choices, default=Escala.CARITAS)
    indicador = models.CharField(max_length=14, choices=Indicador.choices, blank=True)
    activa = models.BooleanField(default=True)

    class Meta:
        ordering = ["orden", "id"]

    def __str__(self):
        return self.texto

    @property
    def opciones(self):
        return OPCIONES_RECOMENDACION if self.escala == self.Escala.RECOMENDACION else OPCIONES_CARITAS

    def es_positiva(self, valor):
        """Lo que cuenta en el numerador del indicador: «buena» o «muy buena»; «definitivamente» o «probablemente sí»."""
        if valor is None:
            return False
        return valor >= 3 if self.escala == self.Escala.RECOMENDACION else valor >= 4

    def es_mala(self, valor):
        if valor is None:
            return False
        return valor <= 2 if self.escala == self.Escala.RECOMENDACION else valor <= 2


def _token():
    return secrets.token_urlsafe(16)


def _expira():
    return timezone.now() + timedelta(days=30)


class InvitacionEncuesta(DeInstitucion):
    """La invitación que recibe un paciente al terminar su tratamiento."""

    nombre_paciente = models.CharField("nombre del paciente", max_length=160)
    telefono = models.CharField("celular o WhatsApp", max_length=20, blank=True)
    correo = models.EmailField(blank=True)
    servicio = models.ForeignKey(Servicio, on_delete=models.PROTECT)
    profesional = models.ForeignKey(Profesional, on_delete=models.SET_NULL, null=True, blank=True)
    fin_tratamiento = models.DateField("terminó el servicio", default=timezone.localdate)
    token = models.CharField(max_length=40, unique=True, default=_token, editable=False)
    expira_en = models.DateTimeField("vence la invitación", default=_expira)
    creada_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, editable=False
    )
    creada = models.DateTimeField(auto_now_add=True)
    enviada_en = models.DateTimeField("enviada", null=True, blank=True)

    class Meta:
        verbose_name = "invitación a la encuesta"
        verbose_name_plural = "invitaciones a la encuesta"
        ordering = ["-creada"]

    def __str__(self):
        return f"{self.nombre_paciente} · {self.servicio}"

    @property
    def respondida(self):
        return hasattr(self, "respuesta")

    @property
    def vigente(self):
        return not self.respondida and timezone.now() <= self.expira_en


class RespuestaEncuesta(DeInstitucion):
    class Canal(models.TextChoices):
        INVITACION = "invitacion", "Invitación por WhatsApp o correo"
        QR = "qr", "Código QR en la sede"
        TABLETA = "tableta", "Tableta de recepción"

    invitacion = models.OneToOneField(
        InvitacionEncuesta, on_delete=models.SET_NULL, null=True, blank=True, related_name="respuesta"
    )
    servicio = models.ForeignKey(Servicio, on_delete=models.SET_NULL, null=True, blank=True)
    canal = models.CharField(max_length=12, choices=Canal.choices, default=Canal.QR)
    respondida_en = models.DateTimeField("respondida", default=timezone.now)
    comentario = models.TextField(blank=True)
    requiere_atencion = models.BooleanField(
        "mala calificación", default=False, help_text="Tuvo una calificación mala o muy mala."
    )
    atendida = models.BooleanField("ya se revisó", default=False)
    pqrsf = models.ForeignKey(
        "pqrsf.PQRSF", on_delete=models.SET_NULL, null=True, blank=True, verbose_name="queja que generó"
    )

    class Meta:
        verbose_name = "respuesta a la encuesta"
        verbose_name_plural = "respuestas a la encuesta"
        ordering = ["-respondida_en"]

    def __str__(self):
        return f"Encuesta del {timezone.localtime(self.respondida_en):%d/%m/%Y}"

    def valor_indicador(self, indicador):
        item = next((i for i in self.items.all() if i.pregunta.indicador == indicador), None)
        return item.valor if item else None


class RespuestaItem(models.Model):
    respuesta = models.ForeignKey(RespuestaEncuesta, on_delete=models.CASCADE, related_name="items")
    pregunta = models.ForeignKey(Pregunta, on_delete=models.PROTECT)
    valor = models.PositiveSmallIntegerField(null=True, blank=True)

    class Meta:
        verbose_name = "respuesta"
        unique_together = [("respuesta", "pregunta")]

    def __str__(self):
        etiqueta = dict(self.pregunta.opciones).get(self.valor, "Sin respuesta")
        return f"{self.pregunta.texto}: {etiqueta}"
