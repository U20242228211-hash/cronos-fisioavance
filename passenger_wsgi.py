"""Punto de entrada para hosting compartido con cPanel («Setup Python App», Phusion Passenger).

En cPanel: Application root = la carpeta de Cronos, Application startup file = passenger_wsgi.py,
Application Entry point = application. Ver DESPLIEGUE.md.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

from config.wsgi import application  # noqa: E402,F401
