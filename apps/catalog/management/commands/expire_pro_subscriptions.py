import logging
from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.catalog.models import Etablissement
from apps.notifications.email_service import EmailNotificationService
from apps.notifications.models import Notification

logger = logging.getLogger('apps')


class Command(BaseCommand):
    help = "Vérifie les abonnements PRO expirés et fait passer leur statut à EXPIRE (Zéro délai de grâce) + envoie les alertes de suspension."

    def handle(self, *args, **options):
        now = timezone.now()
        expired_qs = Etablissement.objects.filter(
            statut_abonnement=Etablissement.STATUT_ABONNEMENT_ACTIF,
            date_expiration_abonnement__lt=now
        )
        count = 0
        for etab in expired_qs:
            etab.statut_abonnement = Etablissement.STATUT_ABONNEMENT_EXPIRE
            etab.save(update_fields=['statut_abonnement'])
            count += 1
            self.stdout.write(self.style.WARNING(f"Abonnement expiré pour Etablissement #{etab.id} ({etab.nom})"))

            if etab.proprietaire:
                # 1. Envoi Email de suspension
                EmailNotificationService.send_subscription_suspension_email(etab)

                # 2. Création Notification In-App de suspension
                Notification.objects.create(
                    utilisateur=etab.proprietaire,
                    type_notification=Notification.TYPE_SUBSCRIPTION,
                    canal=Notification.CANAL_IN_APP,
                    titre=f"Abonnement PRO expiré — {etab.nom}",
                    message=f"Votre abonnement PRO pour « {etab.nom} » a expiré. Votre établissement, vos produits et vos vidéos ne sont plus visibles. Réactivez-le pour restaurer vos ventes.",
                    statut=Notification.STATUT_ENVOYEE,
                    reference_type='Etablissement',
                    reference_id=str(etab.id),
                    metadata={
                        'event': 'PRO_SUBSCRIPTION_SUSPENDED',
                        'etablissement_id': etab.id,
                        'etablissement_nom': etab.nom,
                        'renew_url': '/pro/subscription'
                    }
                )

        self.stdout.write(self.style.SUCCESS(f"Traitement terminé : {count} abonnements basculés au statut EXPIRE et notifiés."))

