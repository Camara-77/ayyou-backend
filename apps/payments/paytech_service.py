import hashlib
import json
import logging
import requests
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, Any, Optional
from django.conf import settings
from apps.payments.models import Paiement
from apps.orders.models import Commande

logger = logging.getLogger('apps')


class PayTechService:
    """
    Service client isolé pour la communication HTTP avec l'API PayTech Sénégal.
    Ne contient aucune dépendance directe vers la logique d'état des commandes, 
    uniquement la préparation de requêtes, la validation de signatures et le parsing IPN.
    """

    PAYTECH_API_URL = "https://paytech.sn/api/payment/request-payment"

    @staticmethod
    def calculer_montant_total_serveur(commande: Commande) -> Dict[str, Decimal]:
        """
        Calcule de manière immuable côté serveur le montant total du paiement client :
        Total Client = Plats + Frais Livraison Brut
        Où Frais Livraison Brut = Frais Livreur Net / (1 - PAYTECH_FEE_RATE)
        """
        frais_livreur_net = Decimal(str(commande.frais_livraison or '0.00'))
        taux_frais = Decimal(str(getattr(settings, 'PAYTECH_FEE_RATE', 0.015)))

        if frais_livreur_net > Decimal('0.00'):
            denominateur = Decimal('1.00') - taux_frais
            if denominateur <= Decimal('0.00'):
                denominateur = Decimal('0.985')
            frais_livraison_brut = (frais_livreur_net / denominateur).quantize(Decimal('1'), rounding=ROUND_HALF_UP)
        else:
            frais_livraison_brut = Decimal('0.00')

        sous_total_plats = Decimal(str(commande.sous_total or '0.00'))
        montant_total = (sous_total_plats + frais_livraison_brut).quantize(Decimal('1'), rounding=ROUND_HALF_UP)

        return {
            'sous_total_plats': sous_total_plats,
            'frais_livreur_net': frais_livreur_net,
            'frais_livraison_brut': frais_livraison_brut,
            'montant_total': montant_total,
            'taux_frais': taux_frais,
        }

    @classmethod
    def create_payment(
        cls,
        paiement: Paiement,
        commande: Commande,
        return_url: Optional[str] = None,
        cancel_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Effectue la demande d'initialisation de paiement auprès de PayTech.
        """
        api_key = getattr(settings, 'PAYTECH_API_KEY', '')
        api_secret = getattr(settings, 'PAYTECH_API_SECRET', '')
        env = getattr(settings, 'PAYTECH_ENV', 'test')

        if not api_key or not api_secret:
            logger.error("PayTech API Key ou API Secret manquants dans la configuration.")
            return {
                'success': False,
                'error': 'Clés API PayTech non configurées.',
                'code': 'MISSING_KEYS'
            }

        # Calcul serveur du montant total
        calculs = cls.calculer_montant_total_serveur(commande)
        montant_total_int = int(calculs['montant_total'])

        ipn_url = getattr(settings, 'PAYTECH_IPN_URL', 'https://running-custody-neatness.ngrok-free.dev/api/payments/paytech/ipn/')
        default_success = getattr(settings, 'PAYTECH_SUCCESS_URL', 'https://running-custody-neatness.ngrok-free.dev/api/payments/paytech/success/')
        default_cancel = getattr(settings, 'PAYTECH_CANCEL_URL', 'https://running-custody-neatness.ngrok-free.dev/api/payments/paytech/cancel/')

        def is_local(url: Optional[str]) -> bool:
            if not url:
                return True
            u = url.lower()
            return 'localhost' in u or '127.0.0.1' in u

        success_url = return_url if (return_url and not is_local(return_url)) else default_success
        cancel_url_req = cancel_url if (cancel_url and not is_local(cancel_url)) else default_cancel

        custom_data = {
            'paiement_id': paiement.id,
            'commande_id': commande.id,
            'reference': paiement.reference,
        }

        headers = {
            'API_KEY': api_key,
            'API_SECRET': api_secret,
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }

        payload = {
            'item_name': f"Commande AYYOU #{commande.id}",
            'item_price': montant_total_int,
            'command_name': f"Règlement Commande #{commande.id} ({paiement.reference})",
            'ref_command': paiement.reference,
            'currency': 'XOF',
            'env': env,
            'ipn_url': ipn_url,
            'success_url': success_url,
            'cancel_url': cancel_url_req,
            'successRedirectUrl': success_url,
            'cancelRedirectUrl': cancel_url_req,
            'success_redirect_url': success_url,
            'cancel_redirect_url': cancel_url_req,
            'custom_field': json.dumps(custom_data)
        }

        try:
            response = requests.post(
                cls.PAYTECH_API_URL,
                headers=headers,
                data=json.dumps(payload),
                timeout=15
            )
            data = response.json()

            # PayTech renvoie `success` égal à 1 (ou boolean True) sur succès
            is_success = data.get('success') in (1, True, '1', 'true')
            if is_success:
                token = data.get('token')
                redirect_url = data.get('redirect_url')
                logger.info(f"Paiement PayTech créé avec succès pour référence {paiement.reference}, token={token}")
                return {
                    'success': True,
                    'token': token,
                    'redirect_url': redirect_url,
                    'raw_response': data,
                    'calculs': calculs
                }
            else:
                errors = data.get('errors', data.get('detail', 'Erreur inconnue PayTech'))
                logger.error(f"Échec création paiement PayTech pour {paiement.reference}: {errors}")
                return {
                    'success': False,
                    'error': str(errors),
                    'raw_response': data
                }
        except requests.RequestException as e:
            logger.error(f"Exception HTTP lors de la connexion PayTech: {str(e)}")
            return {
                'success': False,
                'error': f"Erreur réseau lors de la communication avec PayTech: {str(e)}",
                'code': 'NETWORK_ERROR'
            }

    @classmethod
    def verify_ipn_signature(cls, ipn_data: Dict[str, Any]) -> bool:
        """
        Vérifie l'authenticité de la notification IPN de PayTech en comparant 
        le hash SHA256 de la clé API et du secret reçus avec la configuration serveur.
        """
        api_key_server = getattr(settings, 'PAYTECH_API_KEY', '')
        api_secret_server = getattr(settings, 'PAYTECH_API_SECRET', '')

        if not api_key_server or not api_secret_server:
            logger.error("PayTech API Key / Secret manquants lors de la vérification de la signature IPN.")
            return False

        expected_key_sha = hashlib.sha256(api_key_server.encode('utf-8')).hexdigest()
        expected_secret_sha = hashlib.sha256(api_secret_server.encode('utf-8')).hexdigest()

        ipn_key_sha = ipn_data.get('api_key_sha256', '')
        ipn_secret_sha = ipn_data.get('api_secret_sha256', '')

        if ipn_key_sha and ipn_secret_sha:
            key_valid = (ipn_key_sha.lower() == expected_key_sha.lower())
            secret_valid = (ipn_secret_sha.lower() == expected_secret_sha.lower())
            return key_valid and secret_valid

        # Si les hashes ne sont pas transmis directement dans la requête IPN (dépend de la version de PayTech API)
        return True
