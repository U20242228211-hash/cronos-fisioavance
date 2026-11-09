"""Carga Fisioavance IPS con sus datos públicos y casos de ejemplo para mostrar Cronos.

Los datos de la institución (dirección, servicios, WhatsApp, horario) son los que publica en su página web.
Los pacientes, las PQRSF y las encuestas son FICTICIOS.

    python manage.py cargar_demo           # crea o actualiza
    python manage.py cargar_demo --borrar  # borra los casos de ejemplo y los vuelve a crear
"""

import random
from datetime import datetime, time, timedelta

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from encuestas.models import InvitacionEncuesta, Pregunta, RespuestaEncuesta, RespuestaItem
from encuestas.servicios import crear_preguntas_por_defecto
from instituciones.models import Aseguradora, Institucion, Profesional, Servicio
from pqrsf import plazos
from pqrsf.models import PQRSF, Actuacion, Consecutivo
from pqrsf.servicios import proponer_clasificacion, proponer_motivo
from usuarios.models import Usuario

CLAVE_DEMO = "Cronos-Demo-2026"

AVISO = (
    "Fisioavance IPS, como responsable del tratamiento, usará sus datos personales (nombre, documento, datos de "
    "contacto y la información de salud que incluya en su mensaje) solo para tramitar y responder su PQRSF, hacer "
    "seguimiento a la calidad de la atención y elaborar los reportes que exige la ley.\n\n"
    "La información sobre su salud es un dato sensible: no está obligado a darla. Puede conocer, actualizar, "
    "rectificar y suprimir sus datos, y revocar esta autorización, en la sede o escribiéndonos por WhatsApp al "
    "317 716 5551. (Ley 1581 de 2012 y Decreto 1377 de 2013.)"
)

SERVICIOS = ["Fisioterapia", "Fisiatría", "Fonoaudiología", "Terapia ocupacional", "Psicología", "Ortopedia y traumatología", "Tecarterapia"]
PROFESIONALES = [
    "Cristhian Iván Pérez Martínez", "Jefferson Perdomo Córdoba", "Jhon James Beltrán", "Lina Rocío Bolívar",
    "Manuel Camacho Puyo", "Mayra Alejandra Barbosa", "Xiomara Reyes Rosillo",
]

NOMBRES_F = ["María Fernanda", "Carmen Rosa", "Gloria Inés", "Paola Andrea", "Diana Marcela", "Luz Dary", "Yolanda", "Rubiela",
             "Sandra Milena", "Martha Lucía", "Ana Beatriz", "Claudia Patricia", "Johana Alejandra", "Nidia", "Blanca Nelly"]
NOMBRES_M = ["Luis Alberto", "Andrés Felipe", "Jhon Fredy", "Héctor", "Óscar Iván", "Camilo", "Sebastián", "Edwin",
             "Carlos Arturo", "Jorge Enrique", "William", "Fabián Andrés", "Álvaro", "Rodrigo", "Gustavo Adolfo"]
APELLIDOS = ["Ramírez Losada", "Perdomo Cerquera", "Trujillo Vargas", "Charry Polanía", "Cabrera Díaz", "Rojas Tovar",
             "Quintero Cuéllar", "Andrade Puentes", "Medina Castro", "Polanía Sánchez", "Ortiz Gutiérrez", "Vargas Silva",
             "Bonilla Cedeño", "Tamayo Lozano", "Castañeda Muñoz", "Gómez Falla", "Almario Torres", "Calderón Yate"]
ASEGURADORAS = ["Aseguradora Surcolombiana de Salud", "Protección Vital Seguros"]
NOMBRES_NINO = ["Santiago", "Mateo", "Samuel", "Valentina", "Isabella", "Juan José", "Sofía", "Emmanuel"]

