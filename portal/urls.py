from django.urls import path

from . import views

app_name = "portal"

urlpatterns = [
    path("", views.raiz, name="raiz"),
    path("<slug:slug>/", views.inicio, name="inicio"),
    path("<slug:slug>/pqrsf/", views.radicar, name="radicar"),
    path("<slug:slug>/pqrsf/constancia/<str:token>/", views.constancia, name="constancia"),
    path("<slug:slug>/consulta/", views.consulta, name="consulta"),
    path("<slug:slug>/consulta/<str:token>/", views.estado, name="estado"),
    path("<slug:slug>/encuesta/", views.encuesta, name="encuesta"),
    path("<slug:slug>/encuesta/<str:token>/", views.encuesta, name="encuesta_invitacion"),
    path("<slug:slug>/avisos/", views.avisos, name="avisos"),
    path("<slug:slug>/qr/<str:destino>.svg", views.codigo_qr, name="qr"),
]
