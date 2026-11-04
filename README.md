# Cronos

Sistema web para gestionar las **PQRSF** (peticiones, quejas, reclamos, sugerencias y felicitaciones) y las
**encuestas de satisfacción** de instituciones prestadoras de salud. Controla los términos que fija la norma,
guarda un histórico que no se puede borrar y calcula los indicadores de satisfacción de la Resolución 256 de 2016.

Primera institución: **Fisioavance IPS** (Neiva, Huila). Proyecto final de Ingeniería de Software · Universidad
Surcolombiana · 2026-2 · José Manuel Garzón Durán, Angela Sofía Rupay Aros, Pedro Antonio Silva Tovar y Valeria
Vargas Artunduaga.

## Qué hace

| Para el paciente (sin crear cuenta) | Para el equipo de la IPS |
|---|---|
| Radicar una PQRSF en 3 pasos desde el celular, el QR de la sede o la tableta de recepción | Bandeja con semáforo de términos: a tiempo, pasó la mitad, por vencer, vencida |
| Recibir constancia con número de radicado y fecha límite de respuesta | Confirmar la clasificación de riesgo que propone el sistema |
| Consultar el estado con el radicado y su documento | Responder y enviar la respuesta por WhatsApp o correo con un clic |
| Responder la encuesta de 5 preguntas con caritas | Alertas al 50 % y al 80 % del término y escalamiento a la dirección |
| Ver los avisos de las respuestas a PQRSF anónimas | Tablero, reportes por mes y descargas en Excel |
| | Carteles con QR para imprimir y avisos para la cartelera |

**Multiinstitución:** cada IPS tiene su portal (`/fisioavance/`), sus usuarios, sus servicios, su logo y sus datos,
y nunca ve los de otra. Una IPS nueva se crea con un comando.

## Tecnología

- **Python 3.13 y Django 6.1**, con **Unfold** para el panel del equipo.
- **PostgreSQL** en desarrollo. En un hosting compartido con cPanel también funciona con **MySQL** (ver `DESPLIEGUE.md`).
- Festivos con la librería `holidays`; Excel con `openpyxl`; códigos QR con `qrcode`.
- WhatsApp por enlaces `wa.me`: no necesita la API paga de WhatsApp Business.

## Correrlo en un computador

```bash
git clone https://github.com/U20242228211-hash/cronos-fisioavance.git
cd cronos-fisioavance
python3 -m venv .venv
source .venv/bin/activate            # En Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
cp .env.example .env                 # ajuste DATABASE_URL si su PostgreSQL pide usuario y clave
createdb cronos                      # o créela desde pgAdmin
python manage.py migrate
python manage.py cargar_demo         # Fisioavance con casos de ejemplo
python manage.py runserver
```

- Portal del paciente: <http://localhost:8000/fisioavance/>
- Panel del equipo: <http://localhost:8000/admin/>

### Usuarios de prueba (solo para el computador de desarrollo)

Los crea `cargar_demo`. Todos tienen la clave **`Cronos-Demo-2026`**. Cámbiela antes de usar Cronos con datos reales.

| Usuario | Rol | Qué puede hacer |
|---|---|---|
| `diana` | Atención al usuario | Gestionar y responder PQRSF, encuestas, reportes |
| `cristhian` | Dirección (representante legal) | Todo lo anterior, más usuarios, términos propios y datos de la institución |
| `recepcion` | Recepción | Registrar lo del buzón y enviar invitaciones a la encuesta |
| `plataforma` | Administrador de la plataforma | Todas las instituciones |

Los pacientes, las PQRSF y las encuestas de `cargar_demo` son **ficticios**. Los datos de Fisioavance (dirección,
servicios, WhatsApp, horario, logo) son los que publica en su sitio web, que autorizó usar.

## Comandos

| Comando | Para qué |
|---|---|
| `python manage.py cargar_demo [--borrar]` | Carga (o recarga) Fisioavance con casos de ejemplo |
| `python manage.py crear_institucion "Nombre" --slug nombre --usuario usuario --correo correo` | Da de alta otra IPS con sus preguntas y su usuario de dirección |
| `python manage.py revisar_vencimientos` | Manda las alertas del 50 % y 80 % y escala lo vencido. En el servidor se programa cada hora |
| `python -m pytest` | Corre las pruebas: 30 casos del cálculo de términos y las de integración y de sistema |

## Cómo está organizado

```
config/         configuración (todo lo sensible sale de .env)
instituciones/  IPS, servicios, profesionales, aseguradoras y la base de permisos por institución y rol
usuarios/       usuarios del equipo con su rol
pqrsf/          el caso, sus términos (plazos.py), sus acciones (servicios.py) y su histórico inmutable
encuestas/      preguntas, invitaciones, respuestas e indicadores de la Resolución 256 de 2016
portal/         lo que ve el paciente
tablero/        tablero, reportes, descargas en Excel, carteles con QR y avisos
tests/          pruebas unitarias, de integración y de sistema
```

## Normas que aplica

| Regla | Fuente |
|---|---|
| Términos por riesgo de los reclamos en salud: vital 24 h, priorizado 48 h, simple 72 h | Supersalud, Circular Externa 2023151000000010-5 de 2023 |
| Peticiones: 15 días hábiles; documentos o información: 10; consultas: 30 | Ley 1755 de 2015, art. 14 |
| Respuesta por aviso cuando no hay datos del peticionario | Ley 1437 de 2011, art. 69 |
| Indicadores de satisfacción global y de recomendación | Resolución 256 de 2016 del Ministerio de Salud |
| Autorización y aviso de privacidad; los datos de salud son sensibles | Ley 1581 de 2012 y Decreto 1377 de 2013 |

Los términos viven en la tabla **Términos de respuesta**: si la norma cambia, se actualizan ahí sin tocar código, y
cada institución puede poner los suyos si son más estrictos.
