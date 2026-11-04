"""Pruebas de integración y de sistema: el paciente radica, el equipo gestiona, el paciente consulta."""

from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone

from encuestas import indicadores
from encuestas.models import InvitacionEncuesta, Pregunta, RespuestaEncuesta
from encuestas.servicios import registrar_respuesta
from pqrsf import servicios
from pqrsf.models import PQRSF, Actuacion

from .conftest import CLAVE

pytestmark = pytest.mark.django_db


def url(nombre, institucion, **kwargs):
    return reverse(f"portal:{nombre}", kwargs={"slug": institucion.slug, **kwargs})


# --- Integración: portal del paciente --------------------------------------------------------------
def test_radicar_crea_el_caso_con_radicado_termino_e_historico(client, institucion, datos_paciente):
    respuesta = client.post(url("radicar", institucion), datos_paciente)
    pqrsf = PQRSF.objects.get()
    assert respuesta.status_code == 302 and pqrsf.token in respuesta.url
    assert pqrsf.radicado == f"IPS-{timezone.localdate().year}-00001"
    assert pqrsf.clasificacion_propuesta == "priorizado"  # «me suspendieron» es una de las señales de prioridad
    assert pqrsf.vence_en == pqrsf.recibida_en + timedelta(hours=48)
    assert pqrsf.autorizacion_en is not None and pqrsf.telefono == "3001112233"
    assert pqrsf.actuaciones.get().tipo == Actuacion.Tipo.RADICACION
    assert pqrsf.motivo == "acceso"  # tema principal propuesto: «me suspendieron»


def test_sin_autorizacion_de_datos_no_se_radica(client, institucion, datos_paciente):
    datos_paciente.pop("autoriza_datos")
    respuesta = client.post(url("radicar", institucion), datos_paciente)
    assert respuesta.status_code == 200 and not PQRSF.objects.exists()
    assert "necesitamos su autorización" in respuesta.content.decode()


def test_responder_por_whatsapp_exige_celular(client, institucion, datos_paciente):
    datos_paciente["telefono"] = ""
    respuesta = client.post(url("radicar", institucion), datos_paciente)
    assert "necesitamos su celular" in respuesta.content.decode() and not PQRSF.objects.exists()


def test_anonima_borra_los_datos_y_se_responde_por_aviso(client, institucion, datos_paciente, gestor):
    datos_paciente.update({"tipo": "Q", "anonima": "on", "autoriza_datos": ""})
    client.post(url("radicar", institucion), datos_paciente)
    pqrsf = PQRSF.objects.get()
    assert pqrsf.anonima and pqrsf.nombres == "" and pqrsf.numero_documento == ""
    assert pqrsf.medio_respuesta == PQRSF.MedioRespuesta.AVISO
    servicios.responder(pqrsf, "Ya se arregló el baño.", gestor)
    assert pqrsf.aviso_desde == timezone.localdate() and pqrsf.aviso_hasta > pqrsf.aviso_desde
    assert pqrsf in client.get(url("avisos", institucion)).context["avisos"]


def test_consultar_con_radicado_y_documento(client, institucion, datos_paciente):
    client.post(url("radicar", institucion), datos_paciente)
    pqrsf = PQRSF.objects.get()
    bien = client.post(url("consulta", institucion), {"radicado": pqrsf.radicado.lower(), "documento": "1075123456"})
    assert bien.status_code == 302 and pqrsf.token in bien.url
    mal = client.post(url("consulta", institucion), {"radicado": pqrsf.radicado, "documento": "999"})
    assert mal.status_code == 200 and "No encontramos" in mal.content.decode()


# --- Unidad: reglas de negocio ----------------------------------------------------------------------
@pytest.mark.parametrize(
    "tipo,texto,condicion,esperado",
    [
        ("R", "El paciente se desmayó en la sesión", "ninguna", "vital"),
        ("R", "Tengo mucho dolor y nadie me llama", "ninguna", "priorizado"),
        ("R", "No me han dado la cita de control", "adulto_mayor", "priorizado"),
        ("R", "No me han dado la cita de control", "ninguna", "simple"),
        ("P", "Necesito copia de mi historia clínica", "ninguna", "copias"),
        ("P", "Necesito un certificado de asistencia", "ninguna", "informacion"),
        ("R", "Mi hija se desmayó en la terapia", "menor", "vital_nna"),
        ("R", "Mi hijo tiene asma y no tuvo su sesión", "menor", "vital_nna"),
        ("Q", "Tengo mucho dolor y nadie me llama", "ninguna", "priorizado"),
        ("Q", "Pongan papel en el baño", "ninguna", "general"),
        ("P", "Quisiera saber si atienden los sábados", "ninguna", "consulta"),
        ("S", "Pongan más sillas", "ninguna", "general"),
    ],
)
def test_clasificacion_propuesta(tipo, texto, condicion, esperado):
    assert servicios.proponer_clasificacion(tipo, texto, condicion) == esperado


