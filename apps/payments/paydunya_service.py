import logging
import json
from decimal import Decimal
from django.conf import settings
from apps.payments.models import Paiement
from apps.orders.models import Commande

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    import urllib.request
    import urllib.error
    HAS_REQUESTS = False

logger = logging.getLogger('apps')


class PaydunyaService:
    """
    Service client d'intégration de la passerelle de paiement PayDunya (Sandbox & Production).
    """

    @classmethod
    def get_base_url(cls) -> str:
        mode = getattr(settings, 'PAYDUNYA_MODE', 'test').lower()
        if mode == 'live':
            return 'https://app.paydunya.com/api/v1'
        return 'https://app.paydunya.com/sandbox-api/v1'

    @classmethod
    def get_checkout_base_url(cls) -> str:
        mode = getattr(settings, 'PAYDUNYA_MODE', 'test').lower()
        if mode == 'live':
            return 'https://app.paydunya.com/checkout/invoice'
        return 'https://app.paydunya.com/sandbox-checkout/invoice'

    @classmethod
    def get_headers(cls) -> dict:
        return {
            'PAYDUNYA-MASTER-KEY': getattr(settings, 'PAYDUNYA_MASTER_KEY', ''),
            'PAYDUNYA-PRIVATE-KEY': getattr(settings, 'PAYDUNYA_PRIVATE_KEY', ''),
            'PAYDUNYA-TOKEN': getattr(settings, 'PAYDUNYA_TOKEN', ''),
            'Content-Type': 'application/json',
        }

    @classmethod
    def _http_post(cls, url: str, payload: dict, headers: dict, timeout: int = 10) -> tuple[int, dict]:
        if HAS_REQUESTS:
            response = requests.post(url, json=payload, headers=headers, timeout=timeout)
            return response.status_code, response.json()
        else:
            data_bytes = json.dumps(payload).encode('utf-8')
            req = urllib.request.Request(url, data=data_bytes, headers=headers, method='POST')
            try:
                with urllib.request.urlopen(req, timeout=timeout) as resp:
                    res_body = resp.read().decode('utf-8')
                    return resp.status, json.loads(res_body)
            except urllib.error.HTTPError as e:
                err_body = e.read().decode('utf-8')
                try:
                    return e.code, json.loads(err_body)
                except Exception:
                    return e.code, {'description': str(e)}

    @classmethod
    def _http_get(cls, url: str, headers: dict, timeout: int = 10) -> tuple[int, dict]:
        if HAS_REQUESTS:
            response = requests.get(url, headers=headers, timeout=timeout)
            return response.status_code, response.json()
        else:
            req = urllib.request.Request(url, headers=headers, method='GET')
            try:
                with urllib.request.urlopen(req, timeout=timeout) as resp:
                    res_body = resp.read().decode('utf-8')
                    return resp.status, json.loads(res_body)
            except urllib.error.HTTPError as e:
                err_body = e.read().decode('utf-8')
                try:
                    return e.code, json.loads(err_body)
                except Exception:
                    return e.code, {'description': str(e)}

    @classmethod
    def creer_facture_checkout(cls, paiement: Paiement, commande: Commande, return_url: str = None, cancel_url: str = None, ipn_url: str = None) -> dict:
        """
        Crée une facture de paiement PayDunya et retourne les détails de redirection et le token.
        Le montant est STRICTEMENT extrait du paiement (ou de la commande) et ne peut être altéré.
        """
        base_url = cls.get_base_url()
        endpoint = f"{base_url}/checkout-invoice/create"

        ret_url = return_url or getattr(settings, 'PAYDUNYA_RETURN_URL', '')
        canc_url = cancel_url or getattr(settings, 'PAYDUNYA_CANCEL_URL', '')
        callback_url = ipn_url or getattr(settings, 'PAYDUNYA_IPN_URL', '')

        if '{order_id}' in ret_url:
            ret_url = ret_url.format(order_id=commande.id)

        payload = {
            "invoice": {
                "total_amount": float(paiement.montant),
                "description": f"Commande AYYOU #{commande.numero_commande}"
            },
            "store": {
                "name": "AYYOU",
                "postal_address": "Dakar, Sénégal",
                "phone": getattr(commande.utilisateur, 'numero_telephone', '') or "+221330000000",
                "website_url": "https://ayyou.com"
            },
            "custom_data": {
                "paiement_id": str(paiement.id),
                "commande_id": str(commande.id),
                "reference": paiement.reference
            },
            "actions": {
                "cancel_url": canc_url,
                "return_url": ret_url,
                "callback_url": callback_url
            }
        }

        if commande.utilisateur:
            payload["customer"] = {
                "name": commande.nom_destinataire or commande.utilisateur.get_full_name() or "Client AYYOU",
                "phone": commande.telephone_destinataire or commande.utilisateur.numero_telephone or "",
                "email": commande.utilisateur.email or ""
            }

        headers = cls.get_headers()

        try:
            status_code, res_data = cls._http_post(endpoint, payload, headers, timeout=10)

            if status_code == 200 and res_data.get('response_code') == '00':
                token = res_data.get('token')
                response_text = res_data.get('response_text', '')
                checkout_url = response_text if response_text.startswith('http') else f"{cls.get_checkout_base_url()}/{token}"

                return {
                    'success': True,
                    'token': token,
                    'checkout_url': checkout_url,
                    'response_code': res_data.get('response_code'),
                    'description': res_data.get('description'),
                    'raw': res_data
                }
            else:
                logger.error(f"PayDunya Invoice Creation Failed: {res_data}")
                return {
                    'success': False,
                    'token': res_data.get('token', ''),
                    'checkout_url': '',
                    'response_code': res_data.get('response_code', 'ERROR'),
                    'description': res_data.get('description', 'Erreur création facture PayDunya'),
                    'raw': res_data
                }
        except Exception as e:
            logger.exception(f"PayDunya API Connection Error: {str(e)}")
            return {
                'success': False,
                'token': '',
                'checkout_url': '',
                'response_code': 'EXCEPTION',
                'description': str(e),
                'raw': {}
            }

    @classmethod
    def verifier_facture(cls, token: str) -> dict:
        """
        Vérifie le statut d'une facture auprès des serveurs PayDunya.
        GET/POST /checkout-invoice/confirm/{token}
        """
        base_url = cls.get_base_url()
        endpoint = f"{base_url}/checkout-invoice/confirm/{token}"
        headers = cls.get_headers()

        try:
            status_code, res_data = cls._http_get(endpoint, headers, timeout=10)

            response_code = res_data.get('response_code')
            paydunya_status = res_data.get('status', '').lower()

            is_completed = (response_code == '00' and paydunya_status == 'completed')

            return {
                'success': is_completed,
                'status': paydunya_status,
                'response_code': response_code,
                'invoice': res_data.get('invoice', {}),
                'custom_data': res_data.get('custom_data', {}),
                'raw': res_data
            }
        except Exception as e:
            logger.exception(f"PayDunya Verification Connection Error: {str(e)}")
            return {
                'success': False,
                'status': 'error',
                'response_code': 'EXCEPTION',
                'invoice': {},
                'custom_data': {},
                'raw': {}
            }
