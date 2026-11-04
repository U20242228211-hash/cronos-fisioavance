from django import forms
from django.contrib import admin, messages
from django.db.models import Case, IntegerField, Value, When
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils import timezone
from django.utils.html import format_html, format_html_join
from unfold.admin import TabularInline
from unfold.contrib.filters.admin import RangeDateFilter
from unfold.decorators import action, display

from instituciones.admin_base import GESTION, SOLO_DIRECCION, TODOS, PorInstitucionAdmin, es_plataforma, tiene_rol

from . import notificaciones, servicios
from .models import CLASIFICACIONES_POR_TIPO, PQRSF, Actuacion, ReglaPlazo

ABIERTAS = [PQRSF.Estado.RADICADA, PQRSF.Estado.EN_TRAMITE]
COLORES_SEMAFORO = {
    "verde": "success",
    "amarillo": "warning",
    "rojo": "danger",
    "vencida": "danger",
    "a_tiempo": "info",
    "tarde": "danger",
}
TEXTO_SEMAFORO = {
    "verde": "A tiempo",
    "amarillo": "Pasó la mitad",
    "rojo": "Por vencer",
    "vencida": "Vencida",
    "a_tiempo": "Respondida a tiempo",
    "tarde": "Respondida tarde",
}


def insignia_abiertas(request):
    if not request.user.is_authenticated:
        return None
    qs = PQRSF.objects.filter(estado__in=ABIERTAS)
    if not es_plataforma(request):
        qs = qs.filter(institucion=request.user.institucion)
    total = qs.count()
    return str(total) if total else None


def url_publica(request, pqrsf):
    return request.build_absolute_uri(
        reverse("portal:estado", kwargs={"slug": pqrsf.institucion.slug, "token": pqrsf.token})
    )


class ActuacionInline(TabularInline):
    model = Actuacion
    extra = 0
    can_delete = False
    max_num = 0
    fields = ("fecha", "tipo", "descripcion", "usuario", "visible_paciente")
    readonly_fields = fields
    verbose_name = "actuación"
    verbose_name_plural = "Histórico (no se puede modificar)"

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False


class PQRSFForm(forms.ModelForm):
    nota_interna = forms.CharField(
        label="Agregar nota interna",
        required=False,
        widget=forms.Textarea(attrs={"rows": 2}),
        help_text="Queda en el histórico. El paciente no la ve.",
    )

    class Meta:
        model = PQRSF
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if "clasificacion" in self.fields and self.instance.pk:
            permitidas = CLASIFICACIONES_POR_TIPO.get(self.instance.tipo, [])
            self.fields["clasificacion"].choices = [c for c in self.fields["clasificacion"].choices if c[0] in permitidas]
            self.fields["clasificacion"].required = True
        if "canal" in self.fields and not self.instance.pk:
            self.fields["canal"].choices = [
                c for c in PQRSF.Canal.choices if c[0] in (PQRSF.Canal.BUZON, PQRSF.Canal.PRESENCIAL, PQRSF.Canal.CORREO)
            ]

    def clean(self):
        datos = super().clean()
        if not self.instance.pk:
            medio = datos.get("medio_respuesta")
            if datos.get("anonima"):
                datos["medio_respuesta"] = PQRSF.MedioRespuesta.AVISO
            elif medio == PQRSF.MedioRespuesta.WHATSAPP and not datos.get("telefono"):
                self.add_error("telefono", "Para responder por WhatsApp hace falta el celular.")
            elif medio == PQRSF.MedioRespuesta.CORREO and not datos.get("correo"):
                self.add_error("correo", "Para responder por correo hace falta el correo.")
        return datos