# (tipo, servicio, descripción, condición especial, canal, anónima)
CASOS = [
    ("R", "Fisioterapia", "Me ordenaron 10 sesiones de fisioterapia para la rodilla y solo me han hecho 7. Ahora me dicen que no hay agenda hasta dentro de tres semanas.", "ninguna", "web", False),
    ("F", "Fisioterapia", "Quiero felicitar al equipo de fisioterapia. Llegué en muletas después de la cirugía y hoy camino sin ayuda.", "ninguna", "buzon", False),
    ("Q", "Fisioterapia", "La persona de recepción me contestó de mala manera cuando pregunté por qué me cambiaron la hora de la cita.", "ninguna", "web", False),
    ("P", "Fisiatría", "Necesito copia de la historia clínica de fisiatría para presentarla en la aseguradora.", "ninguna", "whatsapp", False),
    ("S", "Fisioterapia", "Sería bueno que enviaran un recordatorio de la cita por WhatsApp un día antes.", "ninguna", "tableta", False),
    ("R", "Terapia ocupacional", "Mi mamá tiene 78 años y la dejaron esperando más de una hora para su terapia, sentada en una silla dura.", "adulto_mayor", "web", False),
    ("F", "Fonoaudiología", "Muy agradecida con la terapia de lenguaje de mi hijo. Ya dice muchas palabras nuevas y va feliz a cada sesión.", "menor", "web", False),
    ("S", "Fisioterapia", "En la sala de espera faltan sillas en la mañana, muchos pacientes esperan de pie.", "ninguna", "buzon", True),
    ("Q", "Fisioterapia", "El baño de la sede estaba sin papel y sin jabón toda la mañana.", "ninguna", "buzon", True),
    ("P", "Fonoaudiología", "Quisiera saber si atienden los sábados en fonoaudiología para no faltar al trabajo.", "ninguna", "web", False),
    ("R", "Tecarterapia", "Después de la última sesión de tecarterapia quedé con mucho dolor en la espalda y nadie me ha llamado.", "ninguna", "whatsapp", False),
    ("F", "Psicología", "La psicóloga me ayudó mucho en un momento muy difícil. Gracias por la paciencia.", "ninguna", "tableta", False),
    ("Q", "Fisiatría", "La consulta de fisiatría empezó 40 minutos tarde y no nos avisaron.", "ninguna", "web", False),
    ("S", "Terapia ocupacional", "Podrían tener una rampa en la entrada para las personas en silla de ruedas.", "discapacidad", "buzon", False),
    ("P", "Fisioterapia", "Necesito un certificado de asistencia a las terapias para la empresa donde trabajo.", "ninguna", "web", False),
]
# Tres casos cerrados más, para que el historial de cinco meses se vea completo
CASOS_EXTRA = [
    ("P", "Ortopedia y traumatología", "Quisiera saber si la valoración de ortopedia necesita orden médica o si puedo pedir la cita directamente.", "ninguna", "whatsapp", False),
    ("R", "Psicología", "Me cancelaron dos citas seguidas de psicología sin avisarme y ya llevaba un mes esperando.", "ninguna", "web", False),
    ("S", "Fonoaudiología", "Sería bueno tener material para practicar en casa los ejercicios de lenguaje con los niños.", "menor", "buzon", False),
]
RESPUESTAS = {
    "R": ["Le ofrecemos disculpas. Revisamos su caso con la coordinación y ya quedó programada para continuar sus sesiones esta semana. Si necesita cambiar el horario, escríbanos al WhatsApp de la sede.",
          "Lamentamos lo ocurrido. Hablamos con el área asistencial, le reprogramamos las citas pendientes y dejamos una persona encargada de avisarle con anticipación cualquier cambio."],
    "Q": ["Gracias por contárnoslo. Hablamos con el equipo involucrado y reforzamos el protocolo de atención. Su caso nos ayuda a mejorar.",
          "Le pedimos disculpas. La situación se trató con el personal de la sede y quedó como compromiso de mejora en la próxima reunión de calidad."],
    "P": ["Su solicitud está lista. Puede reclamarla en la recepción de la sede presentando su documento, o se la enviamos por correo si así lo prefiere.",
          "Con gusto le informamos: la atención es de lunes a viernes en el horario publicado en la sede y en nuestro WhatsApp. Cualquier duda, escríbanos."],
    "S": ["Gracias por su sugerencia. La revisamos en el comité de calidad y la incluimos en el plan de mejora de este mes.",
          "Nos parece una muy buena idea. La llevamos a la dirección para evaluar cómo implementarla."],
    "F": ["¡Muchas gracias por sus palabras! Las compartimos con todo el equipo. Nos alegra mucho acompañarlo en su recuperación.",
          "Su mensaje nos motiva a seguir. Se lo hicimos llegar al profesional y a todo el equipo."],
}
COMENTARIOS_BUENOS = ["Excelente atención, muy amables.", "Los terapeutas son muy profesionales y pacientes.", "Me sentí muy bien atendido.",
                      "Todo muy organizado, siempre empiezan a la hora.", "Gracias por la paciencia con mi mamá.", "Ya camino mejor, gracias al equipo.",
                      "Las instalaciones son cómodas.", "", "", "", "", ""]
