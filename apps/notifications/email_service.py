import logging
from typing import Optional
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.db import transaction

from .models import Notification

logger = logging.getLogger('apps.notifications')


class EmailNotificationService:
    """
    Service d'envoi d'emails transactionnels pour AYYOU.
    Reçoit un objet Notification (canal EMAIL), construit le contenu HTML et Texte,
    et expédie l'email via le service de messagerie Django (EmailMultiAlternatives).
    Découplé des modèles métier (commandes, livraisons, etc.).
    """

    DEFAULT_HTML_TEMPLATE = 'notifications/emails/base_notification.html'
    DEFAULT_TXT_TEMPLATE = 'notifications/emails/base_notification.txt'

    @classmethod
    def envoyer_email_notification(cls, notification: Notification) -> bool:
        """
        Envoie un email pour une notification donnée si son canal est EMAIL.
        Mets à jour le statut de la notification (STATUT_ENVOYEE ou STATUT_ECHEC).
        Retourne True si l'email a été envoyé avec succès, False sinon.
        Ne lève pas d'exception pour garantir la résilience du système.
        """
        if notification.canal != Notification.CANAL_EMAIL:
            logger.info(f"[EMAIL SERVICE] Ignoré: La notification #{notification.id} utilise le canal '{notification.canal}' (requis: '{Notification.CANAL_EMAIL}').")
            return False

        destinataire = notification.utilisateur
        recipient_email = getattr(destinataire, 'email', None)

        if not recipient_email or not str(recipient_email).strip():
            logger.warning(f"[EMAIL SERVICE] Échec: Adresse email manquante ou invalide pour le destinataire de la notification #{notification.id}.")
            notification.statut = Notification.STATUT_ECHEC
            notification.save(update_fields=['statut', 'updated_at'])
            return False

        destinataire_nom = destinataire.get_full_name() if hasattr(destinataire, 'get_full_name') else ''
        if not destinataire_nom or not destinataire_nom.strip():
            destinataire_nom = recipient_email

        context = {
            'titre': notification.titre,
            'message': notification.message,
            'reference_type': notification.reference_type,
            'reference_id': notification.reference_id,
            'destinataire_nom': destinataire_nom,
            'metadata': notification.metadata or {},
        }

        try:
            html_content = render_to_string(cls.DEFAULT_HTML_TEMPLATE, context)
            text_content = render_to_string(cls.DEFAULT_TXT_TEMPLATE, context)

            subject = notification.titre
            from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'AYYOU <no-reply@ayyou.com>')

            msg = EmailMultiAlternatives(
                subject=subject,
                body=text_content,
                from_email=from_email,
                to=[recipient_email]
            )
            msg.attach_alternative(html_content, "text/html")

            msg.send(fail_silently=False)

            notification.statut = Notification.STATUT_ENVOYEE
            notification.save(update_fields=['statut', 'updated_at'])

            logger.info(f"[EMAIL SERVICE] Email envoyé avec succès pour la notification #{notification.id} à {recipient_email}")
            return True

        except Exception as e:
            # Sécurité : aucun mot de passe SMTP, secret ou token n'est inscrit dans les logs
            logger.error(f"[EMAIL SERVICE] Erreur d'envoi pour notification #{notification.id}: {type(e).__name__} - {str(e)}")
            notification.statut = Notification.STATUT_ECHEC
            notification.save(update_fields=['statut', 'updated_at'])
            return False

    @classmethod
    def dispatch_email_on_commit(cls, notification: Notification) -> None:
        """
        Déclenche l'envoi d'email après le commit de la transaction SQL (transaction.on_commit).
        Si aucune transaction atomique n'est active, l'envoi s'exécute immédiatement.
        """
        if transaction.get_connection().in_atomic_block:
            transaction.on_commit(lambda: cls.envoyer_email_notification(notification))
        else:
            cls.envoyer_email_notification(notification)
