"""Configuración de Cronos.

Todo lo que cambia entre el computador de desarrollo y un servidor (claves, base de datos, correo,
dominios) se lee de variables de entorno o del archivo .env. Ver .env.example.
"""

import os
from pathlib import Path

import dj_database_url
from django.templatetags.static import static
from django.urls import reverse_lazy
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


def _lista(nombre, defecto=""):
    return [v.strip() for v in os.environ.get(nombre, defecto).split(",") if v.strip()]


SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "solo-para-desarrollo")
DEBUG = os.environ.get("DJANGO_DEBUG", "0") == "1"
ALLOWED_HOSTS = _lista("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1")
CSRF_TRUSTED_ORIGINS = _lista("DJANGO_CSRF_TRUSTED_ORIGINS")

INSTALLED_APPS = [
    "unfold",
    "unfold.contrib.filters",
    "unfold.contrib.forms",
    "unfold.contrib.inlines",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",
    "instituciones",
    "usuarios",
    "pqrsf",
    "encuestas",
    "portal",
    "tablero",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "instituciones.middleware.InstitucionMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "instituciones.context_processors.institucion",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# Base de datos: PostgreSQL en desarrollo; en un hosting compartido con cPanel se puede usar MySQL
# cambiando DATABASE_URL (mysql://...). El código no usa nada propio de un solo motor.
DATABASES = {
    "default": dj_database_url.config(
        default="postgres://localhost/cronos", conn_max_age=600
    )
}
if DATABASES["default"]["ENGINE"].endswith("mysql"):
    import pymysql

    pymysql.version_info = (2, 2, 4, "final", 0)
    pymysql.install_as_MySQLdb()

AUTH_USER_MODEL = "usuarios.Usuario"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "es-co"
TIME_ZONE = "America/Bogota"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"
        if not DEBUG
        else "django.contrib.staticfiles.storage.StaticFilesStorage"
    },
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
LOGIN_URL = "admin:login"

# Correo: en desarrollo se muestra en la consola. En producción, EMAIL_URL=smtp://usuario:clave@host:587
_correo = os.environ.get("EMAIL_URL", "")
if _correo:
    from urllib.parse import unquote, urlparse

    _u = urlparse(_correo)
    EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
    EMAIL_HOST = _u.hostname
    EMAIL_PORT = _u.port or 587
    EMAIL_HOST_USER = unquote(_u.username or "")
    EMAIL_HOST_PASSWORD = unquote(_u.password or "")
    EMAIL_USE_TLS = EMAIL_PORT == 587
    EMAIL_USE_SSL = EMAIL_PORT == 465
else:
    EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
DEFAULT_FROM_EMAIL = os.environ.get("DEFAULT_FROM_EMAIL", "Cronos <no-responder@localhost>")

CRONOS_INSTITUCION_POR_DEFECTO = os.environ.get("CRONOS_INSTITUCION_POR_DEFECTO", "")

if not DEBUG:
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")


def environment_callback(request):
    return ["Desarrollo", "warning"] if DEBUG else ["Producción", "success"]


UNFOLD = {
    "SITE_TITLE": "Cronos",
    "SITE_HEADER": "Cronos",
    "SITE_SUBHEADER": "PQRSF y satisfacción",
    "SITE_SYMBOL": "schedule",
    "SITE_URL": "/",
    "SHOW_HISTORY": False,
    "SHOW_VIEW_ON_SITE": False,
    "ENVIRONMENT": "config.settings.environment_callback",
    "DASHBOARD_CALLBACK": "tablero.views.dashboard_callback",
    "STYLES": [lambda request: static("tablero/cronos-admin.css")],
    "COLORS": {
        "primary": {
            "50": "oklch(97.5% .02 175)",
            "100": "oklch(94.5% .045 175)",
            "200": "oklch(89% .08 175)",
            "300": "oklch(82% .11 176)",
            "400": "oklch(72% .13 177)",
            "500": "oklch(62% .12 178)",
            "600": "oklch(53% .105 180)",
            "700": "oklch(46% .09 182)",
            "800": "oklch(39% .075 184)",
            "900": "oklch(33% .06 186)",
            "950": "oklch(24% .045 188)",
        },
    },
    "SIDEBAR": {
        "show_search": True,
        "show_all_applications": False,
        "navigation": [
            {
                "title": "Atención al usuario",
                "items": [
                    {"title": "Tablero", "icon": "dashboard", "link": reverse_lazy("admin:index")},
                    {
                        "title": "Bandeja de PQRSF",
                        "icon": "inbox",
                        "link": reverse_lazy("admin:pqrsf_pqrsf_changelist"),
                        "badge": "pqrsf.admin.insignia_abiertas",
                    },
                    {
                        "title": "Registrar del buzón",
                        "icon": "mark_email_unread",
                        "link": reverse_lazy("admin:pqrsf_pqrsf_add"),
                    },
                    {
                        "title": "Avisos publicados",
                        "icon": "campaign",
                        "link": reverse_lazy("tablero:avisos"),
                    },
                ],
            },
            {
                "title": "Satisfacción",
                "items": [
                    {
                        "title": "Enviar encuesta",
                        "icon": "send",
                        "link": reverse_lazy("admin:encuestas_invitacionencuesta_add"),
                    },
                    {
                        "title": "Invitaciones",
                        "icon": "forward_to_inbox",
                        "link": reverse_lazy("admin:encuestas_invitacionencuesta_changelist"),
                    },
                    {
                        "title": "Respuestas",
                        "icon": "sentiment_satisfied",
                        "link": reverse_lazy("admin:encuestas_respuestaencuesta_changelist"),
                    },
                ],
            },
            {
                "title": "Informes",
                "items": [
                    {"title": "Reportes", "icon": "description", "link": reverse_lazy("tablero:reportes")},
                    {"title": "Carteles con QR", "icon": "qr_code_2", "link": reverse_lazy("tablero:carteles")},
                ],
            },
            {
                "title": "Configuración",
                "collapsible": True,
                "items": [
                    {"title": "Institución", "icon": "local_hospital", "link": reverse_lazy("admin:instituciones_institucion_changelist")},
                    {"title": "Servicios", "icon": "medical_services", "link": reverse_lazy("admin:instituciones_servicio_changelist")},
                    {"title": "Profesionales", "icon": "badge", "link": reverse_lazy("admin:instituciones_profesional_changelist")},
                    {"title": "Aseguradoras", "icon": "shield", "link": reverse_lazy("admin:instituciones_aseguradora_changelist")},
                    {"title": "Preguntas de la encuesta", "icon": "quiz", "link": reverse_lazy("admin:encuestas_pregunta_changelist")},
                    {"title": "Términos de respuesta", "icon": "timer", "link": reverse_lazy("admin:pqrsf_reglaplazo_changelist")},
                    {"title": "Usuarios", "icon": "group", "link": reverse_lazy("admin:usuarios_usuario_changelist")},
                ],
            },
        ],
    },
}
