from .models import Institucion


class InstitucionMiddleware:
    """Si la petición llega por el dominio propio de una institución, la deja en ``request.institucion_dominio``."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        host = request.get_host().split(":")[0].lower()
        request.institucion_dominio = Institucion.objects.filter(dominio=host, activa=True).first()
        return self.get_response(request)
