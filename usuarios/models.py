from django.contrib.auth.models import AbstractUser
from django.db import models


class Usuario(AbstractUser):
    """Persona del equipo de una institución que entra al panel de Cronos.

    Los pacientes no tienen cuenta: radican y responden encuestas sin registrarse.
    """

    class Rol(models.TextChoices):
        DIRECCION = "direccion", "Dirección (representante legal)"
        GESTOR = "gestor", "Atención al usuario (gestiona las PQRSF)"
        RECEPCION = "recepcion", "Recepción"
        PLATAFORMA = "plataforma", "Administrador de la plataforma"

    institucion = models.ForeignKey(
        "instituciones.Institucion",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="usuarios",
        verbose_name="institución",
    )
    rol = models.CharField(max_length=12, choices=Rol.choices, default=Rol.GESTOR)
    cargo = models.CharField(max_length=100, blank=True)
    telefono = models.CharField("teléfono", max_length=20, blank=True)

    class Meta:
        verbose_name = "usuario"
        verbose_name_plural = "usuarios"

    def save(self, *args, **kwargs):
        # Todo el equipo entra al panel; lo que puede ver lo decide su rol.
        self.is_staff = True if self.is_active else self.is_staff
        super().save(*args, **kwargs)

    @property
    def es_plataforma(self):
        return self.is_superuser or self.rol == self.Rol.PLATAFORMA

    def __str__(self):
        return self.get_full_name() or self.username
