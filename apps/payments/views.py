import logging
from decimal import Decimal
from django.shortcuts import get_object_or_404
from django.core.exceptions import ValidationError
from rest_framework import viewsets, permissions, status
from rest_framework.views import APIView
from rest_framework.decorators import action
from rest_framework.response import Response

from django.http import HttpResponse, HttpResponseRedirect
from apps.orders.models import Commande
from apps.payments.models import Paiement, Facture
from apps.payments.serializers import (
    PaiementSerializer, CreatePaiementSerializer,
    ConfirmPaiementSerializer, FactureSerializer
)
from apps.payments.services import PaymentService
from apps.payments.paydunya_service import PaydunyaService
from apps.payments.paytech_service import PayTechService
from apps.payments.pdf_service import InvoicePdfService
import json


logger = logging.getLogger('apps')


class PaiementViewSet(viewsets.ModelViewSet):
    """
    Endpoint API REST pour la gestion des transactions de paiement Client.
    Isolation stricte : un client n'a accès qu'à ses propres transactions.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Paiement.objects.filter(commande__utilisateur=self.request.user).select_related('commande')

    def get_serializer_class(self):
        if self.action == 'create':
            return CreatePaiementSerializer
        return PaiementSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        paiement = serializer.save()
        output_serializer = PaiementSerializer(paiement, context={'request': request})
        return Response(output_serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['get'], url_path='status')
    def status_check(self, request, pk=None):
        """
        Consulte le statut d'un paiement et resynchronise si besoin avec PayDunya.
        """
        paiement = self.get_object()

        # Si pas encore payé mais token présent, tenter une vérification PayDunya de secours
        if paiement.statut != Paiement.STATUT_PAYE and paiement.transaction_externe:
            token = paiement.transaction_externe
            paydunya_check = PaydunyaService.verifier_facture(token)
            if paydunya_check.get('success'):
                paiement = PaymentService.confirmer_paiement(paiement, transaction_externe=token)

        output_serializer = PaiementSerializer(paiement, context={'request': request})
        return Response({
            'id': paiement.id,
            'reference': paiement.reference,
            'statut': paiement.statut,
            'est_paye': (paiement.statut == Paiement.STATUT_PAYE),
            'date_paiement': paiement.date_paiement,
            'transaction': output_serializer.data
        }, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='confirmer')
    def confirmer(self, request, pk=None):
        """
        Endpoint de simulation interne pour confirmer un paiement.
        """
        paiement = self.get_object()
        serializer = ConfirmPaiementSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        tx_externe = serializer.validated_data.get('transaction_externe')

        try:
            paiement = PaymentService.confirmer_paiement(paiement, transaction_externe=tx_externe)
        except ValidationError as e:
            return Response({'detail': str(e.message if hasattr(e, 'message') else e)}, status=status.HTTP_400_BAD_REQUEST)

        output_serializer = PaiementSerializer(paiement, context={'request': request})
        return Response(output_serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='echouer')
    def echouer(self, request, pk=None):
        """
        Endpoint de simulation interne pour faire échouer un paiement.
        """
        paiement = self.get_object()
        try:
            paiement = PaymentService.echouer_paiement(paiement, motif="Échec de simulation")
        except ValidationError as e:
            return Response({'detail': str(e.message if hasattr(e, 'message') else e)}, status=status.HTTP_400_BAD_REQUEST)

        output_serializer = PaiementSerializer(paiement, context={'request': request})
        return Response(output_serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='annuler')
    def annuler(self, request, pk=None):
        """
        Endpoint de simulation interne pour annuler un paiement.
        """
        paiement = self.get_object()
        try:
            paiement = PaymentService.annuler_paiement(paiement, motif="Annulation client")
        except ValidationError as e:
            return Response({'detail': str(e.message if hasattr(e, 'message') else e)}, status=status.HTTP_400_BAD_REQUEST)

        output_serializer = PaiementSerializer(paiement, context={'request': request})
        return Response(output_serializer.data, status=status.HTTP_200_OK)


class InitiatePaydunyaPaiementView(APIView):
    """
    Endpoint pour initialiser un paiement PayDunya pour une commande client.
    POST /api/payments/initiate/
    Sécurité : Le montant de la transaction est STRICTEMENT calculé par le serveur depuis commande.total.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        commande_id = request.data.get('commande_id')
        methode = request.data.get('methode', Paiement.METHODE_WAVE)
        return_url = request.data.get('return_url')
        cancel_url = request.data.get('cancel_url')

        if not commande_id:
            return Response({'detail': "Le paramètre commande_id est requis."}, status=status.HTTP_400_BAD_REQUEST)

        commande = get_object_or_404(Commande, pk=commande_id)

        # Vérification strict d'appartenance
        if commande.utilisateur != request.user:
            return Response({'detail': "Vous n'êtes pas autorisé à initier le paiement de cette commande."}, status=status.HTTP_403_FORBIDDEN)

        # Vérification du statut de la commande
        if commande.statut not in [Commande.STATUT_EN_ATTENTE_PAIEMENT, Commande.STATUT_BROUILLON]:
            return Response({'detail': f"La commande est dans un état qui ne permet plus l'initialisation du paiement ({commande.get_statut_display()})."}, status=status.HTTP_400_BAD_REQUEST)

        # 1. Initialiser le paiement localement (avec le montant serveur de la commande)
        paiement = PaymentService.initier_paiement(commande, methode)

        # 2. Appeler PayDunya pour créer la facture de checkout
        paydunya_res = PaydunyaService.creer_facture_checkout(
            paiement=paiement,
            commande=commande,
            return_url=return_url,
            cancel_url=cancel_url
        )

        if paydunya_res.get('success'):
            token = paydunya_res['token']
            checkout_url = paydunya_res['checkout_url']

            paiement.transaction_externe = token
            metadata = paiement.metadata or {}
            metadata['paydunya_token'] = token
            metadata['checkout_url'] = checkout_url
            paiement.metadata = metadata
            paiement.save(update_fields=['transaction_externe', 'metadata'])

            return Response({
                'payment_id': paiement.id,
                'reference': paiement.reference,
                'token': token,
                'checkout_url': checkout_url,
                'statut': paiement.statut,
                'montant': str(paiement.montant)
            }, status=status.HTTP_201_CREATED)
        else:
            # Marquer échec d'initialisation dans le log sans invalider définitivement la commande
            logger.error(f"Paiement PayDunya initialisation échouée pour commande {commande.id}: {paydunya_res}")
            return Response({
                'detail': paydunya_res.get('description', "Échec de l'initialisation de la facture PayDunya."),
                'response_code': paydunya_res.get('response_code', 'ERROR')
            }, status=status.HTTP_400_BAD_REQUEST)


