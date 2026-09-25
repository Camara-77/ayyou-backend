from rest_framework import serializers
from django.utils.translation import gettext_lazy as _
from apps.catalog.models import (
    Etablissement,
    Produit,
    VarianteProduit,
    OptionProduit,
    Categorie
)
from apps.orders.models import (
    SousCommande,
    LigneCommande,
    LigneCommandeVariante,
    LigneCommandeOption
)


class MerchantEtablissementSerializer(serializers.ModelSerializer):
    """
    Serializer pour la consultation et la mise à jour par le professionnel de son propre établissement.
    """
    class Meta:
        model = Etablissement
        fields = [
            'id',
            'nom',
            'type_etablissement',
            'logo_url',
            'couverture_url',
            'slogan',
            'description',
            'adresse',
            'latitude',
            'longitude',
            'note_moyenne',
            'nombre_avis',
            'statut',
            'heure_fermeture',
            'telephone',
            'specialite',
            'nombre_videos',
            'est_verifie',
            'statut_verification',
            'date_creation',
            'date_modification',
        ]
        read_only_fields = [
            'id',
            'type_etablissement',
            'note_moyenne',
            'nombre_avis',
            'est_verifie',
            'statut_verification',
            'date_creation',
            'date_modification',
        ]


class MerchantVarianteSerializer(serializers.ModelSerializer):
    """
    Serializer pour la gestion des variantes/portions d'un plat par le professionnel.
    """
    id = serializers.IntegerField(required=False)

    class Meta:
        model = VarianteProduit
        fields = ['id', 'titre', 'sous_titre', 'surcout_prix', 'est_requis', 'ordre']


class MerchantOptionSerializer(serializers.ModelSerializer):
    """
    Serializer pour la gestion des sauces et suppléments par le professionnel.
    """
    id = serializers.IntegerField(required=False)

    class Meta:
        model = OptionProduit
        fields = ['id', 'type_option', 'titre', 'sous_titre', 'surcout_prix', 'est_inclus', 'ordre']


