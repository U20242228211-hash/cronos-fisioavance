from django.conf import settings


def institucion(request):
    """La institución del usuario que entró al panel, para mostrar su nombre en las plantillas."""
    usuario = getattr(request, "user", None)
    if usuario is not None and usuario.is_authenticated:
        return {"institucion_usuario": getattr(usuario, "institucion", None)}
    return {}


USUARIOS_DEMO = [
    ("diana", "Atención al usuario: responde las PQRSF"),
    ("cristhian", "Dirección: ve todo y administra"),
    ("recepcion", "Recepción: registra lo del buzón"),
]


def demo(request):
    """En modo demostración, los usuarios y la clave de prueba para mostrarlos en pantalla."""
    if not settings.CRONOS_DEMO:
        return {}
    return {"demo": {"clave": settings.CRONOS_DEMO_CLAVE, "usuarios": USUARIOS_DEMO}}
