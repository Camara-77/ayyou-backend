import os
import json
import logging
import urllib.request
import urllib.error
from typing import Dict, Any, Optional

from apps.catalog.models import Etablissement
from apps.users.models import ProfilLivreur

logger = logging.getLogger('apps.notifications')


class N8nNotificationService:
    """
    Service d'intégration Django -> n8n pour les événements d'automatisation (ex: PRO_ACCOUNT_APPROVED).
    Expédie des requêtes HTTP POST JSON vers un webhook n8n configuré de manière sécurisée via l'environnement.
    Source de vérité = Django DB. Les erreurs d'envoi n8n ne doivent jamais annuler les transactions Django.
    """

    EVENT_PRO_ACCOUNT_APPROVED = 'PRO_ACCOUNT_APPROVED'
    EVENT_PRO_ACCOUNT_REJECTED = 'PRO_ACCOUNT_REJECTED'

    @classmethod
    def get_webhook_url(cls) -> str:
        """
        Récupère l'URL du webhook n8n depuis les variables d'environnement.
        """
        return os.getenv('N8N_PRO_APPROVAL_WEBHOOK_URL', '').strip()

    @classmethod
    def get_webhook_secret(cls) -> str:
        """
        Récupère le secret du webhook n8n depuis les variables d'environnement.
        """
        return os.getenv('N8N_WEBHOOK_SECRET', '').strip()

    @classmethod
    def envoyer_evenement(cls, event: str, payload: Dict[str, Any]) -> bool:
        """
        Envoie un payload JSON au Webhook n8n via une requête HTTP POST.
        Sécurisé par le header 'X-Webhook-Secret'.
        Ne lève jamais d'exception afin de garantir la résilience de la validation Django DB.
        """
        webhook_url = cls.get_webhook_url()
        if not webhook_url:
            logger.info(f"[N8N SERVICE] N8N_PRO_APPROVAL_WEBHOOK_URL non configuré. Événement '{event}' non transmis à n8n.")
            return False

        secret = cls.get_webhook_secret()

        headers = {
            'Content-Type': 'application/json; charset=utf-8',
            'User-Agent': 'AYYOU-Django-Backend/1.0',
        }
        if secret:
            headers['X-Webhook-Secret'] = secret

        data_bytes = json.dumps(payload, ensure_ascii=False).encode('utf-8')

        req = urllib.request.Request(
            url=webhook_url,
            data=data_bytes,
            headers=headers,
            method='POST'
        )

        user_id = payload.get('user_id')
        pro_type = payload.get('type')

        try:
            # Timeout raisonnable de 10 secondes
            with urllib.request.urlopen(req, timeout=10) as response:
                status_code = response.getcode()
                logger.info(f"[N8N SERVICE] N8N {event} event sent successfully for user_id={user_id} (type={pro_type}, HTTP {status_code})")
                return True
        except urllib.error.HTTPError as e:
            logger.error(f"[N8N SERVICE] N8N {event} event failed for user_id={user_id} (type={pro_type}): HTTP {e.code} - {e.reason}")
            return False
        except Exception as e:
            # Sécurité: Ne jamais loguer le secret ou l'URL complète si elle contient des credentials
            logger.error(f"[N8N SERVICE] N8N {event} event failed for user_id={user_id} (type={pro_type}): {type(e).__name__} - {str(e)}")
            return False

    @classmethod
    def send_pro_approval_for_etablissement(cls, etablissement: Etablissement) -> bool:
        """
        Construit le payload et déclenche la notification n8n pour un Etablissement (RESTAURANT ou VENDEUR).
        """
        proprietaire = etablissement.proprietaire
        user_id = proprietaire.id if proprietaire else 0
        email = proprietaire.email if proprietaire else ''
        phone = (proprietaire.numero_telephone if (proprietaire and proprietaire.numero_telephone) else etablissement.telephone) or ''

        frontend_base = os.getenv('FRONTEND_URL', 'http://localhost:4200').rstrip('/')
        if etablissement.type_etablissement == Etablissement.TYPE_VENDEUR:
            login_url = f"{frontend_base}/vendeur/login"
        else:
            login_url = f"{frontend_base}/pro/login"

        payload = {
            "event": cls.EVENT_PRO_ACCOUNT_APPROVED,
            "type": etablissement.type_etablissement,  # RESTAURANT ou VENDEUR
            "user_id": user_id,
            "name": etablissement.nom,
            "email": email,
            "phone": phone,
            "login_url": login_url
        }

        return cls.envoyer_evenement(cls.EVENT_PRO_ACCOUNT_APPROVED, payload)

    @classmethod
    def send_pro_approval_for_driver(cls, driver: ProfilLivreur) -> bool:
        """
        Construit le payload et déclenche la notification n8n pour un ProfilLivreur (LIVREUR).
        """
        utilisateur = driver.utilisateur
        name = utilisateur.get_full_name() or utilisateur.email

        frontend_base = os.getenv('FRONTEND_URL', 'http://localhost:4200').rstrip('/')
        login_url = f"{frontend_base}/delivery/login"

        payload = {
            "event": cls.EVENT_PRO_ACCOUNT_APPROVED,
            "type": "LIVREUR",
            "user_id": utilisateur.id,
            "name": name,
            "email": utilisateur.email or '',
            "phone": utilisateur.numero_telephone or '',
            "login_url": login_url
        }

        return cls.envoyer_evenement(cls.EVENT_PRO_ACCOUNT_APPROVED, payload)

    @classmethod
    def send_pro_rejection_for_etablissement(cls, etablissement: Etablissement, motif: str) -> bool:
        """
        Construit le payload et déclenche la notification n8n de refus pour un Etablissement (RESTAURANT ou VENDEUR).
        """
        proprietaire = etablissement.proprietaire
        user_id = proprietaire.id if proprietaire else 0
        email = proprietaire.email if proprietaire else ''
        phone = (proprietaire.numero_telephone if (proprietaire and proprietaire.numero_telephone) else etablissement.telephone) or ''

        payload = {
            "event": cls.EVENT_PRO_ACCOUNT_REJECTED,
            "type": etablissement.type_etablissement,  # RESTAURANT ou VENDEUR
            "user_id": user_id,
            "name": etablissement.nom,
            "email": email,
            "phone": phone,
            "motif": motif or 'Dossier non conforme'
        }

        return cls.envoyer_evenement(cls.EVENT_PRO_ACCOUNT_REJECTED, payload)

    @classmethod
    def send_pro_rejection_for_driver(cls, driver: ProfilLivreur, motif: str) -> bool:
        """
        Construit le payload et déclenche la notification n8n de refus pour un ProfilLivreur (LIVREUR).
        """
        utilisateur = driver.utilisateur
        name = utilisateur.get_full_name() or utilisateur.email

        payload = {
            "event": cls.EVENT_PRO_ACCOUNT_REJECTED,
            "type": "LIVREUR",
            "user_id": utilisateur.id,
            "name": name,
            "email": utilisateur.email or '',
            "phone": utilisateur.numero_telephone or '',
            "motif": motif or 'Dossier non conforme'
        }

        return cls.envoyer_evenement(cls.EVENT_PRO_ACCOUNT_REJECTED, payload)
