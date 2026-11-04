"""Da de alta una institución nueva con sus preguntas de encuesta y su primer usuario de dirección.

    python manage.py crear_institucion "IPS Ejemplo" --slug ips-ejemplo --usuario direccion --correo dir@ips.com
"""

from django.core.management.base import BaseCommand, CommandError
from django.utils.crypto import get_random_string

from encuestas.servicios import crear_preguntas_por_defecto
from instituciones.models import Institucion
from usuarios.models import Usuario


class Command(BaseCommand):
    help = "Crea una institución nueva lista para usar Cronos."

    def add_arguments(self, parser):
        parser.add_argument("nombre")
        parser.add_argument("--slug", required=True)
        parser.add_argument("--usuario", required=True, help="Usuario de la dirección de la institución")
        parser.add_argument("--correo", default="")

    def handle(self, nombre, slug, usuario, correo, **opciones):
        if Institucion.objects.filter(slug=slug).exists():
            raise CommandError(f"Ya existe una institución con el identificador «{slug}».")
        institucion = Institucion.objects.create(nombre=nombre, slug=slug, correo=correo)
        crear_preguntas_por_defecto(institucion)
        clave = get_random_string(14)
        direccion = Usuario(username=usuario, email=correo, institucion=institucion, rol=Usuario.Rol.DIRECCION)
        direccion.set_password(clave)
        direccion.save()
        self.stdout.write(self.style.SUCCESS(f"Institución creada: {institucion} (/{slug}/)"))
        self.stdout.write(f"Usuario de la dirección: {usuario} · clave temporal: {clave}")
        self.stdout.write("Pídale que la cambie al entrar y que cargue servicios, logo y aviso de privacidad.")
