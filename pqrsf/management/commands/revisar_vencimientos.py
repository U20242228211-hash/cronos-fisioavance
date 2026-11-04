"""Genera las alertas del 50 % y el 80 % del término y escala lo vencido. Se programa cada hora (cron)."""

from django.core.management.base import BaseCommand

from pqrsf.servicios import revisar_vencimientos


class Command(BaseCommand):
    help = "Revisa los términos de las PQRSF abiertas, manda alertas y escala las vencidas."

    def handle(self, *args, **opciones):
        resumen = revisar_vencimientos()
        self.stdout.write(
            f"Alertas al 50 %: {resumen['alerta_50']} · al 80 %: {resumen['alerta_80']} · escaladas: {resumen['escaladas']}"
        )
