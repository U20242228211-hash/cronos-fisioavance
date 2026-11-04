"""Lo que ven los pacientes, sin crear cuenta: radicar, consultar su caso y responder la encuesta."""

import io

import qrcode
import qrcode.image.svg
from django.conf import settings
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from encuestas import servicios as servicios_encuesta
from encuestas.models import InvitacionEncuesta, RespuestaEncuesta
from instituciones.models import Institucion, Servicio
from pqrsf import servicios
from pqrsf.models import PQRSF

from .forms import ConsultaForm, PQRSFPublicaForm

CANALES = {"qr": PQRSF.Canal.WEB, "web": PQRSF.Canal.WEB, "whatsapp": PQRSF.Canal.WHATSAPP, "tableta": PQRSF.Canal.TABLETA}


def _institucion(slug):
    return get_object_or_404(Institucion, slug=slug, activa=True)


def _modo_tableta(request):
    return request.GET.get("canal") == "tableta" or request.POST.get("canal") == "tableta"


def raiz(request):
    if request.institucion_dominio:
        return inicio(request, request.institucion_dominio.slug)
    if settings.CRONOS_INSTITUCION_POR_DEFECTO:
        return redirect("portal:inicio", slug=settings.CRONOS_INSTITUCION_POR_DEFECTO)
    return render(request, "portal/plataforma.html")


def inicio(request, slug):
    institucion = _institucion(slug)
    return render(request, "portal/inicio.html", {"institucion": institucion, "tableta": _modo_tableta(request)})


@require_http_methods(["GET", "POST"])
def radicar(request, slug):
    institucion = _institucion(slug)
    canal = request.POST.get("canal") or request.GET.get("canal") or "web"
    if request.method == "POST":
        form = PQRSFPublicaForm(request.POST, request.FILES, institucion=institucion)
        if form.is_valid():
            pqrsf = form.save(commit=False)
            pqrsf.institucion = institucion
            pqrsf.canal = CANALES.get(canal, PQRSF.Canal.WEB)
            servicios.radicar(pqrsf)
            destino = reverse("portal:constancia", kwargs={"slug": slug, "token": pqrsf.token})
            return redirect(f"{destino}?canal={canal}" if canal == "tableta" else destino)
    else:
        inicial = {"tipo": request.GET.get("tipo") or None, "servicio": request.GET.get("servicio") or None}
        form = PQRSFPublicaForm(initial=inicial, institucion=institucion)
    return render(
        request,
        "portal/radicar.html",
        {"institucion": institucion, "form": form, "canal": canal, "tableta": canal == "tableta"},
    )


def constancia(request, slug, token):
    institucion = _institucion(slug)
    pqrsf = get_object_or_404(PQRSF, institucion=institucion, token=token)
    return render(
        request,
        "portal/constancia.html",
        {"institucion": institucion, "pqrsf": pqrsf, "tableta": _modo_tableta(request), "regla": pqrsf.regla},
    )


@require_http_methods(["GET", "POST"])
def consulta(request, slug):
    institucion = _institucion(slug)
    form = ConsultaForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        radicado = form.cleaned_data["radicado"].strip().upper()
        dato = form.cleaned_data["documento"].strip()
        pqrsf = PQRSF.objects.filter(institucion=institucion, radicado=radicado).first()
        if pqrsf and (dato == pqrsf.numero_documento or dato.upper() == pqrsf.codigo_consulta):
            return redirect("portal:estado", slug=slug, token=pqrsf.token)
        form.add_error(None, "No encontramos una PQRSF con esos datos. Revise el número de radicado y el documento.")
    return render(request, "portal/consulta.html", {"institucion": institucion, "form": form})


def estado(request, slug, token):
    institucion = _institucion(slug)
    pqrsf = get_object_or_404(PQRSF, institucion=institucion, token=token)
    actuaciones = pqrsf.actuaciones.filter(visible_paciente=True)
    return render(request, "portal/estado.html", {"institucion": institucion, "pqrsf": pqrsf, "actuaciones": actuaciones})


@require_http_methods(["GET", "POST"])
def encuesta(request, slug, token=None):
    institucion = _institucion(slug)
    invitacion = None
    if token:
        invitacion = get_object_or_404(InvitacionEncuesta, institucion=institucion, token=token)
        if invitacion.respondida:
            return render(request, "portal/encuesta_gracias.html", {"institucion": institucion, "ya_respondida": True})
        if not invitacion.vigente:
            return render(request, "portal/encuesta_gracias.html", {"institucion": institucion, "vencida": True})
    preguntas = list(servicios_encuesta.preguntas_activas(institucion))
    servicios_lista = Servicio.objects.filter(institucion=institucion, activo=True)
    canal = request.GET.get("canal") or request.POST.get("canal") or ("invitacion" if invitacion else "qr")
    error = ""
    if request.method == "POST":
        valores = {}
        for pregunta in preguntas:
            valor = request.POST.get(f"p{pregunta.id}")
            if valor and valor.isdigit():
                valores[pregunta.id] = int(valor)
        servicio = invitacion.servicio if invitacion else servicios_lista.filter(pk=request.POST.get("servicio") or 0).first()
        if not servicio:
            error = "Elija el servicio que recibió."
        elif len(valores) < len(preguntas):
            error = "Le faltó responder alguna pregunta."
        else:
            respuesta = servicios_encuesta.registrar_respuesta(
                institucion,
                valores,
                comentario=request.POST.get("comentario", ""),
                servicio=servicio,
                canal={"tableta": RespuestaEncuesta.Canal.TABLETA, "invitacion": RespuestaEncuesta.Canal.INVITACION}.get(
                    canal, RespuestaEncuesta.Canal.QR
                ),
                invitacion=invitacion,
            )
            return render(
                request,
                "portal/encuesta_gracias.html",
                {"institucion": institucion, "respuesta": respuesta, "tableta": canal == "tableta"},
            )
    return render(
        request,
        "portal/encuesta.html",
        {
            "institucion": institucion,
            "invitacion": invitacion,
            "primer_nombre": invitacion.nombre_paciente.split()[0] if invitacion else "",
            "preguntas": preguntas,
            "servicios": servicios_lista,
            "canal": canal,
            "error": error,
            "tableta": canal == "tableta",
        },
    )


def avisos(request, slug):
    institucion = _institucion(slug)
    hoy = timezone.localdate()
    publicados = PQRSF.objects.filter(
        institucion=institucion, anonima=True, aviso_desde__lte=hoy, aviso_hasta__gte=hoy
    ).order_by("-respondida_en")
    return render(request, "portal/avisos.html", {"institucion": institucion, "avisos": publicados})


def codigo_qr(request, slug, destino):
    institucion = _institucion(slug)
    rutas = {"pqrsf": "portal:radicar", "encuesta": "portal:encuesta", "consulta": "portal:consulta", "inicio": "portal:inicio"}
    if destino not in rutas:
        raise Http404
    url = request.build_absolute_uri(reverse(rutas[destino], kwargs={"slug": institucion.slug})) + "?canal=qr"
    imagen = qrcode.make(url, image_factory=qrcode.image.svg.SvgPathImage, box_size=12, border=2)
    buffer = io.BytesIO()
    imagen.save(buffer)
    return HttpResponse(buffer.getvalue(), content_type="image/svg+xml")
