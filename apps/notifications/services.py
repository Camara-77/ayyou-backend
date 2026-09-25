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