def test_el_historico_no_se_puede_modificar(institucion, servicio):
    pqrsf = servicios.radicar(PQRSF(institucion=institucion, tipo="S", servicio=servicio, descripcion="x", medio_respuesta="whatsapp", telefono="3001112233"))
    actuacion = pqrsf.actuaciones.get()
    actuacion.descripcion = "cambiada"
    with pytest.raises(ValueError):
        actuacion.save()
    with pytest.raises(ValueError):
        actuacion.delete()


def test_el_radicado_es_consecutivo_por_institucion(institucion, otra_institucion, servicio):
    a = servicios.radicar(PQRSF(institucion=institucion, tipo="S", servicio=servicio, descripcion="x", medio_respuesta="whatsapp"))
    b = servicios.radicar(PQRSF(institucion=institucion, tipo="F", servicio=servicio, descripcion="y", medio_respuesta="whatsapp"))
    c = servicios.radicar(PQRSF(institucion=otra_institucion, tipo="S", descripcion="z", medio_respuesta="whatsapp"))
    anio = timezone.localdate().year
    assert (a.radicado, b.radicado, c.radicado) == (f"IPS-{anio}-00001", f"IPS-{anio}-00002", f"OTR-{anio}-00001")


def test_alertas_y_escalamiento(institucion, servicio, direccion):
    pqrsf = servicios.radicar(PQRSF(institucion=institucion, tipo="R", clasificacion="vital", servicio=servicio, descripcion="x", medio_respuesta="whatsapp"))
    inicio = pqrsf.recibida_en
    assert servicios.revisar_vencimientos(inicio + timedelta(hours=13))["alerta_50"] == 1
    assert servicios.revisar_vencimientos(inicio + timedelta(hours=20))["alerta_80"] == 1
    assert servicios.revisar_vencimientos(inicio + timedelta(hours=25))["escaladas"] == 1
    assert servicios.revisar_vencimientos(inicio + timedelta(hours=30)) == {"alerta_50": 0, "alerta_80": 0, "escaladas": 0}
    assert pqrsf.actuaciones.filter(tipo=Actuacion.Tipo.ESCALAMIENTO).count() == 1


def test_indicadores_de_la_resolucion_256(institucion):
    preguntas = list(Pregunta.objects.filter(institucion=institucion).order_by("orden"))
    satisfaccion, recomendacion = preguntas[0], preguntas[-1]
    for global_, recomienda in [(5, 4), (4, 3), (2, 1)]:
        valores = {p.id: 4 for p in preguntas}
        valores[satisfaccion.id], valores[recomendacion.id] = global_, recomienda
        registrar_respuesta(institucion, valores)
    datos = indicadores.calcular(institucion)
    assert datos["satisfaccion"] == 66.7 and datos["recomendacion"] == 66.7
    assert (datos["satisfaccion_numerador"], datos["satisfaccion_denominador"]) == (2, 3)
    assert RespuestaEncuesta.objects.filter(requiere_atencion=True).count() == 1


def test_encuesta_por_invitacion_solo_se_responde_una_vez(client, institucion, servicio):
    invitacion = InvitacionEncuesta.objects.create(institucion=institucion, nombre_paciente="Luis Pérez", telefono="3001112233", servicio=servicio)
    preguntas = Pregunta.objects.filter(institucion=institucion)
    datos = {f"p{p.id}": "5" if p.escala == "caritas" else "4" for p in preguntas}
    enlace = url("encuesta_invitacion", institucion, token=invitacion.token)
    assert client.post(enlace, datos).status_code == 200
    invitacion.refresh_from_db()
    assert invitacion.respondida
    assert client.get(enlace).context["ya_respondida"]