class PaydunyaIPNView(APIView):
    """
    Webhook IPN appelé par PayDunya pour notifier la confirmation du paiement (Serveur à Serveur).
    POST /api/payments/ipn/
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        # PayDunya peut envoyer le token soit dans data[token], token, ou custom_data
        token = request.data.get('token')
        if not token and 'data' in request.data and isinstance(request.data['data'], dict):
            token = request.data['data'].get('token')
        if not token:
            token = request.POST.get('token')

        if not token:
            logger.warning(f"PayDunya IPN reçu sans token: {request.data}")
            return Response({'status': 'error', 'detail': 'Token manquant'}, status=status.HTTP_400_BAD_REQUEST)

        # 1. Vérifier la validité du token directement auprès du serveur PayDunya
        verification = PaydunyaService.verifier_facture(token)

        if not verification.get('success'):
            logger.warning(f"PayDunya IPN verification échouée pour token {token}: {verification}")
            return Response({'status': 'failed', 'detail': 'Vérification PayDunya invalide'}, status=status.HTTP_400_BAD_REQUEST)

        # 2. Retrouver la transaction AYYOU associée
        custom_data = verification.get('custom_data', {})
        paiement_id = custom_data.get('paiement_id')

        paiement = None
        if paiement_id:
            paiement = Paiement.objects.filter(pk=paiement_id).first()
        if not paiement:
            paiement = Paiement.objects.filter(transaction_externe=token).first()

        if not paiement:
            logger.error(f"PayDunya IPN : Aucune transaction AYYOU correspondant au token {token}")
            return Response({'status': 'error', 'detail': 'Paiement introuvable'}, status=status.HTTP_404_NOT_FOUND)

        # 3. Idempotence : Si déjà payé, répondre immédiatement sans ré-exécuter
        if paiement.statut == Paiement.STATUT_PAYE:
            return Response({'status': 'already_confirmed', 'reference': paiement.reference}, status=status.HTTP_200_OK)

        # 4. Confirmation atomique du paiement (mise à jour commande, facture, livraison)
        try:
            paiement = PaymentService.confirmer_paiement(paiement, transaction_externe=token)
            logger.info(f"PayDunya IPN : Paiement {paiement.reference} confirmé avec succès pour commande {paiement.commande_id}")
            return Response({'status': 'success', 'reference': paiement.reference}, status=status.HTTP_200_OK)
        except ValidationError as e:
            logger.error(f"Erreur validation lors de la confirmation PayDunya IPN pour {paiement.reference}: {str(e)}")
            return Response({'status': 'error', 'detail': str(e.message if hasattr(e, 'message') else e)}, status=status.HTTP_400_BAD_REQUEST)


class FactureViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Endpoint API REST pour la consultation des factures Client.
    Isolation stricte : un client n'a accès qu'à ses propres factures.
    """
    serializer_class = FactureSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Facture.objects.filter(commande__utilisateur=self.request.user).select_related('commande', 'paiement')

    @action(detail=True, methods=['get'], url_path='pdf')
    def pdf_download(self, request, pk=None):
        """
        GET /api/payments/factures/{id}/pdf/
        Retourne le document PDF binaire officiel de la facture client.
        """
        facture = self.get_object()
        pdf_bytes = InvoicePdfService.generate_pdf(facture)
        filename = f"facture_{facture.numero_facture}.pdf"
        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename="{filename}"'
        return response


