from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import Group
from unfold.admin import ModelAdmin
from unfold.forms import AdminPasswordChangeForm, UserChangeForm, UserCreationForm

from instituciones.admin_base import SOLO_DIRECCION, PorInstitucionMixin, es_plataforma

from .models import Usuario

admin.site.unregister(Group)


@admin.register(Usuario)
class UsuarioAdmin(PorInstitucionMixin, BaseUserAdmin, ModelAdmin):
    permisos = {"view": SOLO_DIRECCION, "add": SOLO_DIRECCION, "change": SOLO_DIRECCION, "delete": set()}
    form = UserChangeForm
    add_form = UserCreationForm
    change_password_form = AdminPasswordChangeForm
    list_display = ("username", "nombre", "rol", "institucion", "is_active", "last_login")
    list_filter = ("rol", "is_active")
    search_fields = ("username", "first_name", "last_name", "email")
    ordering = ("institucion", "username")
    fieldsets = (
        (None, {"fields": ("username", "password")}),
        ("Persona", {"fields": ("first_name", "last_name", "email", "telefono", "cargo")}),
        ("Acceso", {"fields": ("institucion", "rol", "is_active")}),
        ("Fechas", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (None, {"classes": ("wide",), "fields": ("username", "first_name", "last_name", "email", "rol", "password1", "password2")}),
    )
    readonly_fields = ("last_login", "date_joined")

    @admin.display(description="nombre")
    def nombre(self, obj):
        return obj.get_full_name()

    def get_fieldsets(self, request, obj=None):
        fieldsets = super().get_fieldsets(request, obj)
        if obj and es_plataforma(request):
            fieldsets = fieldsets + (("Plataforma", {"fields": ("is_superuser",)}),)
        return fieldsets

    def get_exclude(self, request, obj=None):
        return []

    def get_readonly_fields(self, request, obj=None):
        campos = list(super().get_readonly_fields(request, obj))
        if not es_plataforma(request):
            campos.append("institucion")
        return campos

    def formfield_for_choice_field(self, db_field, request, **kwargs):
        campo = super().formfield_for_choice_field(db_field, request, **kwargs)
        if db_field.name == "rol" and not es_plataforma(request):
            campo.choices = [c for c in campo.choices if c[0] != Usuario.Rol.PLATAFORMA]
        return campo
