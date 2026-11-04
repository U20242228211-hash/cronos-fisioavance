"""Instituciones (IPS) que usan Cronos y sus catálogos.

Cronos es multiinstitución: cada IPS tiene sus propios usuarios, servicios, PQRSF y encuestas, y nunca ve
los datos de otra. Todo lo que pertenece a una institución hereda de ``DeInstitucion``.
"""

from django.db import models
from django.utils.text import slugify


class Institucion(models.Model):
    nombre = models.CharField(max_length=150)
    slug = models.SlugField(
        "identificador", unique=True, help_text="Va en las direcciones públicas: /fisioavance/"
    )
    prefijo_radicado = models.CharField(
        "prefijo del radicado", max_length=6, help_text="Ejemplo: FIS → FIS-2026-00001"
    )
    nit = models.CharField("NIT", max_length=20, blank=True)
    codigo_habilitacion = models.CharField(
        "código de habilitación (REPS)", max_length=20, blank=True
    )
    direccion = models.CharField("dirección", max_length=200, blank=True)
    municipio = models.CharField(max_length=80, blank=True)
    departamento = models.CharField(max_length=80, blank=True)
    pais = models.CharField(
        "país", max_length=2, default="CO", help_text="Código ISO del país, para los festivos"
    )
    telefono = models.CharField("teléfono", max_length=30, blank=True)
    whatsapp = models.CharField(
        max_length=20, blank=True, help_text="Solo números y con indicativo: 573177165551"
    )
    correo = models.EmailField("correo de atención al usuario", blank=True)
    sitio_web = models.URLField("sitio web", blank=True)
    dominio = models.CharField(
        "dominio propio",
        max_length=150,
        blank=True,
        null=True,
        unique=True,
        help_text="Opcional. Si se usa, por ejemplo pqrsf.fisioavanceips.com, abre directo esta institución.",
    )
    logo = models.ImageField(upload_to="logos/", blank=True)
    logo_url = models.URLField(
        "logo (enlace)", blank=True, help_text="Se usa si no se ha subido un archivo de logo."
    )
    color_primario = models.CharField("color principal", max_length=7, default="#0F766E")
    horario_atencion = models.CharField("horario de atención", max_length=200, blank=True)
    aviso_privacidad = models.TextField(
        "aviso de privacidad",
        blank=True,
        help_text="Texto que el paciente acepta antes de enviar sus datos (Ley 1581 de 2012).",
    )
    advertencia_respuesta = models.TextField(
        "advertencia al final de cada respuesta",
        default=(
            "Si no está de acuerdo con esta respuesta, puede acudir a la Superintendencia Nacional de Salud "
            "(www.supersalud.gov.co) o a la Secretaría de Salud de su departamento o municipio."
        ),
        help_text="La Circular Única de la Supersalud (Título VII, numeral 3.3.1) exige incluirla, destacada.",
    )
    activa = models.BooleanField(default=True)
    creada = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "institución"
        verbose_name_plural = "instituciones"
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.nombre)
        if not self.prefijo_radicado:
            self.prefijo_radicado = self.slug.replace("-", "")[:3].upper()
        self.dominio = (self.dominio or "").strip().lower() or None
        super().save(*args, **kwargs)

    @property
    def logo_src(self):
        if self.logo:
            return self.logo.url
        return self.logo_url

    @property
    def enlace_whatsapp(self):
        return f"https://wa.me/{self.whatsapp}" if self.whatsapp else ""


class DeInstitucion(models.Model):
    """Base para todo lo que pertenece a una institución."""

    institucion = models.ForeignKey(
        Institucion, on_delete=models.PROTECT, related_name="+", verbose_name="institución"
    )

    class Meta:
        abstract = True


class Servicio(DeInstitucion):
    nombre = models.CharField(max_length=120)
    orden = models.PositiveSmallIntegerField(default=0)
    activo = models.BooleanField(default=True)

    class Meta:
        ordering = ["orden", "nombre"]
        unique_together = [("institucion", "nombre")]

    def __str__(self):
        return self.nombre


class Profesional(DeInstitucion):
    nombre = models.CharField(max_length=150)
    servicio = models.ForeignKey(Servicio, on_delete=models.SET_NULL, null=True, blank=True)
    activo = models.BooleanField(default=True)

    class Meta:
        verbose_name_plural = "profesionales"
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre


class Aseguradora(DeInstitucion):
    nombre = models.CharField(max_length=150)
    activa = models.BooleanField(default=True)

    class Meta:
        ordering = ["nombre"]
        unique_together = [("institucion", "nombre")]

    def __str__(self):
        return self.nombre