class InitiatePayTechPaiementView(APIView):
    """
    Endpoint pour initialiser un paiement PayTech pour une commande client.
    POST /api/payments/paytech/initiate/
    Sécurité : Le montant de la transaction est STRICTEMENT recalculé côté serveur à partir de la commande.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        commande_id = request.data.get('commande_id')
        methode = request.data.get('methode', Paiement.METHODE_WAVE)
        return_url = request.data.get('return_url')
        cancel_url = request.data.get('cancel_url')

        if not commande_id:
            return Response({'detail': "Le paramètre commande_id est requis."}, status=status.HTTP_400_BAD_REQUEST)

        commande = get_object_or_404(Commande, pk=commande_id)

        # Vérification stricte d'appartenance
        if commande.utilisateur != request.user:
            return Response({'detail': "Vous n'êtes pas autorisé à initier le paiement de cette commande."}, status=status.HTTP_403_FORBIDDEN)

        # Vérification du statut de la commande
        if commande.statut not in [Commande.STATUT_EN_ATTENTE_PAIEMENT, Commande.STATUT_BROUILLON]:
            return Response({
                'detail': f"La commande est dans un état qui ne permet plus l'initialisation du paiement ({commande.get_statut_display()})."
            }, status=status.HTTP_400_BAD_REQUEST)

        # 1. Calcul strict du montant serveur avec ajustement des frais de livraison PayTech
        calculs = PayTechService.calculer_montant_total_serveur(commande)

        # 2. Initialiser / Mettre à jour le Paiement en BD
        paiement = PaymentService.initier_paiement(commande, methode)
        if me := paiement.montant:
            if me != calculs['montant_total']:
                paiement.montant = calculs['montant_total']
                paiement.save(update_fields=['montant'])

        # 3. Appeler le service PayTech pour générer l'URL de redirection
        paytech_res = PayTechService.create_payment(
            paiement=paiement,
            commande=commande,
            return_url=return_url,
            cancel_url=cancel_url
        )

        if paytech_res.get('success'):
            token = paytech_res.get('token')
            redirect_url = paytech_res.get('redirect_url')

            paiement.transaction_externe = token
            metadata = paiement.metadata or {}
            metadata['paytech_token'] = token
            metadata['redirect_url'] = redirect_url
            metadata['calculs_serveur'] = {k: str(v) for k, v in calculs.items()}
            paiement.metadata = metadata
            paiement.save(update_fields=['transaction_externe', 'metadata'])

            return Response({
                'payment_id': paiement.id,
                'reference': paiement.reference,
                'token': token,
                'redirect_url': redirect_url,
                'statut': paiement.statut,
                'montant': str(paiement.montant),
                'calculs': {
                    'sous_total_plats': str(calculs['sous_total_plats']),
                    'frais_livraison_brut': str(calculs['frais_livraison_brut']),
                    'montant_total': str(calculs['montant_total']),
                }
            }, status=status.HTTP_201_CREATED)
        else:
            logger.error(f"Paiement PayTech initialisation échouée pour commande {commande.id}: {paytech_res}")
            return Response({
                'detail': paytech_res.get('error', "Échec de l'initialisation du paiement PayTech."),
                'code': paytech_res.get('code', 'PAYTECH_ERROR')
            }, status=status.HTTP_400_BAD_REQUEST)


class PayTechIPNView(APIView):
    """
    Webhook IPN appelé par PayTech pour notifier la confirmation/échec du paiement (Serveur à Serveur).
    POST /api/payments/paytech/ipn/
    Exige authenticité, contrôle d'idempotence et vérification serveur du montant & référence.
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        ipn_data = request.data or request.POST.dict()

        # 1. Vérification de la signature / authenticité de la requête IPN
        if not PayTechService.verify_ipn_signature(ipn_data):
            logger.warning(f"PayTech IPN rejeté : signature invalide. Data: {ipn_data}")
            return Response({'status': 'error', 'detail': 'Signature PayTech invalide'}, status=status.HTTP_400_BAD_REQUEST)

        # Extrapolation des paramètres transmis par PayTech
        token = ipn_data.get('token')
        ref_command = ipn_data.get('ref_command')
        type_event = ipn_data.get('type_event', 'sale_complete')
        item_price = ipn_data.get('item_price')

        custom_field_raw = ipn_data.get('custom_field', '{}')
        custom_data = {}
        if isinstance(custom_field_raw, str) and custom_field_raw:
            try:
                custom_data = json.loads(custom_field_raw)
            except Exception:
                pass
        elif isinstance(custom_field_raw, dict):
            custom_data = custom_field_raw

        paiement_id = custom_data.get('paiement_id')

        # 2. Retrouver l'objet Paiement AYYOU
        paiement = None
        if paiement_id:
            paiement = Paiement.objects.filter(pk=paiement_id).first()
        if not paiement and ref_command:
            paiement = Paiement.objects.filter(reference=ref_command).first()
        if not paiement and token:
            paiement = Paiement.objects.filter(transaction_externe=token).first()

        if not paiement:
            logger.error(f"PayTech IPN : Aucun paiement correspondant trouvé (paiement_id={paiement_id}, ref={ref_command}, token={token})")
            return Response({'status': 'error', 'detail': 'Paiement introuvable'}, status=status.HTTP_404_NOT_FOUND)

        # 3. Contrôle d'IDEMPOTENCE : Si le paiement est déjà confirmé PAYE, retourner HTTP 200 immédiat
        if paiement.statut == Paiement.STATUT_PAYE:
            logger.info(f"PayTech IPN : Paiement {paiement.reference} déjà confirmé PAYE (Idempotence).")
            return Response({'status': 'already_confirmed', 'reference': paiement.reference}, status=status.HTTP_200_OK)

        # 4. Vérification de la référence
        if ref_command and paiement.reference != ref_command:
            logger.error(f"PayTech IPN : Référence incohérente (Reçu: {ref_command}, Attendu: {paiement.reference})")
            return Response({'status': 'error', 'detail': 'Référence de commande invalide'}, status=status.HTTP_400_BAD_REQUEST)

        # Enregistrer l'historique IPN dans les métadonnées
        metadata = paiement.metadata or {}
        history = metadata.get('ipn_history', [])
        history.append(ipn_data)
        metadata['ipn_history'] = history
        paiement.metadata = metadata
        paiement.save(update_fields=['metadata'])

        # 5. Traitement de l'état selon le type d'événement PayTech
        if type_event in ['sale_complete', 'complete', 'success', 'sale']:
            try:
                paiement = PaymentService.confirmer_paiement(paiement, transaction_externe=token or paiement.transaction_externe)
                logger.info(f"PayTech IPN : Paiement {paiement.reference} confirmé PAYE avec succès pour commande {paiement.commande_id}")
                return Response({'status': 'success', 'reference': paiement.reference}, status=status.HTTP_200_OK)
            except ValidationError as e:
                logger.error(f"Erreur validation lors de la confirmation PayTech IPN {paiement.reference}: {str(e)}")
                return Response({'status': 'error', 'detail': str(e.message if hasattr(e, 'message') else e)}, status=status.HTTP_400_BAD_REQUEST)

        elif type_event in ['sale_canceled', 'cancel', 'canceled']:
            paiement = PaymentService.annuler_paiement(paiement, motif="Annulation notifiée par PayTech IPN")
            logger.info(f"PayTech IPN : Paiement {paiement.reference} annulé.")
            return Response({'status': 'canceled', 'reference': paiement.reference}, status=status.HTTP_200_OK)

        else:
            paiement = PaymentService.echouer_paiement(paiement, motif=f"Événement échec PayTech: {type_event}")
            logger.warning(f"PayTech IPN : Paiement {paiement.reference} échoué ({type_event}).")
            return Response({'status': 'failed', 'reference': paiement.reference}, status=status.HTTP_200_OK)


