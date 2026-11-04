"""Banco de 30 casos del cálculo de términos (objetivo específico 5 del proyecto).

Los resultados esperados se calcularon a mano con el calendario de festivos de Colombia de 2026 y 2027:
noviembre de 2026 tiene festivos el lunes 2 y el lunes 16; diciembre, el martes 8 y el viernes 25; enero de
2027, el viernes 1 y el lunes 11; y en Semana Santa de 2026, el jueves 2 y el viernes 3 de abril.
"""

from datetime import timedelta

import pytest
from django.utils import timezone

from pqrsf import plazos
from pqrsf.models import PQRSF, ReglaPlazo

from .conftest import bogota

H, D = plazos.HORAS, plazos.DIAS_HABILES


def fin_del_dia(anio, mes, dia):
    return bogota(anio, mes, dia, 23, 59, 59)


CASOS_VENCIMIENTO = [
    # (caso, recibida, cantidad, unidad, vence esperado)
    ("01 petición 15 días con festivo en medio", bogota(2026, 11, 9, 10, 0), 15, D, fin_del_dia(2026, 12, 1)),
    ("02 información 10 días desde un viernes antes de festivo", bogota(2026, 10, 30, 16, 0), 10, D, fin_del_dia(2026, 11, 17)),
    ("03 consulta 30 días con dos festivos", bogota(2026, 11, 3, 9, 0), 30, D, fin_del_dia(2026, 12, 17)),
    ("04 radicada un sábado", bogota(2026, 11, 7, 10, 0), 15, D, fin_del_dia(2026, 11, 30)),
    ("05 radicada un domingo", bogota(2026, 11, 8, 18, 0), 15, D, fin_del_dia(2026, 11, 30)),
    ("06 radicada en un festivo", bogota(2026, 11, 16, 8, 0), 15, D, fin_del_dia(2026, 12, 7)),
    ("07 radicada tarde en la noche", bogota(2026, 11, 10, 23, 30), 15, D, fin_del_dia(2026, 12, 2)),
    ("08 queja que cruza el año", bogota(2026, 12, 15, 11, 0), 15, D, fin_del_dia(2027, 1, 7)),
    ("09 información en Semana Santa", bogota(2026, 3, 30, 8, 0), 10, D, fin_del_dia(2026, 4, 15)),
    ("10 un día hábil desde un viernes antes de puente", bogota(2026, 11, 13, 15, 0), 1, D, fin_del_dia(2026, 11, 17)),
    ("11 cinco días hábiles del aviso", bogota(2026, 11, 4, 9, 0), 5, D, fin_del_dia(2026, 11, 11)),
    ("12 sugerencia del 31 de diciembre", bogota(2026, 12, 31, 10, 0), 15, D, fin_del_dia(2027, 1, 25)),
    ("13 riesgo vital 24 h", bogota(2026, 11, 4, 10, 0), 24, H, bogota(2026, 11, 5, 10, 0)),
    ("14 riesgo vital 24 h un sábado en la noche", bogota(2026, 11, 7, 22, 15), 24, H, bogota(2026, 11, 8, 22, 15)),
    ("15 priorizado 48 h que cae en domingo", bogota(2026, 11, 13, 17, 0), 48, H, bogota(2026, 11, 15, 17, 0)),
    ("16 simple 72 h sobre un festivo", bogota(2026, 11, 14, 9, 30), 72, H, bogota(2026, 11, 17, 9, 30)),
    ("17 priorizado 48 h que cambia de mes", bogota(2026, 11, 30, 20, 0), 48, H, bogota(2026, 12, 2, 20, 0)),
    ("18 simple 72 h que cambia de año", bogota(2026, 12, 30, 12, 0), 72, H, bogota(2027, 1, 2, 12, 0)),
    ("19 riesgo vital radicado en Navidad", bogota(2026, 12, 25, 8, 0), 24, H, bogota(2026, 12, 26, 8, 0)),
]


@pytest.mark.parametrize("caso,recibida,cantidad,unidad,esperado", CASOS_VENCIMIENTO, ids=[c[0] for c in CASOS_VENCIMIENTO])
def test_vencimiento(caso, recibida, cantidad, unidad, esperado):
    assert plazos.calcular_vencimiento(recibida, cantidad, unidad) == esperado


CASOS_SEMAFORO = [
    ("20 justo a la mitad", 24, "amarillo"),
    ("21 un poco antes de la mitad", 23.9, "verde"),
    ("22 al 80 %", 38.4, "rojo"),
    ("23 al 100 %", 48, "vencida"),
    ("24 ya vencida", 72, "vencida"),
    ("25 recién radicada", 0, "verde"),
]


@pytest.mark.parametrize("caso,horas,esperado", CASOS_SEMAFORO, ids=[c[0] for c in CASOS_SEMAFORO])
def test_semaforo(caso, horas, esperado):
    inicio = bogota(2026, 11, 4, 8, 0)
    vence = inicio + timedelta(hours=48)
    assert plazos.semaforo(plazos.porcentaje_transcurrido(inicio, vence, inicio + timedelta(hours=horas))) == esperado


@pytest.mark.parametrize(
    "caso,inicio,fin,esperado",
    [
        ("26 de viernes a martes con festivo", bogota(2026, 11, 13, 10, 0), bogota(2026, 11, 17, 9, 0), 1),
        ("27 el mismo día", bogota(2026, 11, 4, 8, 0), bogota(2026, 11, 4, 17, 0), 0),
        ("28 una semana corriente", bogota(2026, 11, 3, 8, 0), bogota(2026, 11, 10, 8, 0), 5),
    ],
)
def test_dias_habiles_entre(caso, inicio, fin, esperado):
    assert plazos.dias_habiles_entre(inicio, fin) == esperado


@pytest.mark.django_db
def test_29_la_pqrsf_usa_la_regla_de_la_norma(institucion, servicio):
    pqrsf = PQRSF(institucion=institucion, tipo="R", clasificacion="vital", servicio=servicio, descripcion="x",
                  medio_respuesta="whatsapp", recibida_en=bogota(2026, 11, 4, 10, 0))
    pqrsf.recalcular_vencimiento()
    assert pqrsf.vence_en == bogota(2026, 11, 5, 10, 0)


@pytest.mark.django_db
def test_30_la_regla_propia_de_la_institucion_gana(institucion, servicio):
    ReglaPlazo.objects.create(institucion=institucion, tipo="P", clasificacion="general", cantidad=10, unidad=D, norma="Política interna")
    pqrsf = PQRSF(institucion=institucion, tipo="P", clasificacion="general", servicio=servicio, descripcion="x",
                  medio_respuesta="whatsapp", recibida_en=bogota(2026, 11, 9, 10, 0))
    pqrsf.recalcular_vencimiento()
    assert pqrsf.vence_en == fin_del_dia(2026, 11, 24)
    assert timezone.localtime(pqrsf.vence_en).date().isoformat() == "2026-11-24"
