def institucion(request):
    """La institución del usuario que entró al panel, para mostrar su nombre en las plantillas."""
    usuario = getattr(request, "user", None)
    if usuario is not None and usuario.is_authenticated:
        return {"institucion_usuario": getattr(usuario, "institucion", None)}
    return {}
