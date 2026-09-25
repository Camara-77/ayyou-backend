from django.core.management.base import BaseCommand
from apps.deliveries.services import DeliveryService


class Command(BaseCommand):
    help = "Vérifie et libère automatiquement les livraisons attribuées dont le délai d'acceptation de 2 minutes a expiré."

    def handle(self, *args, **options):
        count = DeliveryService.expire_expired_deliveries()
        self.stdout.write(
            self.style.SUCCESS(f"[AYYOU EXPIRATION] {count} livraison(s) attribuée(s) expirée(s) et remise(s) en attente avec succès.")
        )
