import json
import logging
import os
from typing import Dict, Any, Optional, List
from django.conf import settings
from pywebpush import webpush, WebPushException
from apps.notifications.models import PushSubscription, PushNotificationPreference

logger = logging.getLogger('apps.notifications')

# Clés VAPID par défaut pour la PWA AYYOU (surchargeables via variables d'environnement)
VAPID_PUBLIC_KEY = os.getenv(
    'VAPID_PUBLIC_KEY',
    'BEl62iUYgUivxIkv69yViEuiBIa1FDF3Vj8a6hD20f78W_2Rz96tqU3d-O1S_p-G98S9w0aB8b1112233445566'
)
VAPID_PRIVATE_KEY = os.getenv(
    'VAPID_PRIVATE_KEY',
    'x1y2z3a4b5c6d7e8f9g0h1i2j3k4l5m6n7o8p9q0r1s'
)
VAPID_ADMIN_EMAIL = os.getenv('VAPID_ADMIN_EMAIL', 'mailto:contact@ayyou.sn')


class WebPushService:
    """
    Service d'expédition de notifications Web Push PWA (VAPID) pour AYYOU.
    Interagit avec pywebpush pour transmettre les alertes aux navigateurs/mobiles enregistrés.
    """

    @classmethod
    def send_push_to_user(
        cls,
        utilisateur_id: int,
        titre: str,
        message: str,
        url: str = '/',
        category: str = 'GENERAL',
        data: Optional[Dict[str, Any]] = None
    ) -> int:
        """
        Envoie une notification Web Push à tous les appareils actifs enregistrés pour un utilisateur,
        en contrôlant ses préférences utilisateur [ON/OFF].
        """
        # Vérification des préférences utilisateur selon la catégorie
        pref, _ = PushNotificationPreference.objects.get_or_create(utilisateur_id=utilisateur_id)
        if category == 'PLANNING' and not pref.push_rappels_planning:
            logger.info(f"[WEB PUSH] Envoi ignoré : utilisateur #{utilisateur_id} a désactivé les Push Planning.")
            return 0
        if category == 'VIDEO' and not pref.push_publications_video:
            logger.info(f"[WEB PUSH] Envoi ignoré : utilisateur #{utilisateur_id} a désactivé les Push Vidéos.")
            return 0

        subscriptions = PushSubscription.objects.filter(utilisateur_id=utilisateur_id, is_active=True)
        if not subscriptions.exists():
            return 0

        payload = json.dumps({
            "title": titre,
            "body": message,
            "icon": "/assets/icons/icon-192x192.png",
            "badge": "/assets/icons/apple-touch-icon.png",
            "url": url,
            "data": data or {"url": url, "category": category}
        })

        sent_count = 0
        for sub in subscriptions:
            success = cls.send_to_subscription(sub, payload)
            if success:
                sent_count += 1

        return sent_count

    @classmethod
    def send_to_subscription(cls, subscription: PushSubscription, payload: str) -> bool:
        """
        Transmet le payload Web Push chiffré à un endpoint unique via pywebpush.
        Désactive l'abonnement en cas de réponse HTTP 404 / 410 (appareil/token expiré).
        """
        subscription_info = {
            "endpoint": subscription.endpoint,
            "keys": {
                "p256dh": subscription.p256dh,
                "auth": subscription.auth
            }
        }

        vapid_claims = {
            "sub": VAPID_ADMIN_EMAIL
        }

        try:
            webpush(
                subscription_info=subscription_info,
                data=payload,
                vapid_private_key=VAPID_PRIVATE_KEY,
                vapid_claims=vapid_claims,
                ttl=3600
            )
            logger.info(f"[WEB PUSH SUCCESS] Push envoyé avec succès à l'abonnement #{subscription.id}")
            return True
        except WebPushException as ex:
            logger.warning(f"[WEB PUSH ERROR] Échec d'envoi VAPID Push #{subscription.id}: {ex}")
            # Si le Push Server renvoie 404 ou 410, le token est expiré ou révoqué par le navigateur
            if ex.response and ex.response.status_code in (404, 410):
                subscription.is_active = False
                subscription.save(update_fields=['is_active', 'updated_at'])
                logger.info(f"[WEB PUSH CLEANUP] Abonnement obsolète #{subscription.id} marqué is_active=False")
            return False
        except Exception as e:
            logger.error(f"[WEB PUSH EXCEPTION] Exception inattendue Push #{subscription.id}: {e}")
            return False
