from django.contrib import admin

from .admin_base import GESTION, SOLO_DIRECCION, PorInstitucionAdmin, es_plataforma
from .models import Aseguradora, Institucion, Profesional, Servicio


@admin.register(Institucion)
class InstitucionAdmin(PorInstitucionAdmin):
    permisos = {"view": GESTION, "add": set(), "change": SOLO_DIRECCION, "delete": set()}
    list_display = ("nombre", "municipio", "slug", "activa")
    search_fields = ("nombre", "nit")
    fieldsets = (
        ("Datos de la institución", {"fields": ("nombre", "nit", "codigo_habilitacion", "direccion", "municipio", "departamento", "pais")}),
        ("Contacto con los pacientes", {"fields": ("telefono", "whatsapp", "correo", "sitio_web", "horario_atencion")}),
        ("Imagen", {"fields": ("logo", "logo_url", "color_primario")}),
        ("Portal público", {"fields": ("slug", "prefijo_radicado", "dominio")}),
        ("Protección de datos", {"fields": ("aviso_privacidad",)}),
        ("Estado", {"fields": ("activa",)}),
    )

    tiene_campo_institucion = False

    def filtrar_institucion(self, request, qs):
        return qs.filter(pk=request.user.institucion_id)

    def get_readonly_fields(self, request, obj=None):
        return [] if es_plataforma(request) else ["slug", "prefijo_radicado", "dominio", "activa"]

    def has_add_permission(self, request, *args):
        return es_plataforma(request)



class CatalogoAdmin(PorInstitucionAdmin):
    permisos = {"view": GESTION, "add": GESTION, "change": GESTION, "delete": SOLO_DIRECCION}


@admin.register(Servicio)
class ServicioAdmin(CatalogoAdmin):
    list_display = ("nombre", "orden", "activo")
    list_editable = ("orden", "activo")
    search_fields = ("nombre",)


@admin.register(Profesional)
class ProfesionalAdmin(CatalogoAdmin):
    list_display = ("nombre", "servicio", "activo")
    list_filter = ("servicio", "activo")
    search_fields = ("nombre",)


@admin.register(Aseguradora)
class AseguradoraAdmin(CatalogoAdmin):
    list_display = ("nombre", "activa")
    search_fields = ("nombre",)
