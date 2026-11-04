"""Base para el panel: cada usuario solo ve y modifica lo de su institución, según su rol.

El administrador de la plataforma ve todas las instituciones.
"""

from unfold.admin import ModelAdmin

from usuarios.models import Usuario

R = Usuario.Rol
TODOS = {R.DIRECCION, R.GESTOR, R.RECEPCION}
GESTION = {R.DIRECCION, R.GESTOR}
SOLO_DIRECCION = {R.DIRECCION}


def es_plataforma(request):
    return request.user.is_authenticated and request.user.es_plataforma


def rol_de(request):
    return getattr(request.user, "rol", None)


def tiene_rol(request, roles):
    return es_plataforma(request) or (
        request.user.is_authenticated and request.user.institucion_id and rol_de(request) in roles
    )


class PorInstitucionMixin:
    """``permisos`` dice qué roles pueden ver, agregar, cambiar y borrar en cada modelo."""

    permisos = {"view": GESTION, "add": GESTION, "change": GESTION, "delete": set()}
    tiene_campo_institucion = True

    def filtrar_institucion(self, request, qs):
        return qs.filter(institucion=request.user.institucion)

    def _puede(self, request, accion):
        return request.user.is_active and tiene_rol(request, self.permisos.get(accion, set()))

    def has_module_permission(self, request):
        return self._puede(request, "view")

    def has_view_permission(self, request, obj=None):
        return self._puede(request, "view") or self._puede(request, "change")

    def has_add_permission(self, request, *args):
        return self._puede(request, "add")

    def has_change_permission(self, request, obj=None):
        return self._puede(request, "change")

    def has_delete_permission(self, request, obj=None):
        return self._puede(request, "delete")

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs if es_plataforma(request) else self.filtrar_institucion(request, qs)

    def get_exclude(self, request, obj=None):
        excluidos = list(super().get_exclude(request, obj) or [])
        if not es_plataforma(request) and self.tiene_campo_institucion:
            excluidos.append("institucion")
        return excluidos

    def get_list_filter(self, request):
        filtros = list(super().get_list_filter(request))
        if es_plataforma(request) and self.tiene_campo_institucion:
            filtros.insert(0, "institucion")
        return filtros

    def save_model(self, request, obj, form, change):
        if not change and not es_plataforma(request) and self.tiene_campo_institucion:
            obj.institucion = request.user.institucion
        super().save_model(request, obj, form, change)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        campo = super().formfield_for_foreignkey(db_field, request, **kwargs)
        if campo is not None and not es_plataforma(request):
            modelo = db_field.related_model
            if modelo is Usuario or "institucion" in {f.name for f in modelo._meta.get_fields()}:
                campo.queryset = campo.queryset.filter(institucion=request.user.institucion)
        return campo


class PorInstitucionAdmin(PorInstitucionMixin, ModelAdmin):
    pass
