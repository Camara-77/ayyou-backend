from rest_framework import serializers
from .models import RepasPlanifie
from apps.catalog.models import Produit, Etablissement, VarianteProduit


from django.utils import timezone

class RepasPlanifieSerializer(serializers.ModelSerializer):
    nom_produit = serializers.CharField(source='produit.nom', read_only=True)
    image_url = serializers.CharField(source='produit.image_url', read_only=True)
    nom_etablissement = serializers.CharField(source='etablissement.nom', read_only=True)
    adresse_etablissement = serializers.CharField(source='etablissement.adresse', read_only=True)
    nom_variante = serializers.CharField(source='variante.titre', read_only=True, allow_null=True, default='')
    creneau_display = serializers.CharField(source='get_creneau_display', read_only=True)
    statut_display = serializers.CharField(source='get_statut_display', read_only=True)

    class Meta:
        model = RepasPlanifie
        fields = [
            'id',
            'produit',
            'nom_produit',
            'image_url',
            'etablissement',
            'nom_etablissement',
            'adresse_etablissement',
            'variante',
            'nom_variante',
            'date_planifiee',
            'heure_planifiee',
            'creneau',
            'creneau_display',
            'statut',
            'statut_display',
            'prix_total',
            'quantite',
            'instructions',
            'rappel_valide',
            'rappel_valide_at',
            'rappel_reporte',
            'rappel_reporte_at',
            'date_creation',
            'date_modification',
        ]
        read_only_fields = ['id', 'date_creation', 'date_modification', 'rappel_valide_at', 'rappel_reporte_at']

    def validate(self, attrs):
        produit = attrs.get('produit')
        etablissement = attrs.get('etablissement')

        if produit and not etablissement:
            if getattr(produit, 'etablissement', None):
                attrs['etablissement'] = produit.etablissement
                etablissement = produit.etablissement

        effective_produit = produit or getattr(self.instance, 'produit', None)
        effective_etablissement = etablissement or getattr(self.instance, 'etablissement', None)

        if effective_produit and effective_etablissement:
            if effective_produit.etablissement_id and effective_produit.etablissement_id != effective_etablissement.id:
                raise serializers.ValidationError({
                    "produit": f"Le plat '{effective_produit.nom}' n'est pas proposé par le restaurant '{effective_etablissement.nom}'."
                })
        return attrs

    def update(self, instance, validated_data):
        produit = validated_data.get('produit', instance.produit)
        quantite = validated_data.get('quantite', instance.quantite)
        if ('produit' in validated_data or 'quantite' in validated_data or 'variante' in validated_data) and 'prix_total' not in validated_data:
            if produit and produit.prix_base:
                prix_unit = float(produit.prix_base)
                variante = validated_data.get('variante', instance.variante)
                if variante and hasattr(variante, 'surcout_prix'):
                    prix_unit += float(variante.surcout_prix)
                validated_data['prix_total'] = prix_unit * quantite

        if validated_data.get('rappel_valide') and not instance.rappel_valide:
            instance.rappel_valide_at = timezone.now()
        if validated_data.get('rappel_reporte') and not instance.rappel_reporte:
            instance.rappel_reporte_at = timezone.now()
        return super().update(instance, validated_data)