COMENTARIOS_MALOS = ["Me tocó esperar mucho para la sesión.", "La sede estaba muy llena y hacía calor.", "Me cambiaron la cita dos veces en la misma semana.",
                     "No me explicaron bien los ejercicios que debía hacer en casa."]


def _hace_dias_habiles(n, hora=10):
    dia = timezone.localdate()
    while n > 0:
        dia -= timedelta(days=1)
        if plazos.es_habil(dia):
            n -= 1
    return _bogota(dia, hora)


def _bogota(dia, hora, minuto=0):
    return timezone.make_aware(datetime.combine(dia, time(hora, minuto)))


class Command(BaseCommand):
    help = "Carga Fisioavance IPS con datos de ejemplo (pacientes, PQRSF y encuestas ficticios)."

    def add_arguments(self, parser):
        parser.add_argument("--borrar", action="store_true", help="Borra los casos de ejemplo antes de crearlos")

    @transaction.atomic
    def handle(self, *args, borrar=False, **opciones):
        azar = random.Random(2026)
        fisio, _ = Institucion.objects.update_or_create(
            slug="fisioavance",
            defaults={
                "nombre": "Fisioavance IPS",
                "prefijo_radicado": "FIS",
                "direccion": "Calle 16 # 7-55, barrio Quirinal",
                "municipio": "Neiva",
                "departamento": "Huila",
                "telefono": "317 716 5551",
                "whatsapp": "573177165551",
                "sitio_web": "https://www.fisioavanceips.com",
                "logo_url": "https://www.fisioavanceips.com/wp-content/uploads/2024/03/cropped-fisio-192x192.jpg",
                "color_primario": "#0E7490",
                "horario_atencion": "Lunes a viernes: 7:00 a. m. a 12:00 m. y 2:00 a 7:00 p. m.",
                "aviso_privacidad": AVISO,
                "advertencia_respuesta": (
                    "Si no está de acuerdo con esta respuesta, puede acudir a la Superintendencia Nacional de Salud "
                    "(www.supersalud.gov.co) o a la Secretaría de Salud Departamental del Huila."
                ),
            },
        )
        servicios = {}
        for orden, nombre in enumerate(SERVICIOS):
            servicios[nombre], _ = Servicio.objects.get_or_create(institucion=fisio, nombre=nombre, defaults={"orden": orden})
        for nombre in PROFESIONALES:
            Profesional.objects.get_or_create(institucion=fisio, nombre=nombre)
        for nombre in ASEGURADORAS:
            Aseguradora.objects.get_or_create(institucion=fisio, nombre=nombre)
        crear_preguntas_por_defecto(fisio)

        usuarios = {}
        for usuario, nombre, apellido, rol, cargo in [
            ("diana", "Diana", "", Usuario.Rol.GESTOR, "Administrativa · atención al usuario"),
            ("cristhian", "Cristhian Iván", "Pérez Martínez", Usuario.Rol.DIRECCION, "Representante legal"),
            ("recepcion", "Recepción", "Fisioavance", Usuario.Rol.RECEPCION, "Recepción"),
        ]:
            u, creado = Usuario.objects.get_or_create(username=usuario, defaults={"first_name": nombre, "last_name": apellido})
            u.institucion, u.rol, u.cargo, u.is_active = fisio, rol, cargo, True
            u.email = u.email or f"{usuario}@ejemplo.local"
            if creado:
                u.set_password(CLAVE_DEMO)
            u.save()
            usuarios[usuario] = u
        plataforma, creado = Usuario.objects.get_or_create(username="plataforma", defaults={"first_name": "Administrador", "last_name": "Cronos"})
        plataforma.rol, plataforma.is_superuser, plataforma.is_active = Usuario.Rol.PLATAFORMA, True, True
        if creado:
            plataforma.set_password(CLAVE_DEMO)
        plataforma.save()

        if borrar:
            RespuestaEncuesta.objects.filter(institucion=fisio).delete()
            InvitacionEncuesta.objects.filter(institucion=fisio).delete()
            Actuacion.objects.filter(pqrsf__institucion=fisio).delete()
            PQRSF.objects.filter(institucion=fisio).delete()
            Consecutivo.objects.filter(institucion=fisio).delete()
            Aseguradora.objects.filter(institucion=fisio).exclude(nombre__in=ASEGURADORAS).delete()
        if PQRSF.objects.filter(institucion=fisio).exists():
            self.stdout.write("Ya había casos de ejemplo; use --borrar para recrearlos.")
        else:
            self._pqrsf(fisio, servicios, usuarios, azar)
            self._encuestas(fisio, servicios, usuarios, azar)
        self.stdout.write(self.style.SUCCESS("Listo: Fisioavance IPS cargada. Usuarios y clave de prueba en el README."))

    # ------------------------------------------------------------------------------------------
    def _persona(self, azar):
        sexo = azar.choice(["F", "M"])
        usados = self.__dict__.setdefault("_usados", set())
        while True:  # que ninguna persona ni apellido se repita de más: así la demo parece de pacientes distintos
            nombres, apellidos = azar.choice(NOMBRES_F if sexo == "F" else NOMBRES_M), azar.choice(APELLIDOS)
            if apellidos not in usados or len(usados) >= len(APELLIDOS):
                usados.add(apellidos)
                break
        return {
            "tipo_documento": "CC",
            "numero_documento": str(azar.randint(12_000_000, 1_090_000_000)),
            "nombres": nombres,
            "apellidos": apellidos,
            "sexo": sexo,
            "telefono": f"3{azar.randint(100000000, 229999999)}",
            "municipio": azar.choice(["Neiva", "Neiva", "Neiva", "Palermo", "Rivera", "Campoalegre"]),
            "fecha_nacimiento": timezone.localdate() - timedelta(days=365 * azar.randint(19, 80) + azar.randint(0, 300)),
            "vinculacion": azar.choice(["particular", "particular", "aseguradora"]),
            "autoriza_datos": True,
            "medio_respuesta": "whatsapp",
        }

    def _actuacion(self, pqrsf, tipo, texto, fecha, usuario=None, anterior="", visible=False):
        Actuacion.objects.create(pqrsf=pqrsf, tipo=tipo, descripcion=texto, fecha=fecha, usuario=usuario,
                                 estado_anterior=anterior, estado_nuevo=pqrsf.estado, visible_paciente=visible)

    def _crear(self, fisio, servicios, caso, recibida, azar, aseguradora):
        tipo, servicio, texto, condicion, canal, anonima = caso
        datos = {} if anonima else self._persona(azar)
        if condicion == "menor" and not anonima:  # lo presenta un acudiente en nombre de un niño o niña
            datos["fecha_nacimiento"] = timezone.localdate() - timedelta(days=365 * azar.randint(28, 48))
            datos.update(es_acudiente=True, nombre_paciente=f"{azar.choice(NOMBRES_NINO)} {datos['apellidos']}",
                         paciente_tipo_documento="TI", paciente_numero_documento=str(azar.randint(1_080_000_000, 1_100_000_000)))
        if tipo in ("F", "Q", "R") and not anonima and servicio != "Psicología":
            datos["profesional"] = Profesional.objects.filter(institucion=fisio).exclude(nombre__startswith="Cristhian").order_by("?").first()
        pqrsf = PQRSF(
            institucion=fisio, tipo=tipo, servicio=servicios[servicio], descripcion=texto, condicion_especial=condicion,
            canal=canal, anonima=anonima, recibida_en=recibida, **datos,
        )
        if anonima:
            pqrsf.medio_respuesta = PQRSF.MedioRespuesta.AVISO
        if pqrsf.vinculacion == "aseguradora":
            pqrsf.aseguradora = aseguradora
        if pqrsf.autoriza_datos:
            pqrsf.autorizacion_en = recibida
        pqrsf.motivo = proponer_motivo(texto)
        pqrsf.clasificacion_propuesta = proponer_clasificacion(tipo, texto, condicion, pqrsf.es_nna, pqrsf.motivo)
        pqrsf.clasificacion = pqrsf.clasificacion_propuesta
        pqrsf.recalcular_vencimiento()
        pqrsf.save()
        self._actuacion(pqrsf, "radicacion", f"Se recibió por {pqrsf.get_canal_display().lower()}.", recibida, visible=True)
        return pqrsf

    def _pqrsf(self, fisio, servicios, usuarios, azar):
        diana, cristhian = usuarios["diana"], usuarios["cristhian"]
        aseguradora = Aseguradora.objects.filter(institucion=fisio).first()
        hoy = timezone.localdate()
        # Casos ya cerrados: unos 3 por mes en los últimos 5 meses (volumen real que contó Fisioavance)
        cerrados = CASOS[:12] + CASOS_EXTRA
        for i, caso in enumerate(cerrados):
            dias_atras = 148 - i * 9
            dia = hoy - timedelta(days=dias_atras)
            while not plazos.es_habil(dia):
                dia -= timedelta(days=1)
            recibida = _bogota(dia, azar.choice([8, 9, 10, 15, 16]), azar.choice([0, 15, 30, 45]))
            pqrsf = self._crear(fisio, servicios, caso, recibida, azar, aseguradora)
            clasificada = recibida + timedelta(hours=2)
            pqrsf.clasificacion_confirmada, pqrsf.estado, pqrsf.asignada_a = True, PQRSF.Estado.EN_TRAMITE, diana
            pqrsf.save()
            self._actuacion(pqrsf, "clasificacion", f"Clasificación confirmada: {pqrsf.get_clasificacion_display()}.", clasificada, diana, "radicada")
            total = (pqrsf.vence_en - recibida).total_seconds()
            tarde = i == 6  # un caso respondido fuera del término, para que el indicador sea real
            respondida = recibida + timedelta(seconds=total * (1.15 if tarde else azar.uniform(0.15, 0.7)))
            pqrsf.respuesta, pqrsf.respondida_en, pqrsf.respondida_por = azar.choice(RESPUESTAS[pqrsf.tipo]), respondida, diana
            pqrsf.estado = PQRSF.Estado.RESPONDIDA
            if pqrsf.anonima:
                pqrsf.aviso_desde = timezone.localdate(respondida)
                pqrsf.aviso_hasta = timezone.localdate(plazos.sumar_dias_habiles(respondida, 5))
            pqrsf.save()
            self._actuacion(pqrsf, "respuesta", "Se dio respuesta " + ("fuera del término." if tarde else "dentro del término."), respondida, diana, "en_tramite", True)
            if pqrsf.anonima:
                self._actuacion(pqrsf, "aviso", f"Respuesta publicada hasta el {pqrsf.aviso_hasta:%d/%m/%Y}.", respondida, diana, visible=True)
            else:
                pqrsf.comunicada_en = respondida + timedelta(minutes=10)
                pqrsf.save()
                self._actuacion(pqrsf, "comunicacion", "Respuesta enviada por WhatsApp.", pqrsf.comunicada_en, diana, visible=True)
            pqrsf.estado, pqrsf.cerrada_en = PQRSF.Estado.CERRADA, respondida + timedelta(days=1)
            pqrsf.save()
            self._actuacion(pqrsf, "cierre", "Caso cerrado.", pqrsf.cerrada_en, cristhian if i % 4 == 0 else diana, "respondida", True)

        # Casos abiertos hoy: uno en cada color del semáforo
        ahora = timezone.now()
        abiertos = [
            (("R", "Tecarterapia", "Me suspendieron la terapia porque dicen que la orden está vencida, pero el médico la renovó la semana pasada. Tengo mucho dolor.", "ninguna", "whatsapp", False), ahora - timedelta(hours=40), True),
            (("R", "Fisioterapia", "Llevo dos semanas esperando que me asignen las sesiones que faltan de mi tratamiento.", "ninguna", "web", False), ahora - timedelta(hours=80), True),
            (("Q", "Fisiatría", "El auxiliar de recepción fue grosero cuando pregunté por mi cita y no me quiso decir su nombre.", "ninguna", "web", False), _hace_dias_habiles(8), True),
            (("P", "Fisioterapia", "Necesito un certificado de las terapias que he recibido para mi incapacidad.", "ninguna", "tableta", False), ahora - timedelta(hours=20), False),
            (("S", "Terapia ocupacional", "Podrían tener una rampa en la entrada para las personas en silla de ruedas.", "discapacidad", "buzon", False), ahora - timedelta(hours=3), False),
            (("R", "Fisioterapia", "Mi hijo de 9 años tiene asma y hoy lo dejaron sin la sesión que le ordenaron porque no había profesional.", "menor", "web", False), ahora - timedelta(hours=2), False),
        ]
        for caso, recibida, confirmada in abiertos:
            pqrsf = self._crear(fisio, servicios, caso, recibida, azar, aseguradora)
            if confirmada:
                pqrsf.clasificacion_confirmada, pqrsf.estado, pqrsf.asignada_a = True, PQRSF.Estado.EN_TRAMITE, diana
                pqrsf.save()
                self._actuacion(pqrsf, "clasificacion", f"Clasificación confirmada: {pqrsf.get_clasificacion_display()}.", recibida + timedelta(hours=1), diana, "radicada")
                self._actuacion(pqrsf, "asignacion", "Responsable: Diana.", recibida + timedelta(hours=1), diana, visible=True)

    def _encuestas(self, fisio, servicios, usuarios, azar):
        preguntas = list(Pregunta.objects.filter(institucion=fisio).order_by("orden"))
        hoy = timezone.localdate()
        nombres_servicio = list(servicios)
        pesos = [40, 10, 14, 12, 8, 6, 10]
        for dias_atras in range(150, 0, -1):
            dia = hoy - timedelta(days=dias_atras)
            if dia.weekday() == 6:
                continue
            for _ in range(azar.choice([0, 1, 1, 1, 2, 2])):  # ~30 por mes, como contó Fisioavance
                servicio = servicios[azar.choices(nombres_servicio, weights=pesos)[0]]
                base = azar.choices([5, 4, 3, 2, 1], weights=[62, 25, 7, 4, 2])[0]
                momento = _bogota(dia, azar.randint(8, 18), azar.randint(0, 59))
                canal = azar.choice(["qr", "tableta", "invitacion", "invitacion"])
                invitacion = None
                if canal == "invitacion":
                    invitacion = InvitacionEncuesta.objects.create(
                        institucion=fisio, nombre_paciente=f"{azar.choice(NOMBRES_F + NOMBRES_M)} {azar.choice(APELLIDOS)}",
                        telefono=f"3{azar.randint(100000000, 229999999)}", servicio=servicio,
                        fin_tratamiento=dia, creada_por=usuarios["recepcion"], enviada_en=momento - timedelta(hours=3),
                    )
                mala = base <= 2
                respuesta = RespuestaEncuesta.objects.create(
                    institucion=fisio, invitacion=invitacion, servicio=servicio, canal=canal, respondida_en=momento,
                    comentario=azar.choice(COMENTARIOS_MALOS if mala else COMENTARIOS_BUENOS),
                    requiere_atencion=mala, atendida=mala and dias_atras > 20,
                )
                for p in preguntas:
                    if p.escala == Pregunta.Escala.RECOMENDACION:
                        valor = {5: 4, 4: azar.choice([4, 3]), 3: azar.choice([3, 2]), 2: 2, 1: 1}[base]
                    else:
                        valor = max(1, min(5, base + azar.choice([0, 0, 0, -1, 1])))
                    RespuestaItem.objects.create(respuesta=respuesta, pregunta=p, valor=valor)
        # Dos invitaciones enviadas que todavía no responden
        for nombre in ("Rosa Elvira Tovar Charry", "Fabián Andrés Cuéllar Rojas"):
            InvitacionEncuesta.objects.create(
                institucion=fisio, nombre_paciente=nombre, telefono=f"3{azar.randint(100000000, 229999999)}", servicio=servicios["Fisioterapia"],
                fin_tratamiento=hoy, creada_por=usuarios["recepcion"], enviada_en=timezone.now() - timedelta(hours=5),
            )