@admin.register(PQRSF)
class PQRSFAdmin(PorInstitucionAdmin):
    form = PQRSFForm
    permisos = {"view": GESTION, "add": TODOS, "change": GESTION, "delete": set()}
    list_display = (
        "radicado",
        "ver_tipo",
        "ver_peticionario",
        "servicio",
        "ver_recibida",
        "ver_vence",
        "ver_semaforo",
        "ver_estado",
        "asignada_a",
    )
    list_filter = (
        "estado",
        "tipo",
        "clasificacion",
        "canal",
        "servicio",
        "anonima",
        ("recibida_en", RangeDateFilter),
    )
    list_filter_submit = True
    search_fields = ("radicado", "numero_documento", "nombres", "apellidos", "descripcion")
    list_per_page = 25
    inlines = [ActuacionInline]
    actions_detail = ["enviar_whatsapp", "enviar_correo", "cerrar_caso", "reabrir_caso", "ver_como_paciente"]
    autocomplete_fields = ()
    radio_fields = {"tipo": admin.HORIZONTAL}

    campos_paciente = (
        "anonima", "tipo_documento", "numero_documento", "nombres", "apellidos", "sexo", "fecha_nacimiento",
        "telefono", "correo", "municipio", "vinculacion", "aseguradora", "condicion_especial", "es_acudiente",
        "nombre_paciente", "medio_respuesta", "autoriza_datos",
    )

    def get_fieldsets(self, request, obj=None):
        if obj is None:  # registrar lo que llegó por el buzón, en persona o por correo
            return (
                ("Cómo llegó", {"fields": ("canal", "recibida_en", "tipo")}),
                ("Lo que dice", {"fields": ("servicio", "profesional", "descripcion", "adjunto")}),
                ("Quién la presenta", {"fields": self.campos_paciente}),
            )
        return (
            ("Caso", {"fields": ("ver_resumen",)}),
            ("Lo que dice el paciente", {"fields": ("tipo", "canal", "recibida_en", "servicio", "profesional", "descripcion", "adjunto")}),
            ("Quién la presenta", {"classes": ("collapse",), "fields": ("ver_peticionario_completo",)}),
            ("Gestión", {"fields": ("clasificacion", "ver_clasificacion_propuesta", "asignada_a", "nota_interna")}),
            ("Respuesta al paciente", {"fields": ("respuesta", "respondida_en", "comunicada_en", "aviso_desde", "aviso_hasta")}),
        )

    def get_readonly_fields(self, request, obj=None):
        if obj is None:
            return ()
        campos = [
            "ver_resumen", "tipo", "canal", "recibida_en", "servicio", "profesional", "descripcion", "adjunto",
            "ver_peticionario_completo", "ver_clasificacion_propuesta", "respondida_en", "comunicada_en",
            "aviso_desde", "aviso_hasta",
        ]
        if obj.estado == PQRSF.Estado.CERRADA:
            campos += ["clasificacion", "asignada_a", "respuesta"]
        return campos

    def get_queryset(self, request):
        abierta = Case(When(estado__in=ABIERTAS, then=Value(0)), default=Value(1), output_field=IntegerField())
        return (
            super().get_queryset(request)
            .select_related("servicio", "asignada_a", "institucion")
            .annotate(cerrada_orden=abierta)
        )

    def get_ordering(self, request):
        return ["cerrada_orden", "vence_en", "-recibida_en"]

    def get_changeform_initial_data(self, request):
        datos = super().get_changeform_initial_data(request)
        datos.setdefault("canal", PQRSF.Canal.BUZON)
        datos.setdefault("recibida_en", timezone.now())
        datos.setdefault("medio_respuesta", PQRSF.MedioRespuesta.WHATSAPP)
        return datos

    # --- Guardar: cada cambio pasa por los servicios para que quede en el histórico -------------
    def save_model(self, request, obj, form, change):
        if not change:
            if not es_plataforma(request):
                obj.institucion = request.user.institucion
            servicios.radicar(obj, request.user)
            messages.success(request, f"Quedó radicada con el número {obj.radicado}.")
            return
        cambios = set(form.changed_data)
        anterior = PQRSF.objects.get(pk=obj.pk)
        guardado = False
        if "clasificacion" in cambios:
            servicios.clasificar(obj, obj.clasificacion, request.user)
            guardado = True
        if "asignada_a" in cambios:
            servicios.asignar(obj, obj.asignada_a, request.user)
            guardado = True
        if "respuesta" in cambios and obj.respuesta.strip():
            if anterior.abierta:
                servicios.responder(obj, obj.respuesta, request.user)
                messages.success(request, "Respuesta guardada. Ahora envíela con el botón de WhatsApp o de correo.")
            else:
                obj.save()
                servicios.nota(obj, "Se corrigió el texto de la respuesta.", request.user)
            guardado = True
        if not guardado:
            obj.save()
        if form.cleaned_data.get("nota_interna"):
            servicios.nota(obj, form.cleaned_data["nota_interna"], request.user)

    def save_related(self, request, form, formsets, change):
        form.save_m2m()

    # --- Columnas ----------------------------------------------------------------------------
    @display(description="tipo", label={"P": "info", "Q": "warning", "R": "danger", "S": "primary", "F": "success"})
    def ver_tipo(self, obj):
        return obj.tipo, obj.get_tipo_display()

    @display(description="quién", ordering="apellidos")
    def ver_peticionario(self, obj):
        return obj.nombre_completo

    @display(description="recibida", ordering="recibida_en")
    def ver_recibida(self, obj):
        return timezone.localtime(obj.recibida_en).strftime("%d/%m/%Y %I:%M %p")

    @display(description="vence", ordering="vence_en")
    def ver_vence(self, obj):
        return timezone.localtime(obj.vence_en).strftime("%d/%m/%Y %I:%M %p") if obj.vence_en else "—"

    @display(description="término", label=COLORES_SEMAFORO)
    def ver_semaforo(self, obj):
        estado = obj.semaforo
        return estado, TEXTO_SEMAFORO[estado]

    @display(description="estado", ordering="estado", label={
        "radicada": "warning", "en_tramite": "info", "respondida": "success", "cerrada": "primary",
    })
    def ver_estado(self, obj):
        return obj.estado, obj.get_estado_display()

    @display(description="resumen del caso")
    def ver_resumen(self, obj):
        vence = timezone.localtime(obj.vence_en).strftime("%d/%m/%Y %I:%M %p") if obj.vence_en else "sin término"
        regla = obj.regla
        termino = str(regla).split(": ", 1)[-1] if regla else "—"
        confirmada = "confirmada" if obj.clasificacion_confirmada else "propuesta por el sistema, falta confirmarla"
        return format_html(
            '<div class="cronos-resumen"><p><b>{}</b> · {} · {}</p>'
            "<p>Término: <b>{}</b> ({}). Vence: <b>{}</b>. Va en el <b>{} %</b> del término: {}.</p>"
            "<p>Clasificación: {} ({}).</p></div>",
            obj.radicado, obj.get_tipo_display(), obj.get_estado_display(), termino,
            regla.norma if regla else "", vence, round(obj.porcentaje()), TEXTO_SEMAFORO[obj.semaforo].lower(),
            obj.get_clasificacion_display() or "—", confirmada,
        )

    @display(description="datos")
    def ver_peticionario_completo(self, obj):
        if obj.anonima:
            return "Anónima: la respuesta se publica por aviso en la cartelera y en el portal."
        filas = [
            ("Nombre", obj.nombre_completo),
            ("Documento", f"{obj.tipo_documento} {obj.numero_documento}"),
            ("Celular", obj.telefono or "—"),
            ("Correo", obj.correo or "—"),
            ("Sexo", obj.get_sexo_display() or "—"),
            ("Edad", f"{obj.edad} años" if obj.edad is not None else "—"),
            ("Municipio", obj.municipio or "—"),
            ("Vinculación", f"{obj.get_vinculacion_display() or '—'} {obj.aseguradora or ''}"),
            ("Condición especial", obj.get_condicion_especial_display()),
            ("Acudiente de", obj.nombre_paciente if obj.es_acudiente else "—"),
            ("Quiere la respuesta por", obj.get_medio_respuesta_display()),
            ("Autorizó sus datos", timezone.localtime(obj.autorizacion_en).strftime("%d/%m/%Y %I:%M %p") if obj.autorizacion_en else "No"),
        ]
        return format_html(
            "<table class='cronos-tabla'>{}</table>",
            format_html_join("", "<tr><th>{}</th><td>{}</td></tr>", filas),
        )

    @display(description="propuesta del sistema")
    def ver_clasificacion_propuesta(self, obj):
        return obj.get_clasificacion_propuesta_display() or "—"

    # --- Botones del caso --------------------------------------------------------------------
    def has_gestionar_permission(self, request, object_id=None):
        return tiene_rol(request, GESTION)

    def _caso(self, request, object_id):
        return get_object_or_404(self.get_queryset(request), pk=object_id)

    def _volver(self, object_id):
        return redirect(reverse("admin:pqrsf_pqrsf_change", args=[object_id]))

    @action(description="Enviar respuesta por WhatsApp", icon="chat", permissions=["gestionar"])
    def enviar_whatsapp(self, request, object_id):
        pqrsf = self._caso(request, object_id)
        if not pqrsf.respuesta:
            messages.warning(request, "Primero escriba y guarde la respuesta.")
            return self._volver(object_id)
        if not pqrsf.telefono:
            messages.warning(request, "Esta PQRSF no tiene celular registrado.")
            return self._volver(object_id)
        enlace = notificaciones.enlace_whatsapp(pqrsf.telefono, notificaciones.mensaje_respuesta(pqrsf, url_publica(request, pqrsf)))
        servicios.comunicar(pqrsf, "WhatsApp", request.user)
        return redirect(enlace)

    @action(description="Enviar respuesta por correo", icon="mail", permissions=["gestionar"])
    def enviar_correo(self, request, object_id):
        pqrsf = self._caso(request, object_id)
        if not pqrsf.respuesta:
            messages.warning(request, "Primero escriba y guarde la respuesta.")
        elif notificaciones.enviar_respuesta_por_correo(pqrsf, url_publica(request, pqrsf)):
            servicios.comunicar(pqrsf, "correo electrónico", request.user)
            messages.success(request, f"Se envió la respuesta a {pqrsf.correo}.")
        else:
            messages.warning(request, "No se pudo enviar: revise que tenga correo.")
        return self._volver(object_id)

    @action(description="Cerrar caso", icon="task_alt", permissions=["gestionar"])
    def cerrar_caso(self, request, object_id):
        pqrsf = self._caso(request, object_id)
        if pqrsf.estado != PQRSF.Estado.RESPONDIDA:
            messages.warning(request, "Solo se cierra un caso que ya tiene respuesta.")
        else:
            servicios.cerrar(pqrsf, request.user)
            messages.success(request, "Caso cerrado.")
        return self._volver(object_id)

    @action(description="Reabrir", icon="restart_alt", permissions=["gestionar"])
    def reabrir_caso(self, request, object_id):
        pqrsf = self._caso(request, object_id)
        if pqrsf.abierta:
            messages.info(request, "El caso ya está abierto.")
        else:
            servicios.reabrir(pqrsf, "a solicitud del equipo.", request.user)
            messages.success(request, "Caso reabierto.")
        return self._volver(object_id)

    @action(description="Ver lo que ve el paciente", icon="visibility", permissions=["gestionar"])
    def ver_como_paciente(self, request, object_id):
        return redirect(url_publica(request, self._caso(request, object_id)))


@admin.register(ReglaPlazo)
class ReglaPlazoAdmin(PorInstitucionAdmin):
    permisos = {"view": GESTION, "add": SOLO_DIRECCION, "change": SOLO_DIRECCION, "delete": SOLO_DIRECCION}
    list_display = ("tipo", "clasificacion", "cantidad", "unidad", "norma", "ver_alcance")
    list_filter = ("tipo", "unidad")

    def filtrar_institucion(self, request, qs):
        from django.db.models import Q

        return qs.filter(Q(institucion=request.user.institucion) | Q(institucion__isnull=True))

    @display(description="aplica a")
    def ver_alcance(self, obj):
        return obj.institucion or "Todas (norma)"

    def has_change_permission(self, request, obj=None):
        if obj is not None and obj.institucion_id is None and not es_plataforma(request):
            return False
        return super().has_change_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        if obj is not None and obj.institucion_id is None and not es_plataforma(request):
            return False
        return super().has_delete_permission(request, obj)
