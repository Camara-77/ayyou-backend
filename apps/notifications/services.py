import logging
from typing import Optional, Dict, Any
from django.db import models
from django.utils import timezone
from apps.users.models import Utilisateur
from .models import Notification

logger = logging.getLogger('apps.notifications')


class NotificationService:
    """
    Service métier centralisé pour la gestion des notifications AYYOU.
    Responsable de la création, consultation, statistiques et marquage de lecture des notifications.
    """

    @staticmethod
    def creer_notification(
        utilisateur: Utilisateur,
        titre: str,
        message: str,
        type_notification: str = Notification.TYPE_SYSTEM,
        canal: str = Notification.CANAL_IN_APP,
        reference_type: str = '',
        reference_id: str = '',
        metadata: Optional[Dict[str, Any]] = None,
        statut: str = Notification.STATUT_ENVOYEE
    ) -> Notification:
        """
        Crée et enregistre une notification pour un utilisateur donné.
        """
        if metadata is None:
            metadata = {}

        notification = Notification.objects.create(
            utilisateur=utilisateur,
            titre=titre,
            message=message,
            type_notification=type_notification,
            canal=canal,
            reference_type=reference_type,
            reference_id=str(reference_id),
            metadata=metadata,
            statut=statut
        )
        logger.info(f"[NOTIFICATION SERVICE] Notification #{notification.id} créée pour {utilisateur.email} (Type: {type_notification}, Canal: {canal})")
        return notification

    @staticmethod
    def get_notifications_utilisateur(utilisateur: Utilisateur) -> models.QuerySet:
        """
        Retourne la liste complète des notifications appartenant à un utilisateur connecté.
        """
        return Notification.objects.filter(utilisateur=utilisateur)

    @staticmethod
    def get_nombre_non_lues(utilisateur: Utilisateur) -> int:
        """
        Retourne le nombre total de notifications non lues pour un utilisateur.
        """
        return Notification.objects.filter(utilisateur=utilisateur, est_lu=False).count()

    @staticmethod
    def marquer_comme_lue(notification_id: int, utilisateur: Utilisateur) -> Optional[Notification]:
        """
        Marque une notification spécifique comme lue en garantissant l'isolation utilisateur.
        Retourne None si la notification n'existe pas ou n'appartient pas à l'utilisateur.
        """
        try:
            notification = Notification.objects.get(id=notification_id, utilisateur=utilisateur)
            notification.marquer_comme_lu()
            return notification
        except Notification.DoesNotExist:
            return None

    @staticmethod
    def marquer_tout_comme_lu(utilisateur: Utilisateur) -> int:
        """
        Marque toutes les notifications non lues d'un utilisateur comme lues.
        Retourne le nombre de notifications mises à jour.
        """
        non_lues = Notification.objects.filter(utilisateur=utilisateur, est_lu=False)
        count = non_lues.count()
        if count > 0:
            now = timezone.now()
            non_lues.update(
                est_lu=True,
                statut=Notification.STATUT_LU,
                date_lecture=now,
                updated_at=now
            )
        return count

    @classmethod
    def traiter_rappels_repas_planifies(cls, utilisateur: Optional[Utilisateur] = None) -> int:
        """
        Scanne les repas planifiés actifs (statut='PLANIFIE') et génère de manière idempotente
        les notifications de rappel In-App T-30 min, T-20 min et T-5 min.
        """
        from apps.orders.models import RepasPlanifie
        import datetime

        now = timezone.now()
        today = now.date()

        qs = RepasPlanifie.objects.filter(
            statut=RepasPlanifie.STATUT_PLANIFIE,
            date_planifiee__gte=today - datetime.timedelta(days=1),
            date_planifiee__lte=today + datetime.timedelta(days=1)
        ).select_related('utilisateur', 'produit', 'etablissement')

        if utilisateur:
            qs = qs.filter(utilisateur=utilisateur)

        notifs_creees = 0

        for meal in qs:
            if meal.heure_planifiee:
                meal_time = meal.heure_planifiee
            else:
                if meal.creneau == RepasPlanifie.CRENEAU_MATIN:
                    meal_time = datetime.time(8, 0)
                elif meal.creneau == RepasPlanifie.CRENEAU_SOIR:
                    meal_time = datetime.time(19, 30)
                elif meal.creneau == RepasPlanifie.CRENEAU_EN_CAS:
                    meal_time = datetime.time(16, 0)
                else:
                    meal_time = datetime.time(12, 30)

            dt_naive = datetime.datetime.combine(meal.date_planifiee, meal_time)

            if timezone.is_naive(dt_naive):
                meal_dt = timezone.make_aware(dt_naive, timezone.get_current_timezone())
            else:
                meal_dt = dt_naive

            if now > meal_dt + datetime.timedelta(minutes=30):
                continue

            heure_formatee = meal_time.strftime('%H:%M')
            prod_name = meal.produit.nom if meal.produit else "votre plat"
            resto_name = meal.etablissement.nom if meal.etablissement else "le restaurant"

            reminders_config = [
                {
                    'key': 'T-30',
                    'trigger_dt': meal_dt - datetime.timedelta(minutes=30),
                    'message': f"Votre repas '{prod_name}' de chez {resto_name} est prévu dans 30 minutes (à {heure_formatee})."
                },
                {
                    'key': 'T-20',
                    'trigger_dt': meal_dt - datetime.timedelta(minutes=20),
                    'message': f"Votre repas '{prod_name}' est prévu dans 20 minutes (à {heure_formatee})."
                },
                {
                    'key': 'T-5',
                    'trigger_dt': meal_dt - datetime.timedelta(minutes=5),
                    'message': f"Votre repas '{prod_name}' est prévu dans 5 minutes (à {heure_formatee})."
                },
            ]

            for rem in reminders_config:
                trigger_dt = rem['trigger_dt']

                if now >= trigger_dt and now <= meal_dt + datetime.timedelta(minutes=30):
                    already_sent = Notification.objects.filter(
                        utilisateur=meal.utilisateur,
                        type_notification=Notification.TYPE_RAPPEL_REPAS_PLANIFIE,
                        reference_type='RepasPlanifie',
                        reference_id=str(meal.id),
                        metadata__reminder_type=rem['key']
                    ).exists()

                    if not already_sent:
                        cls.creer_notification(
                            utilisateur=meal.utilisateur,
                            titre="Repas planifié",
                            message=rem['message'],
                            type_notification=Notification.TYPE_RAPPEL_REPAS_PLANIFIE,
                            canal=Notification.CANAL_IN_APP,
                            reference_type='RepasPlanifie',
                            reference_id=str(meal.id),
                            metadata={
                                'planning_id': meal.id,
                                'reminder_type': rem['key'],
                                'date_planifiee': str(meal.date_planifiee),
                                'heure_planifiee': heure_formatee
                            }
                        )
                        notifs_creees += 1

                        # Expédition Web Push PWA complémentaire (avec vérification des préférences & Deep Link)
                        try:
                            from apps.notifications.webpush_service import WebPushService
                            WebPushService.send_push_to_user(
                                utilisateur_id=meal.utilisateur_id,
                                titre="Repas planifié AYYOU",
                                message=rem['message'],
                                url=f"/planning/detail/{meal.id}",
                                category="PLANNING",
                                data={
                                    "url": f"/planning/detail/{meal.id}",
                                    "planning_id": meal.id,
                                    "reminder_type": rem['key']
                                }
                            )
                        except Exception as push_err:
                            logger.warning(f"[PUSH ERROR] Échec Push Rappel Planning #{meal.id}: {push_err}")

        return notifs_creees