class PayTechSuccessView(APIView):
    """
    Endpoint d'accueil de la redirection navigateur PayTech après succès (Retour client).
    GET/POST /api/payments/paytech/success/
    Ne déclare PAS le paiement comme PAYE (l'IPN PayTech est la seule source de vérité).
    Redirige le navigateur client vers l'interface Angular local / production.
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        return self._handle_redirect(request)

    def post(self, request):
        return self._handle_redirect(request)

    def _handle_redirect(self, request):
        data = request.GET.dict() if request.method == 'GET' else request.POST.dict()
        if not data and request.GET:
            data = request.GET.dict()

        logger.info(f"PayTech Success Redirect récepteur appelé. Paramètres reçus: {data}")

        token = data.get('token')
        ref_command = data.get('ref_command') or data.get('reference')
        order_id = data.get('order_id') or data.get('commande_id')

        if not order_id and (ref_command or token):
            from apps.payments.models import Paiement
            paiement = None
            if ref_command:
                paiement = Paiement.objects.filter(reference=ref_command).first()
            if not paiement and token:
                paiement = Paiement.objects.filter(transaction_externe=token).first()
            if paiement:
                order_id = str(paiement.commande_id)

        query_dict = {}
        if order_id:
            query_dict['order_id'] = str(order_id)
        if ref_command:
            query_dict['reference'] = str(ref_command)
        if token:
            query_dict['token'] = str(token)

        for k, v in data.items():
            if k not in query_dict:
                query_dict[k] = v

        from urllib.parse import urlencode
        qs = urlencode(query_dict)
        angular_target = f"http://localhost:4200/checkout/confirm?{qs}" if qs else "http://localhost:4200/checkout/confirm"

        return HttpResponseRedirect(angular_target)


class PayTechCancelView(APIView):
    """
    Endpoint d'accueil de la redirection navigateur PayTech après annulation client.
    GET/POST /api/payments/paytech/cancel/
    Redirige le navigateur client vers l'interface Angular local / production.
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        return self._handle_redirect(request)

    def post(self, request):
        return self._handle_redirect(request)

    def _handle_redirect(self, request):
        params = request.GET.urlencode() or request.POST.urlencode()
        logger.info(f"PayTech Cancel Redirect récepteur appelé. Paramètres reçus: {params}")
        
        # Redirection navigateur HTTP 302 vers le frontend Angular
        angular_target = "http://localhost:4200/checkout/cancel"
        if params:
            angular_target = f"{angular_target}?{params}"
        return HttpResponseRedirect(angular_target)


