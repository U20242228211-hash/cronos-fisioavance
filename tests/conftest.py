from datetime import datetime

import pytest
from django.utils import timezone

from encuestas.servicios import crear_preguntas_por_defecto
from instituciones.models import Institucion, Servicio
from usuarios.models import Usuario

CLAVE = "clave-de-prueba-123"


def bogota(*partes):
    """Fecha y hora en Bogotá: bogota(2026, 11, 9, 10, 0)."""
    return timezone.make_aware(datetime(*partes))


@pytest.fixture
def institucion(db):
    inst = Institucion.objects.create(nombre="IPS de Prueba", slug="ips-prueba", prefijo_radicado="IPS", whatsapp="573001112233")
    Servicio.objects.create(institucion=inst, nombre="Fisioterapia")
    crear_preguntas_por_defecto(inst)
    return inst


@pytest.fixture
def otra_institucion(db):
    inst = Institucion.objects.create(nombre="Otra IPS", slug="otra-ips", prefijo_radicado="OTR")
    Servicio.objects.create(institucion=inst, nombre="Psicología")
    crear_preguntas_por_defecto(inst)
    return inst


def _usuario(institucion, nombre, rol):
    u = Usuario(username=nombre, institucion=institucion, rol=rol, email=f"{nombre}@prueba.local")
    u.set_password(CLAVE)
    u.save()
    return u


@pytest.fixture
def gestor(institucion):
    return _usuario(institucion, "gestor", Usuario.Rol.GESTOR)


@pytest.fixture
def direccion(institucion):
    return _usuario(institucion, "direccion", Usuario.Rol.DIRECCION)


@pytest.fixture
def recepcion(institucion):
    return _usuario(institucion, "recepcion", Usuario.Rol.RECEPCION)


@pytest.fixture
def gestor_otra(otra_institucion):
    return _usuario(otra_institucion, "gestor_otra", Usuario.Rol.GESTOR)


@pytest.fixture
def servicio(institucion):
    return Servicio.objects.get(institucion=institucion)


@pytest.fixture
def datos_paciente(servicio):
    return {
        "tipo": "R",
        "servicio": servicio.pk,
        "descripcion": "Me suspendieron las sesiones sin avisarme.",
        "tipo_documento": "CC",
        "numero_documento": "1075123456",
        "nombres": "Ana María",
        "apellidos": "Rojas Tovar",
        "telefono": "300 111 2233",
        "medio_respuesta": "whatsapp",
        "condicion_especial": "ninguna",
        "autoriza_datos": "on",
    }
