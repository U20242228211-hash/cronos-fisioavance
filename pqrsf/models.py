import secrets
from datetime import date

from django.conf import settings
from django.db import models, transaction
from django.utils import timezone

from instituciones.models import Aseguradora, DeInstitucion, Institucion, Profesional, Servicio

from . import plazos


class Tipo(models.TextChoices):
    PETICION = "P", "Petición"
    QUEJA = "Q", "Queja"
    RECLAMO = "R", "Reclamo"
    SUGERENCIA = "S", "Sugerencia"
    FELICITACION = "F", "Felicitación"


class Clasificacion(models.TextChoices):
    VITAL_NNA = "vital_nna", "Riesgo vital · niño, niña o adolescente"
    VITAL = "vital", "Riesgo vital"
    PRIORIZADO = "priorizado", "Riesgo priorizado"
    SIMPLE = "simple", "Riesgo simple"
    GENERAL = "general", "General"
    INFORMACION = "informacion", "Solicitud de documentos o información"
    COPIAS = "copias", "Copias (por ejemplo, de la historia clínica)"
    CONSULTA = "consulta", "Consulta"


RIESGOS = [Clasificacion.VITAL_NNA, Clasificacion.VITAL, Clasificacion.PRIORIZADO, Clasificacion.SIMPLE]

# Una queja que tiene que ver con la atención se trata como reclamo, porque prevalece lo más favorable al
# usuario (Circular Única de la Supersalud, Título VII, numeral 3.3).
CLASIFICACIONES_POR_TIPO = {
    Tipo.RECLAMO: RIESGOS,
    Tipo.PETICION: [Clasificacion.GENERAL, Clasificacion.INFORMACION, Clasificacion.COPIAS, Clasificacion.CONSULTA],
    Tipo.QUEJA: [Clasificacion.GENERAL] + RIESGOS,
    Tipo.SUGERENCIA: [Clasificacion.GENERAL],
    Tipo.FELICITACION: [Clasificacion.GENERAL],
}


class ReglaPlazo(models.Model):
    """Término de respuesta para un tipo y una clasificación. Las reglas sin institución son las de la norma
    y sirven para todas; una institución puede tener las suyas si su política es más estricta."""

    institucion = models.ForeignKey(
        Institucion,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name="institución",
        help_text="Vacío: regla general de la norma, para todas las instituciones.",
    )
    tipo = models.CharField(max_length=1, choices=Tipo.choices)
    clasificacion = models.CharField("clasificación", max_length=12, choices=Clasificacion.choices)
    cantidad = models.PositiveIntegerField()
    unidad = models.CharField(
        max_length=12,
        choices=[(plazos.HORAS, "Horas corridas"), (plazos.DIAS_HABILES, "Días hábiles")],
    )
    norma = models.CharField("fuente", max_length=250, blank=True)

    class Meta:
        verbose_name = "término de respuesta"
        verbose_name_plural = "términos de respuesta"
        unique_together = [("institucion", "tipo", "clasificacion")]
        ordering = ["tipo", "clasificacion"]

    def __str__(self):
        unidad = "h" if self.unidad == plazos.HORAS else "días hábiles"
        return f"{self.get_tipo_display()} · {self.get_clasificacion_display()}: {self.cantidad} {unidad}"

    @classmethod
    def para(cls, institucion, tipo, clasificacion):
        reglas = cls.objects.filter(tipo=tipo, clasificacion=clasificacion)
        return reglas.filter(institucion=institucion).first() or reglas.filter(institucion=None).first()


class Consecutivo(models.Model):
    """Contador de radicados por institución y año (se bloquea al usarlo para no repetir números)."""

    institucion = models.ForeignKey(Institucion, on_delete=models.CASCADE)
    anio = models.PositiveSmallIntegerField()
    ultimo = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = [("institucion", "anio")]

    @classmethod
    def siguiente(cls, institucion, anio):
        with transaction.atomic():
            fila, _ = cls.objects.select_for_update().get_or_create(institucion=institucion, anio=anio)
            fila.ultimo += 1
            fila.save(update_fields=["ultimo"])
            return fila.ultimo


