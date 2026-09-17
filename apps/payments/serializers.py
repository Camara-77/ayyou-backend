from rest_framework import serializers
from decimal import Decimal
from django.utils.translation import gettext_lazy as _

from apps.orders.models import Commande
from apps.payments.models import Paiement, Facture
from apps.payments.services import PaymentService


class PaiementSerializer(serializers.ModelSerializer):
    commande_numero = serializers.CharField(source='commande.numero_commande', read_only=True)
    methode_nom = serializers.CharField(source='get_methode_display', read_only=True)
    statut_nom = serializers.CharField(source='get_statut_display', read_only=True)

    class Meta:
        model = Paiement
        fields = [
            'id', 'reference', 'commande', 'commande_numero',
            'montant', 'methode', 'methode_nom', 'statut',
            'statut_nom', 'transaction_externe', 'date_creation',
            'date_paiement', 'metadata'
        ]
        read_only_fields = ['id', 'reference', 'statut', 'transaction_externe', 'date_creation', 'date_paiement']


class CreatePaiementSerializer(serializers.Serializer):
    """
    Serializer de création/initialisation d'un paiement.
    Le montant transmis par le client (s'il existe) est STRICTEMENT ignoré.
    Le serveur utilise toujours le montant total calculé de la commande.
    """
    commande = serializers.PrimaryKeyRelatedField(queryset=Commande.objects.all(), required=True)
    methode = serializers.ChoiceField(choices=Paiement.CHOIX_METHODES, required=True)

    def validate_commande(self, value):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            if value.utilisateur != request.user:
                raise serializers.ValidationError(_("Vous n'êtes pas autorisé à payer une commande appartenant à un autre utilisateur."))
        return value

    def create(self, validated_data):
        commande = validated_data['commande']
        methode = validated_data['methode']
        return PaymentService.initier_paiement(commande, methode)


class ConfirmPaiementSerializer(serializers.Serializer):
    """
    Serializer de confirmation interne d'un paiement (pour tests/simulations).
    """
    transaction_externe = serializers.CharField(required=False, allow_blank=True, default=None)


class FactureSerializer(serializers.ModelSerializer):
    commande_numero = serializers.CharField(source='commande.numero_commande', read_only=True)

    class Meta:
        model = Facture
        fields = [
            'id', 'numero_facture', 'commande', 'commande_numero',
            'paiement', 'nom_client_snapshot', 'telephone_client_snapshot',
            'adresse_livraison_snapshot', 'montant_ht', 'frais_livraison',
            'montant_total', 'details_lignes_snapshot', 'est_payee',
            'date_emission', 'date_paiement'
        ]
        read_only_fields = ['id', 'numero_facture', 'date_emission']