# --- Seguridad: cada institución solo ve lo suyo -----------------------------------------------------
def test_una_institucion_no_ve_las_pqrsf_de_otra(client, institucion, servicio, gestor_otra):
    pqrsf = servicios.radicar(PQRSF(institucion=institucion, tipo="Q", servicio=servicio, descripcion="secreto", medio_respuesta="whatsapp"))
    client.login(username="gestor_otra", password=CLAVE)
    lista = client.get(reverse("admin:pqrsf_pqrsf_changelist"))
    assert lista.status_code == 200 and pqrsf.radicado not in lista.content.decode()
    detalle = client.get(reverse("admin:pqrsf_pqrsf_change", args=[pqrsf.pk]))
    assert detalle.status_code in (302, 404)


def test_recepcion_registra_pero_no_lee_la_bandeja(client, recepcion):
    client.login(username="recepcion", password=CLAVE)
    assert client.get(reverse("admin:pqrsf_pqrsf_add")).status_code == 200
    assert client.get(reverse("admin:pqrsf_pqrsf_changelist")).status_code == 403


# --- Sistema: el caso completo de punta a punta ------------------------------------------------------
def test_caso_completo(client, institucion, datos_paciente, gestor):
    client.post(url("radicar", institucion), datos_paciente)
    pqrsf = PQRSF.objects.get()

    client.login(username="gestor", password=CLAVE)
    cambio = reverse("admin:pqrsf_pqrsf_change", args=[pqrsf.pk])
    pagina = client.get(cambio)
    assert pagina.status_code == 200
    formulario = {"clasificacion": "simple", "motivo": "acceso", "regimen": "no_aplica", "asignada_a": gestor.pk,
                  "respuesta": "Ya le reprogramamos las sesiones.", "accion_realizada": "Se reprogramaron 3 sesiones.",
                  "nota_interna": "Se llamó a la paciente.", "actuaciones-TOTAL_FORMS": "1", "actuaciones-INITIAL_FORMS": "1",
                  "actuaciones-MIN_NUM_FORMS": "0", "actuaciones-MAX_NUM_FORMS": "0", "actuaciones-0-id": pqrsf.actuaciones.get().pk,
                  "actuaciones-0-pqrsf": pqrsf.pk, "_continue": "1"}
    assert client.post(cambio, formulario).status_code == 302
    pqrsf.refresh_from_db()
    assert pqrsf.estado == PQRSF.Estado.RESPONDIDA and pqrsf.clasificacion_confirmada and pqrsf.respondida_a_tiempo
    tipos = list(pqrsf.actuaciones.values_list("tipo", flat=True))
    assert tipos == ["radicacion", "clasificacion", "asignacion", "respuesta", "nota"]

    enviar = client.get(reverse("admin:pqrsf_pqrsf_enviar_whatsapp", args=[pqrsf.pk]))
    assert enviar.status_code == 302 and enviar.url.startswith("https://wa.me/573001112233?text=")
    client.get(reverse("admin:pqrsf_pqrsf_cerrar_caso", args=[pqrsf.pk]))
    pqrsf.refresh_from_db()
    assert pqrsf.estado == PQRSF.Estado.CERRADA and pqrsf.comunicada_en

    client.logout()
    estado = client.get(url("estado", institucion, token=pqrsf.token))
    contenido = estado.content.decode()
    assert "Ya le reprogramamos las sesiones." in contenido and "Se llamó a la paciente." not in contenido
    assert "Superintendencia Nacional de Salud" in contenido  # advertencia obligatoria (num. 3.3.1)


def test_tablero_y_reportes(client, institucion, gestor, datos_paciente):
    client.post(url("radicar", institucion), datos_paciente)
    client.login(username="gestor", password=CLAVE)
    assert client.get(reverse("admin:index")).status_code == 200
    assert client.get(reverse("tablero:reportes")).status_code == 200
    for tipo in ("pqrsf", "encuestas", "indicadores", "res256"):
        excel = client.get(reverse("tablero:reportes"), {"descargar": tipo})
        assert excel.status_code == 200 and excel["Content-Type"].startswith("application/vnd.openxmlformats")
    assert client.get(reverse("portal:qr", kwargs={"slug": institucion.slug, "destino": "pqrsf"}))["Content-Type"] == "image/svg+xml"