class Motivo(models.TextChoices):
    OPORTUNIDAD = "oportunidad", "Oportunidad: citas y agendamiento"
    ACCESO = "acceso", "Acceso: órdenes, autorizaciones o negación del servicio"
    ATENCION = "atencion", "Atención del profesional y calidad del tratamiento"
    TRATO = "trato", "Trato del personal"
    INFORMACION = "informacion", "Información, documentos y trámites"
    INFRAESTRUCTURA = "infraestructura", "Instalaciones, aseo y comodidad"
    COBROS = "cobros", "Cobros y facturación"
    RECONOCIMIENTO = "reconocimiento", "Reconocimiento al equipo"
    OTRO = "otro", "Otro"


class PQRSF(DeInstitucion):
    class Canal(models.TextChoices):
        WEB = "web", "Formulario web (código QR o enlace)"
        WHATSAPP = "whatsapp", "Enlace enviado por WhatsApp"
        TABLETA = "tableta", "Tableta de recepción"
        BUZON = "buzon", "Buzón físico"
        PRESENCIAL = "presencial", "Presencial o telefónico"
        CORREO = "correo", "Correo electrónico"

    class Estado(models.TextChoices):
        RADICADA = "radicada", "Radicada"
        EN_TRAMITE = "en_tramite", "En trámite"
        RESPONDIDA = "respondida", "Respondida"
        CERRADA = "cerrada", "Cerrada"

    class MedioRespuesta(models.TextChoices):
        WHATSAPP = "whatsapp", "WhatsApp"
        CORREO = "correo", "Correo electrónico"
        PERSONAL = "personal", "La recoge en la sede"
        AVISO = "aviso", "Aviso publicado (sin datos de contacto)"

    class TipoDocumento(models.TextChoices):
        CC = "CC", "Cédula de ciudadanía"
        TI = "TI", "Tarjeta de identidad"
        RC = "RC", "Registro civil"
        CE = "CE", "Cédula de extranjería"
        PA = "PA", "Pasaporte"
        PPT = "PPT", "Permiso por protección temporal"

    class Sexo(models.TextChoices):
        F = "F", "Femenino"
        M = "M", "Masculino"
        I = "I", "Intersexual"
        N = "N", "Prefiere no decir"

    class Regimen(models.TextChoices):
        NO_APLICA = "no_aplica", "No aplica (particular o póliza)"
        CONTRIBUTIVO = "contributivo", "Contributivo"
        SUBSIDIADO = "subsidiado", "Subsidiado"
        ESPECIAL = "especial", "Especial o de excepción"

    class Vinculacion(models.TextChoices):
        PARTICULAR = "particular", "Particular"
        ASEGURADORA = "aseguradora", "Aseguradora o póliza"

    class Condicion(models.TextChoices):
        NINGUNA = "ninguna", "Ninguna"
        ADULTO_MAYOR = "adulto_mayor", "Persona mayor"
        DISCAPACIDAD = "discapacidad", "Persona con discapacidad"
        GESTANTE = "gestante", "Mujer gestante"
        MENOR = "menor", "Niño, niña o adolescente"
        VICTIMA = "victima", "Víctima del conflicto armado"

    radicado = models.CharField(max_length=24, unique=True, editable=False)
    tipo = models.CharField(max_length=1, choices=Tipo.choices)
    canal = models.CharField(max_length=12, choices=Canal.choices, default=Canal.WEB)
    clasificacion = models.CharField(
        "clasificación", max_length=12, choices=Clasificacion.choices, blank=True
    )
    clasificacion_propuesta = models.CharField(
        "clasificación propuesta", max_length=12, choices=Clasificacion.choices, blank=True, editable=False
    )
    clasificacion_confirmada = models.BooleanField("clasificación confirmada", default=False)

    servicio = models.ForeignKey(Servicio, on_delete=models.SET_NULL, null=True, blank=True)
    profesional = models.ForeignKey(
        Profesional, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="profesional que lo atendió"
    )
    descripcion = models.TextField("descripción")
    adjunto = models.FileField(upload_to="adjuntos/%Y/%m/", blank=True)

    # Quién la presenta
    anonima = models.BooleanField("anónima", default=False)
    tipo_documento = models.CharField(
        "tipo de documento", max_length=3, choices=TipoDocumento.choices, blank=True
    )
    numero_documento = models.CharField("número de documento", max_length=20, blank=True)
    nombres = models.CharField(max_length=80, blank=True)
    apellidos = models.CharField(max_length=80, blank=True)
    sexo = models.CharField(max_length=1, choices=Sexo.choices, blank=True)
    fecha_nacimiento = models.DateField("fecha de nacimiento", null=True, blank=True)
    telefono = models.CharField("celular o WhatsApp", max_length=20, blank=True)
    correo = models.EmailField(blank=True)
    municipio = models.CharField(max_length=80, blank=True)
    departamento = models.CharField(max_length=80, blank=True)
    vinculacion = models.CharField(
        "vinculación", max_length=12, choices=Vinculacion.choices, blank=True
    )
    aseguradora = models.ForeignKey(Aseguradora, on_delete=models.SET_NULL, null=True, blank=True)
    condicion_especial = models.CharField(
        "condición especial", max_length=14, choices=Condicion.choices, default=Condicion.NINGUNA
    )
    es_acudiente = models.BooleanField("la presenta un acudiente", default=False)
    nombre_paciente = models.CharField("nombre del paciente", max_length=160, blank=True)
    paciente_tipo_documento = models.CharField(
        "tipo de documento del paciente", max_length=3, choices=TipoDocumento.choices, blank=True
    )
    paciente_numero_documento = models.CharField("documento del paciente", max_length=20, blank=True)
    medio_respuesta = models.CharField(
        "dónde quiere la respuesta", max_length=10, choices=MedioRespuesta.choices
    )
    autoriza_datos = models.BooleanField("autorizó el tratamiento de datos", default=False)
    autorizacion_en = models.DateTimeField("fecha de la autorización", null=True, blank=True)

    # Registro que pide la Circular Única (Título VII, numeral 3.3)
    motivo = models.CharField("tema principal", max_length=16, choices=Motivo.choices, blank=True)
    regimen = models.CharField("régimen", max_length=12, choices=Regimen.choices, default=Regimen.NO_APLICA)
    tutela = models.BooleanField("hay fallo de tutela relacionado", default=False)
    negacion_servicio = models.BooleanField("tiene que ver con una negación del servicio", default=False)
    detalle_negacion = models.TextField("motivo y responsable de la negación", blank=True)
    accion_realizada = models.TextField(
        "acción realizada", blank=True, help_text="Qué se hizo para solucionarla. No lo ve el paciente."
    )

    # Tiempos y gestión
    recibida_en = models.DateTimeField(
        "recibida", default=timezone.now, help_text="Para el buzón físico: la fecha en que se abrió."
    )
    vence_en = models.DateTimeField("vence", null=True, blank=True)
    estado = models.CharField(max_length=12, choices=Estado.choices, default=Estado.RADICADA)
    asignada_a = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="pqrsf_asignadas",
        verbose_name="responsable",
    )
    respuesta = models.TextField(blank=True)
    respondida_en = models.DateTimeField("respondida", null=True, blank=True)
    respondida_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    comunicada_en = models.DateTimeField("respuesta comunicada", null=True, blank=True)
    aviso_desde = models.DateField("aviso publicado desde", null=True, blank=True)
    aviso_hasta = models.DateField("aviso publicado hasta", null=True, blank=True)
    cerrada_en = models.DateTimeField("cerrada", null=True, blank=True)
    alerta_50 = models.BooleanField(default=False, editable=False)
    alerta_80 = models.BooleanField(default=False, editable=False)
    escalada = models.BooleanField(default=False, editable=False)

    token = models.CharField(max_length=40, unique=True, editable=False)
    codigo_consulta = models.CharField("código de consulta", max_length=8, editable=False)
    creada = models.DateTimeField(auto_now_add=True)
    actualizada = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "PQRSF"
        verbose_name_plural = "PQRSF"
        ordering = ["-recibida_en"]
        indexes = [
            models.Index(fields=["institucion", "estado"]),
            models.Index(fields=["institucion", "recibida_en"]),
        ]

    def __str__(self):
        return f"{self.radicado} · {self.get_tipo_display()}"

    def save(self, *args, **kwargs):
        if not self.token:
            self.token = secrets.token_urlsafe(24)
        if not self.codigo_consulta:
            self.codigo_consulta = secrets.token_hex(3).upper()
        if not self.radicado:
            anio = timezone.localtime(self.recibida_en).year
            numero = Consecutivo.siguiente(self.institucion, anio)
            self.radicado = f"{self.institucion.prefijo_radicado}-{anio}-{numero:05d}"
        super().save(*args, **kwargs)

    # --- Términos ------------------------------------------------------------------------------
    @property
    def regla(self):
        clasificacion = self.clasificacion or self.clasificacion_propuesta
        return ReglaPlazo.para(self.institucion, self.tipo, clasificacion)

    def recalcular_vencimiento(self):
        regla = self.regla
        self.vence_en = (
            plazos.calcular_vencimiento(self.recibida_en, regla.cantidad, regla.unidad, self.institucion.pais)
            if regla
            else None
        )

    @property
    def abierta(self):
        return self.estado in (self.Estado.RADICADA, self.Estado.EN_TRAMITE)

    def porcentaje(self, ahora=None):
        if not self.vence_en:
            return 0.0
        fin = self.respondida_en or ahora or timezone.now()
        return plazos.porcentaje_transcurrido(self.recibida_en, self.vence_en, fin)

    @property
    def semaforo(self):
        if not self.abierta:
            return "a_tiempo" if self.respondida_a_tiempo else "tarde"
        return plazos.semaforo(self.porcentaje())

    @property
    def respondida_a_tiempo(self):
        return bool(self.respondida_en and self.vence_en and self.respondida_en <= self.vence_en)

    @property
    def horas_restantes(self):
        if not self.vence_en:
            return None
        return (self.vence_en - timezone.now()).total_seconds() / 3600

    # --- Datos de quien la presenta -------------------------------------------------------------
    @property
    def nombre_completo(self):
        if self.anonima:
            return "Anónima"
        return f"{self.nombres} {self.apellidos}".strip()

    @property
    def es_nna(self):
        """Niño, niña o adolescente: tiene un término más corto si el riesgo es vital."""
        return self.condicion_especial == self.Condicion.MENOR or (self.edad is not None and self.edad < 18)

    @property
    def edad(self):
        if not self.fecha_nacimiento:
            return None
        hoy = date.today()
        n = self.fecha_nacimiento
        return hoy.year - n.year - ((hoy.month, hoy.day) < (n.month, n.day))


