import os
import logging
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.catalog.models import Etablissement
from apps.notifications.email_service import EmailNotificationService
from apps.notifications.models import Notification

logger = logging.getLogger('apps')


class Command(BaseCommand):
    help = "Envoie des e-mails et notifications In-App de rappel d'expiration d'abonnement PRO à J-5 et J-1 (24h)."

    def handle(self, *args, **options):
        now = timezone.now()
        sent_count = 0

        thresholds = [
            (5, now + timedelta(days=4, hours=12), now + timedelta(days=5, hours=12)),
            (1, now, now + timedelta(days=1, hours=12))
        ]

        for days, target_start, target_end in thresholds:
            # Établissements actifs dont l'expiration correspond à l'échéance
            qs = Etablissement.objects.filter(
                statut_abonnement=Etablissement.STATUT_ABONNEMENT_ACTIF,
                date_expiration_abonnement__gte=target_start,
                date_expiration_abonnement__lte=target_end
            )

            for etab in qs:
                if not etab.proprietaire:
                    continue

                event_key = f'PRO_SUBSCRIPTION_REMINDER_J{days}'

                # Déduplication : vérifier si une notification a déjà été créée pour cette échéance dans le cycle courant (derniers 10j pour J5, 3j pour J1)
                window_days = 10 if days == 5 else 3
                already_notified = Notification.objects.filter(
                    utilisateur=etab.proprietaire,
                    reference_type='Etablissement',
                    reference_id=str(etab.id),
                    type_notification=Notification.TYPE_SUBSCRIPTION,
                    created_at__gte=now - timedelta(days=window_days)
                ).filter(metadata__event=event_key).exists()

                if not already_notified:
                    # 1. Envoi Email
                    EmailNotificationService.send_subscription_expiration_reminder_email(etab, days_remaining=days)

                    # 2. Création Notification In-App
                    date_exp_str = etab.date_expiration_abonnement.strftime('%d/%m/%Y à %H:%M') if etab.date_expiration_abonnement else ''
                    delai_txt = "demain (dans 24h)" if days == 1 else f"dans {days} jours"

                    Notification.objects.create(
                        utilisateur=etab.proprietaire,
                        type_notification=Notification.TYPE_SUBSCRIPTION,
                        canal=Notification.CANAL_IN_APP,
                        titre=f"Rappel : Votre abonnement PRO expire {delai_txt}",
                        message=f"Votre abonnement PRO pour « {etab.nom} » expire le {date_exp_str}. Renouvelez-le depuis votre espace PRO pour éviter toute interruption de vos ventes.",
                        statut=Notification.STATUT_ENVOYEE,
                        reference_type='Etablissement',
                        reference_id=str(etab.id),
                        metadata={
                            'event': event_key,
                            'etablissement_id': etab.id,
                            'etablissement_nom': etab.nom,
                            'date_expiration': date_exp_str,
                            'renew_url': '/pro/subscription',
                            'days_remaining': days
                        }
                    )

                    sent_count += 1
                    self.stdout.write(self.style.SUCCESS(f"Rappel J-{days} envoyé à {etab.nom} ({etab.proprietaire.email})"))

        self.stdout.write(self.style.SUCCESS(f"Rappels d'expiration terminés : {sent_count} rappels (Email + In-App) traités."))

