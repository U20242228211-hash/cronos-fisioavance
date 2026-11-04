from django.urls import path

from . import views

app_name = "tablero"

urlpatterns = [
    path("reportes/", views.reportes, name="reportes"),
    path("carteles/", views.carteles, name="carteles"),
    path("avisos/", views.avisos, name="avisos"),
]