class Actuacion(models.Model):
    """Lo que le pasa a una PQRSF, en orden. Es un histórico inmutable: no se edita ni se borra."""

    class Tipo(models.TextChoices):
        RADICACION = "radicacion", "Radicación"
        CLASIFICACION = "clasificacion", "Clasificación"
        ASIGNACION = "asignacion", "Asignación"
        NOTA = "nota", "Nota interna"
        RESPUESTA = "respuesta", "Respuesta"
        COMUNICACION = "comunicacion", "Respuesta comunicada"
        AVISO = "aviso", "Aviso publicado"
        CIERRE = "cierre", "Cierre"
        REAPERTURA = "reapertura", "Reapertura"
        ALERTA = "alerta", "Alerta de vencimiento"
        ESCALAMIENTO = "escalamiento", "Escalamiento"

    pqrsf = models.ForeignKey(PQRSF, on_delete=models.PROTECT, related_name="actuaciones")
    tipo = models.CharField(max_length=14, choices=Tipo.choices)
    descripcion = models.TextField("descripción")
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="hecha por"
    )
    estado_anterior = models.CharField(max_length=12, blank=True)
    estado_nuevo = models.CharField(max_length=12, blank=True)
    visible_paciente = models.BooleanField("la ve el paciente", default=False)
    fecha = models.DateTimeField(default=timezone.now)

    class Meta:
        verbose_name = "actuación"
        verbose_name_plural = "histórico de actuaciones"
        ordering = ["fecha", "id"]

    def __str__(self):
        return f"{self.get_tipo_display()} · {timezone.localtime(self.fecha):%d/%m/%Y %H:%M}"

    def save(self, *args, **kwargs):
        if self.pk:
            raise ValueError("El histórico no se puede modificar.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValueError("El histórico no se puede borrar.")
