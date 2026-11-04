from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

admin.site.site_header = "Cronos"
admin.site.site_title = "Cronos"
admin.site.index_title = "Tablero"

urlpatterns = [
    path("admin/", admin.site.urls),
    path("panel/", include("tablero.urls")),
    path("", include("portal.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
