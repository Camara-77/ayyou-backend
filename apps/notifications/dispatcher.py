import logging
from typing import Dict, Any, Optional
from apps.users.models import Utilisateur
from .models import Notification
from .services import NotificationService
from .email_service import EmailNotificationService

logger = logging.getLogger('apps.notifications')


class NotificationDispatcher:
    """
    Dispatcher centralisé des événements AYYOU vers les canaux appropriés (In-App, Email, WhatsApp).
    Orchestre la création de la notification et son acheminement vers le service du canal sélectionné.
    """

    @staticmethod
    def dispatch_event(
        event_type: str,
        destinataire: Utilisateur,
        titre: str,
        message: str,
        canal: str = Notification.CANAL_IN_APP,
        reference_type: str = '',
        reference_id: str = '',
        metadata: Optional[Dict[str, Any]] = None
    ) -> Notification:
        """
        Reçoit un événement métadonnées, crée la notification et l'expédie selon le canal de diffusion.
        """
        logger.info(f"[NOTIFICATION DISPATCHER] Événement '{event_type}' (Canal: {canal}) vers {destinataire.email}")

        # Pour les emails, statut initial en attente avant traitement par le service Email
        statut_initial = Notification.STATUT_EN_ATTENTE if canal == Notification.CANAL_EMAIL else Notification.STATUT_ENVOYEE

        notification = NotificationService.creer_notification(
            utilisateur=destinataire,
            titre=titre,
            message=message,
            type_notification=event_type,
            canal=canal,
            reference_type=reference_type,
            reference_id=reference_id,
            metadata=metadata,
            statut=statut_initial
        )

        # Routage vers le service Email si le canal est EMAIL
        if canal == Notification.CANAL_EMAIL:
            EmailNotificationService.dispatch_email_on_commit(notification)

        return notification

