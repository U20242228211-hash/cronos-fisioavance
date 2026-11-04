from django.contrib import admin, messages
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils import timezone
from django.utils.html import format_html
from unfold.admin import TabularInline
from unfold.contrib.filters.admin import RangeDateFilter
from unfold.decorators import action, display

from instituciones.admin_base import GESTION, TODOS, PorInstitucionAdmin, tiene_rol
from pqrsf.notificaciones import enlace_whatsapp

from . import servicios
from .models import InvitacionEncuesta, Pregunta, RespuestaEncuesta, RespuestaItem


def url_encuesta(request, invitacion):
    return request.build_absolute_uri(
        reverse("portal:encuesta_invitacion", kwargs={"slug": invitacion.institucion.slug, "token": invitacion.token})
    )


@admin.register(Pregunta)
class PreguntaAdmin(PorInstitucionAdmin):
    list_display = ("orden", "texto", "escala", "indicador", "activa")
    list_display_links = ("texto",)
    list_editable = ("orden", "activa")


@admin.register(InvitacionEncuesta)
class InvitacionEncuestaAdmin(PorInstitucionAdmin):
    permisos = {"view": TODOS, "add": TODOS, "change": GESTION, "delete": set()}
    list_display = ("nombre_paciente", "servicio", "fin_tratamiento", "ver_estado", "ver_enviar")
    list_filter = ("servicio", ("fin_tratamiento", RangeDateFilter))
    list_filter_submit = True
    search_fields = ("nombre_paciente", "telefono")
    fields = ("nombre_paciente", "telefono", "correo", "servicio", "profesional", "fin_tratamiento", "ver_enlace")
    readonly_fields = ("ver_enlace",)
    actions_detail = ["enviar_whatsapp"]

    def has_change_permission(self, request, obj=None):
        return tiene_rol(request, TODOS)

    def save_model(self, request, obj, form, change):
        if not change:
            obj.creada_por = request.user
        super().save_model(request, obj, form, change)

    def response_add(self, request, obj, post_url_continue=None):
        messages.success(request, "Invitación lista. Envíela con el botón «Enviar por WhatsApp».")
        return redirect(reverse("admin:encuestas_invitacionencuesta_change", args=[obj.pk]))

    @display(description="estado", label={"respondida": "success", "pendiente": "warning", "vencida": "danger", "sin_enviar": "info"})
    def ver_estado(self, obj):
        if obj.respondida:
            return "respondida", "Respondida"
        if timezone.now() > obj.expira_en:
            return "vencida", "Venció"
        if not obj.enviada_en:
            return "sin_enviar", "Sin enviar"
        return "pendiente", "Enviada"

    @display(description="")
    def ver_enviar(self, obj):
        if obj.respondida or not obj.telefono:
            return ""
        return format_html(
            '<a class="cronos-boton" href="{}">Enviar por WhatsApp</a>',
            reverse("admin:encuestas_invitacionencuesta_enviar_whatsapp", args=[obj.pk]),
        )

    @display(description="enlace de la encuesta")
    def ver_enlace(self, obj):
        if not obj.pk:
            return "Aparece al guardar."
        enlace = reverse("portal:encuesta_invitacion", kwargs={"slug": obj.institucion.slug, "token": obj.token})
        return format_html('<a href="{0}" target="_blank">{0}</a>', enlace)

    def has_enviar_permission(self, request, object_id=None):
        return tiene_rol(request, TODOS)

    @action(description="Enviar por WhatsApp", icon="chat", permissions=["enviar"], url_path="enviar-whatsapp")
    def enviar_whatsapp(self, request, object_id):
        invitacion = get_object_or_404(self.get_queryset(request), pk=object_id)
        if not invitacion.telefono:
            messages.warning(request, "La invitación no tiene celular.")
            return redirect(reverse("admin:encuestas_invitacionencuesta_change", args=[object_id]))
        invitacion.enviada_en = timezone.now()
        invitacion.save(update_fields=["enviada_en"])
        mensaje = servicios.mensaje_invitacion(invitacion, url_encuesta(request, invitacion))
        return redirect(enlace_whatsapp(invitacion.telefono, mensaje))


class RespuestaItemInline(TabularInline):
    model = RespuestaItem
    extra = 0
    can_delete = False
    max_num = 0
    fields = ("pregunta", "ver_valor")
    readonly_fields = fields

    @display(description="respuesta")
    def ver_valor(self, obj):
        return dict(obj.pregunta.opciones).get(obj.valor, "Sin respuesta")

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(RespuestaEncuesta)
class RespuestaEncuestaAdmin(PorInstitucionAdmin):
    permisos = {"view": GESTION, "add": set(), "change": GESTION, "delete": set()}
    list_display = ("ver_fecha", "servicio", "canal", "ver_satisfaccion", "ver_recomendacion", "ver_alerta", "atendida")
    list_filter = ("servicio", "canal", "requiere_atencion", "atendida", ("respondida_en", RangeDateFilter))
    list_filter_submit = True
    search_fields = ("comentario", "invitacion__nombre_paciente")
    fields = ("respondida_en", "servicio", "canal", "ver_paciente", "comentario", "requiere_atencion", "atendida", "pqrsf")
    readonly_fields = ("respondida_en", "servicio", "canal", "ver_paciente", "comentario", "requiere_atencion", "pqrsf")
    inlines = [RespuestaItemInline]
    actions = ["marcar_revisadas"]

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("servicio", "invitacion").prefetch_related("items__pregunta")

    @display(description="fecha", ordering="respondida_en")
    def ver_fecha(self, obj):
        return timezone.localtime(obj.respondida_en).strftime("%d/%m/%Y %I:%M %p")

    def _etiqueta(self, obj, indicador):
        item = next((i for i in obj.items.all() if i.pregunta.indicador == indicador), None)
        if not item or item.valor is None:
            return "sin_dato", "—"
        texto = dict(item.pregunta.opciones)[item.valor]
        if item.pregunta.es_positiva(item.valor):
            return "buena", texto
        return ("mala" if item.pregunta.es_mala(item.valor) else "regular"), texto

    @display(description="satisfacción global", label={"buena": "success", "regular": "warning", "mala": "danger", "sin_dato": "info"})
    def ver_satisfaccion(self, obj):
        return self._etiqueta(obj, Pregunta.Indicador.SATISFACCION)

    @display(description="¿recomendaría?", label={"buena": "success", "regular": "warning", "mala": "danger", "sin_dato": "info"})
    def ver_recomendacion(self, obj):
        return self._etiqueta(obj, Pregunta.Indicador.RECOMENDACION)

    @display(description="alerta", label={True: "danger", False: "success"})
    def ver_alerta(self, obj):
        return obj.requiere_atencion, "Mala calificación" if obj.requiere_atencion else "Sin novedad"

    @display(description="paciente")
    def ver_paciente(self, obj):
        if obj.invitacion:
            return f"{obj.invitacion.nombre_paciente} · {obj.invitacion.telefono or obj.invitacion.correo or ''}"
        return "Anónima (por código QR o tableta)"

    @admin.action(description="Marcar como revisadas")
    def marcar_revisadas(self, request, queryset):
        total = queryset.update(atendida=True)
        messages.success(request, f"{total} encuestas marcadas como revisadas.")
