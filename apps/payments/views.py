from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.core.exceptions import ValidationError

from apps.payments.models import Paiement, Facture
from apps.payments.serializers import (
    PaiementSerializer, CreatePaiementSerializer,
    ConfirmPaiementSerializer, FactureSerializer
)
from apps.payments.services import PaymentService


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


class FactureViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Endpoint API REST pour la consultation des factures Client.
    Isolation stricte : un client n'a accès qu'à ses propres factures.
    """
    serializer_class = FactureSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Facture.objects.filter(commande__utilisateur=self.request.user).select_related('commande', 'paiement')
