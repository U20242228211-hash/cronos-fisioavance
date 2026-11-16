#!/bin/bash
# Instala Cronos en una cuenta gratis de PythonAnywhere. Se corre en una consola Bash de PythonAnywhere:
#   git clone --depth 1 https://github.com/U20242228211-hash/cronos-fisioavance.git && bash cronos-fisioavance/despliegue/pythonanywhere.sh
# Se puede volver a correr sin dañar nada: conserva la clave, la base de datos y los datos que ya haya.
set -e
cd "$(dirname "$0")/.."
CARPETA="$(pwd)"
USUARIO="$(whoami)"
DOMINIO="$USUARIO.pythonanywhere.com"
WSGI="/var/www/${USUARIO//./_}_pythonanywhere_com_wsgi.py"

PY=""
for v in 3.13 3.12; do
  if command -v "python$v" >/dev/null 2>&1; then PY="python$v"; break; fi
done
if [ -z "$PY" ]; then
  echo "❌ Esta cuenta no tiene Python 3.12 ni 3.13 (Cronos usa Django 6, que los necesita)."
  exit 1
fi
echo "▶ Usando $PY"

if [ ! -d .venv ]; then "$PY" -m venv .venv; fi
. .venv/bin/activate
echo "▶ Instalando las librerías (tarda unos minutos)…"
pip install -q --no-cache-dir --upgrade pip
pip install -q --no-cache-dir -r requirements.txt

if [ ! -f .env ]; then
  cat > .env <<ENV
DJANGO_SECRET_KEY=$(python -c 'import secrets; print(secrets.token_urlsafe(50))')
DJANGO_DEBUG=0
DJANGO_ALLOWED_HOSTS=$DOMINIO
DJANGO_CSRF_TRUSTED_ORIGINS=https://$DOMINIO
DATABASE_URL=sqlite:///$CARPETA/db.sqlite3
CRONOS_INSTITUCION_POR_DEFECTO=fisioavance
ENV
  echo "▶ Archivo .env creado"
fi
# Es una demo con datos ficticios: mostrar usuarios y clave de prueba (quitar la línea CRONOS_DEMO=1 del .env para ocultarlos)
grep -q "^CRONOS_DEMO=" .env || echo "CRONOS_DEMO=1" >> .env

echo "▶ Base de datos y datos de ejemplo…"
python manage.py migrate --noinput -v 0
python manage.py cargar_demo
python manage.py collectstatic --noinput -v 0

if [ -f "$WSGI" ]; then
  cat > "$WSGI" <<PYW
# Cronos en PythonAnywhere (lo escribió despliegue/pythonanywhere.sh)
import os
import sys

ruta = "$CARPETA"
if ruta not in sys.path:
    sys.path.insert(0, ruta)
os.chdir(ruta)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

from django.core.wsgi import get_wsgi_application  # noqa: E402

application = get_wsgi_application()
PYW
  echo "▶ Archivo WSGI listo: $WSGI"
else
  echo "⚠️  Todavía no existe la aplicación web. Créala en la pestaña Web y vuelve a correr:"
  echo "    bash $CARPETA/despliegue/pythonanywhere.sh"
fi

echo
echo "✅ Instalado. En la pestaña Web pon:"
echo "   Virtualenv:     $CARPETA/.venv"
echo "   Static files:   URL /static/   →   Directory $CARPETA/staticfiles"
echo "   Force HTTPS:    Enabled"
echo "Luego toca Reload y abre https://$DOMINIO/fisioavance/"
