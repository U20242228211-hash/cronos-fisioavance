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
- **SQLite** para probarlo sin instalar nada, **PostgreSQL** en desarrollo y en un servidor, y **MySQL** en un hosting
  compartido con cPanel (ver `DESPLIEGUE.md`).
- Festivos con la librería `holidays`; Excel con `openpyxl`; códigos QR con `qrcode`.
- WhatsApp por enlaces `wa.me`: no necesita la API paga de WhatsApp Business.

## Correrlo en un computador

Necesita **Python 3.12 o más nuevo**. No hay que instalar ninguna base de datos: por defecto usa SQLite, que es
un archivo (`db.sqlite3`) que se crea solo.

```bash
git clone https://github.com/U20242228211-hash/cronos-fisioavance.git
cd cronos-fisioavance
python3 -m venv .venv                # En Windows: python -m venv .venv
source .venv/bin/activate            # En Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
cp .env.example .env                 # En Windows: copy .env.example .env
python manage.py migrate
python manage.py cargar_demo         # Fisioavance con casos de ejemplo
python manage.py runserver
```

- Portal del paciente: <http://localhost:8000/fisioavance/>
- Panel del equipo: <http://localhost:8000/admin/>

Para usar PostgreSQL en vez de SQLite, cree la base `cronos` y cambie `DATABASE_URL` en el archivo `.env`
(por ejemplo `postgres://usuario:clave@localhost/cronos`).

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
| `python -m pytest` | Corre las pruebas: 33 casos del cálculo de términos y las de integración y de sistema |

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

Revisadas al 4 de noviembre de 2026.

| Regla | Fuente |
|---|---|
| Reclamos en salud por riesgo, en horas corridas desde la radicación: vital 24 h, priorizado 48 h, simple 72 h. Aplica también a las IPS | Circular Única de la Supersalud, Título VII, num. 3.3.2 (Circular Externa 2023151000000010-5 de 2023) |
| Riesgo vital de niños, niñas y adolescentes: máximo 8 horas | Supersalud, Circular Externa 2026151000000007-5 de 2026, instrucción 3ª |
| Una queja relacionada con la atención se trata como reclamo según su riesgo | Circular Única, num. 3.3: prevalece lo más favorable al usuario |
| Peticiones: 15 días hábiles; documentos o información: 10; copias: 3; consultas: 30 | Ley 1755 de 2015, art. 14; Circular Única, num. 3.3.2.4 |
| Campos mínimos del registro de cada PQRSF | Circular Única, Título VII, num. 3.3, literales a) a s) |
| Respuesta escrita por el medio que elija el usuario, con la advertencia de que puede acudir a la Supersalud | Circular Única, num. 3.3.1; Ley 1751 de 2015, art. 10 |
| Se reciben PQRSF anónimas; la respuesta se publica 5 días en el portal y en la cartelera | Ley 1755, art. 32; Sentencia C-951 de 2014; Ley 1437 de 2011, art. 69 (buena práctica para una IPS privada) |
| Indicadores de satisfacción global y de recomendación, reportados por trimestre en PISIS | Resolución 256 de 2016 y su parágrafo de reporte trimestral (vigente por la Resolución 1632 de 2025) |
| Autorización y aviso de privacidad; los datos de salud son sensibles y opcionales | Ley 1581 de 2012 y Decreto 1377 de 2013 |

Los términos viven en la tabla **Términos de respuesta**: si la norma cambia, se actualizan ahí sin tocar código, y
cada institución puede poner los suyos si son más estrictos.
