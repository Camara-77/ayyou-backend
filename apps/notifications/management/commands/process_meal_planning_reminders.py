from django.core.management.base import BaseCommand
from apps.notifications.services import NotificationService


class Command(BaseCommand):
    help = 'Scanne les repas planifiés et génère les notifications de rappel (T-30, T-20, T-5 min).'

    def handle(self, *args, **options):
        count = NotificationService.traiter_rappels_repas_planifies()
        self.stdout.write(
            self.style.SUCCESS(f"Traitement terminé : {count} notification(s) de rappel de repas planifié créée(s).")
        )