class MerchantProduitSerializer(serializers.ModelSerializer):
    """
    Serializer complet pour les produits du marchand avec gestion du stock,
    de l'allocation AYYOU, des variantes et des options.
    """
    categorie_nom = serializers.CharField(source='categorie.nom', read_only=True)
    variantes = MerchantVarianteSerializer(many=True, required=False)
    options = MerchantOptionSerializer(many=True, required=False)

    class Meta:
        model = Produit
        fields = [
            'id',
            'etablissement',
            'categorie',
            'categorie_nom',
            'nom',
            'description',
            'prix_base',
            'image_url',
            'images_galerie',
            'est_disponible',
            'stock_disponible',
            'stock_ayyou_reserve',
            'temps_preparation',
            'nombre_likes',
            'tags',
            'variantes',
            'options',
            'date_creation',
            'date_modification',
        ]
        read_only_fields = ['id', 'etablissement', 'nombre_likes', 'date_creation', 'date_modification']

    def validate_prix_base(self, value):
        if value < 0:
            raise serializers.ValidationError(_("Le prix de base doit être supérieur ou égal à 0."))
        return value

    def validate_stock_disponible(self, value):
        if value < 0:
            raise serializers.ValidationError(_("Le stock disponible ne peut pas être négatif."))
        return value

    def validate_stock_ayyou_reserve(self, value):
        if value < 0:
            raise serializers.ValidationError(_("Le stock alloué à AYYOU ne peut pas être négatif."))
        return value

    def create(self, validated_data):
        variantes_data = validated_data.pop('variantes', [])
        options_data = validated_data.pop('options', [])

        produit = Produit.objects.create(**validated_data)

        for v_data in variantes_data:
            VarianteProduit.objects.create(produit=produit, **v_data)

        for o_data in options_data:
            OptionProduit.objects.create(produit=produit, **o_data)

        return produit

    def update(self, instance, validated_data):
        variantes_data = validated_data.pop('variantes', None)
        options_data = validated_data.pop('options', None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if variantes_data is not None:
            sent_ids = [item['id'] for item in variantes_data if 'id' in item]
            instance.variantes.exclude(id__in=sent_ids).delete()

            for v_data in variantes_data:
                v_id = v_data.get('id')
                if v_id:
                    VarianteProduit.objects.filter(id=v_id, produit=instance).update(**v_data)
                else:
                    VarianteProduit.objects.create(produit=instance, **v_data)

        if options_data is not None:
            sent_ids = [item['id'] for item in options_data if 'id' in item]
            instance.options.exclude(id__in=sent_ids).delete()

            for o_data in options_data:
                o_id = o_data.get('id')
                if o_id:
                    OptionProduit.objects.filter(id=o_id, produit=instance).update(**o_data)
                else:
                    OptionProduit.objects.create(produit=instance, **o_data)

        return instance


class MerchantLigneCommandeSerializer(serializers.ModelSerializer):
    """
    Serializer pour une ligne de sous-commande d'un marchand.
    """
    nom_produit = serializers.CharField(source='nom_produit_snapshot', read_only=True)
    variante = serializers.SerializerMethodField()
    options = serializers.SerializerMethodField()

    class Meta:
        model = LigneCommande
        fields = [
            'id',
            'produit',
            'nom_produit',
            'quantite',
            'prix_unitaire',
            'total_ligne',
            'variante',
            'options',
        ]
        read_only_fields = ['id', 'produit', 'nom_produit', 'quantite', 'prix_unitaire', 'total_ligne']

    def get_variante(self, obj) -> str:
        if hasattr(obj, 'variante_snapshot') and obj.variante_snapshot:
            return obj.variante_snapshot.nom_variante_snapshot
        return ''

    def get_options(self, obj) -> list:
        if hasattr(obj, 'options_snapshot'):
            return [opt.nom_option_snapshot for opt in obj.options_snapshot.all()]
        return []


class MerchantSousCommandeSerializer(serializers.ModelSerializer):
    """
    Serializer complet pour la gestion d'une sous-commande marchand PRO.
    Expose les lignes d'articles, les informations client et les totaux sans exposer de données sensibles.
    """
    numero_commande = serializers.CharField(source='commande.numero_commande', read_only=True)
    statut_display = serializers.CharField(source='get_statut_display', read_only=True)
    client_nom = serializers.SerializerMethodField()
    client_telephone = serializers.SerializerMethodField()
    adresse_livraison = serializers.CharField(source='commande.adresse_livraison', read_only=True)
    instructions_livraison = serializers.CharField(source='commande.instructions_livraison', read_only=True)
    lignes = MerchantLigneCommandeSerializer(many=True, read_only=True)

    class Meta:
        model = SousCommande
        fields = [
            'id',
            'commande',
            'numero_commande',
            'etablissement',
            'statut',
            'statut_display',
            'sous_total',
            'frais_livraison',
            'total',
            'client_nom',
            'client_telephone',
            'adresse_livraison',
            'instructions_livraison',
            'lignes',
            'date_creation',
            'date_modification',
        ]
        read_only_fields = [
            'id',
            'commande',
            'numero_commande',
            'etablissement',
            'sous_total',
            'frais_livraison',
            'total',
            'client_nom',
            'client_telephone',
            'adresse_livraison',
            'instructions_livraison',
            'lignes',
            'date_creation',
            'date_modification',
        ]

    def get_client_nom(self, obj) -> str:
        if obj.commande and obj.commande.nom_destinataire:
            return obj.commande.nom_destinataire
        if obj.commande and obj.commande.utilisateur:
            return obj.commande.utilisateur.get_full_name()
        return "Client AYYOU"

    def get_client_telephone(self, obj) -> str:
        if obj.commande and obj.commande.telephone_destinataire:
            return obj.commande.telephone_destinataire
        if obj.commande and obj.commande.utilisateur:
            return obj.commande.utilisateur.numero_telephone
        return ""
