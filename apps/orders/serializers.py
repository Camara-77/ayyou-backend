from rest_framework import serializers
from decimal import Decimal

from apps.catalog.models import Produit, VarianteProduit, OptionProduit, Etablissement
from apps.orders.models import (
    Panier, PanierItem, Commande, SousCommande,
    LigneCommande, LigneCommandeVariante, LigneCommandeOption, AdresseLivraison
)


class AdresseLivraisonSerializer(serializers.ModelSerializer):
    """
    Serializer pour la gestion du carnet d'adresses de livraison Client.
    """
    class Meta:
        model = AdresseLivraison
        fields = [
            'id', 'titre', 'adresse', 'latitude', 'longitude',
            'instructions', 'est_defaut', 'date_creation'
        ]
        read_only_fields = ['id', 'date_creation']


class VarianteSimpleSerializer(serializers.ModelSerializer):
    """
    représentation simplifiée d'une variante de produit pour le panier.
    """
    class Meta:
        model = VarianteProduit
        fields = ['id', 'titre', 'surcout_prix']


class OptionSimpleSerializer(serializers.ModelSerializer):
    """
    représentation simplifiée d'une option de produit pour le panier.
    """
    class Meta:
        model = OptionProduit
        fields = ['id', 'type_option', 'titre', 'surcout_prix']


class ProduitPanierSerializer(serializers.ModelSerializer):
    """
    Informations essentielles du produit sérialisées dans un article de panier.
    Exclut strictement les stocks internes et données sensibles.
    """
    etablissement_nom = serializers.CharField(source='etablissement.nom', read_only=True)
    etablissement_id = serializers.CharField(source='etablissement.id', read_only=True)

    class Meta:
        model = Produit
        fields = [
            'id', 'nom', 'description', 'prix_base', 'image_url',
            'etablissement_id', 'etablissement_nom', 'est_disponible'
        ]


class PanierItemSerializer(serializers.ModelSerializer):
    """
    Serializer complet pour la consultation d'un article de panier.
    """
    produit = ProduitPanierSerializer(read_only=True)
    variante = VarianteSimpleSerializer(read_only=True)
    options = OptionSimpleSerializer(many=True, read_only=True)
    prix_total_unitaire = serializers.SerializerMethodField()
    total_ligne = serializers.SerializerMethodField()

    class Meta:
        model = PanierItem
        fields = [
            'id', 'produit', 'quantite', 'prix_unitaire',
            'variante', 'options', 'prix_total_unitaire', 'total_ligne'
        ]

    def get_prix_total_unitaire(self, obj) -> str:
        return str(obj.calculer_prix_total_unitaire())

    def get_total_ligne(self, obj) -> str:
        return str(obj.calculer_total_ligne())


class PanierSerializer(serializers.ModelSerializer):
    """
    Serializer pour la consultation du Panier Client actif.
    """
    items = PanierItemSerializer(many=True, read_only=True)
    total_panier = serializers.SerializerMethodField()
    nombre_articles = serializers.SerializerMethodField()

    class Meta:
        model = Panier
        fields = [
            'id', 'actif', 'items', 'total_panier',
            'nombre_articles', 'date_creation', 'date_modification'
        ]

    def get_total_panier(self, obj) -> str:
        return str(obj.calculer_total())

    def get_nombre_articles(self, obj) -> int:
        return sum(item.quantite for item in obj.items.all())


class AddCartItemSerializer(serializers.Serializer):
    """
    Serializer de validation pour l'ajout d'un produit au panier.
    """
    produit = serializers.IntegerField(required=True)
    quantite = serializers.IntegerField(required=False, default=1, min_value=1)
    variante = serializers.IntegerField(required=False, allow_null=True, default=None)
    options = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        default=list
    )


class UpdateCartItemSerializer(serializers.Serializer):
    """
    Serializer de validation pour la modification de la quantité d'un article.
    """
    quantite = serializers.IntegerField(required=True, min_value=1)


class LigneCommandeOptionSerializer(serializers.ModelSerializer):
    """
    Snapshot de l'option choisie lors de la commande.
    """
    class Meta:
        model = LigneCommandeOption
        fields = ['id', 'nom_option_snapshot', 'type_option_snapshot', 'prix_supplementaire_snapshot']


class LigneCommandeVarianteSerializer(serializers.ModelSerializer):
    """
    Snapshot de la variante choisie lors de la commande.
    """
    class Meta:
        model = LigneCommandeVariante
        fields = ['id', 'nom_variante_snapshot', 'prix_supplementaire_snapshot']


class LigneCommandeSerializer(serializers.ModelSerializer):
    """
    Serializer d'une ligne de commande historique.
    """
    variante_snapshot = LigneCommandeVarianteSerializer(read_only=True)
    options_snapshot = LigneCommandeOptionSerializer(many=True, read_only=True)

    class Meta:
        model = LigneCommande
        fields = [
            'id', 'produit', 'nom_produit_snapshot', 'quantite',
            'prix_unitaire', 'total_ligne', 'variante_snapshot', 'options_snapshot'
        ]


class SousCommandeSerializer(serializers.ModelSerializer):
    """
    Sous-commande d'un établissement au sein d'une commande globale.
    """
    etablissement_nom = serializers.CharField(source='etablissement.nom', read_only=True)
    etablissement_logo = serializers.CharField(source='etablissement.logo_url', read_only=True)
    etablissement_adresse = serializers.CharField(source='etablissement.adresse', read_only=True)
    etablissement_specialite = serializers.CharField(source='etablissement.specialite', read_only=True)
    etablissement_statut = serializers.CharField(source='etablissement.statut', read_only=True)
    lignes = LigneCommandeSerializer(many=True, read_only=True)

    class Meta:
        model = SousCommande
        fields = [
            'id', 'etablissement', 'etablissement_nom', 'etablissement_logo',
            'etablissement_adresse', 'etablissement_specialite', 'etablissement_statut',
            'statut', 'sous_total', 'frais_livraison', 'total', 'lignes'
        ]


class CommandeSerializer(serializers.ModelSerializer):
    """
    Commande globale passée par le Client.
    """
    sous_commandes = SousCommandeSerializer(many=True, read_only=True)

    class Meta:
        model = Commande
        fields = [
            'id', 'numero_commande', 'statut', 'sous_total',
            'frais_livraison', 'total', 'adresse_livraison',
            'latitude_livraison', 'longitude_livraison',
            'instructions_livraison', 'nom_destinataire',
            'telephone_destinataire', 'sous_commandes', 'date_creation'
        ]


class DestinataireSerializer(serializers.Serializer):
    nom = serializers.CharField(required=False, allow_blank=True, default='')
    telephone = serializers.CharField(required=False, allow_blank=True, default='')


class CheckoutSerializer(serializers.Serializer):
    """
    Serializer de validation du payload de passage de commande (Checkout).
    """
    adresse_livraison = serializers.CharField(required=True)
    latitude_livraison = serializers.DecimalField(max_digits=10, decimal_places=7, required=False, allow_null=True, default=None)
    longitude_livraison = serializers.DecimalField(max_digits=10, decimal_places=7, required=False, allow_null=True, default=None)
    instructions_livraison = serializers.CharField(required=False, allow_blank=True, default='')
    destinataire = DestinataireSerializer(required=False, default=dict)
