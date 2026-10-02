from rest_framework import serializers
from django.utils.translation import gettext_lazy as _
from .models import Categorie, Etablissement, Produit, VarianteProduit, OptionProduit, PublicationFeed, LikeProduit


class CategorieSerializer(serializers.ModelSerializer):
    """
    Serializer pour les catégories de plats et produits.
    """
    class Meta:
        model = Categorie
        fields = ['id', 'slug', 'nom', 'icone', 'image_url', 'est_active', 'ordre']
        read_only_fields = ['id']


class EtablissementSimplifieSerializer(serializers.ModelSerializer):
    """
    Serializer réseau léger pour l'affichage de l'établissement dans les listes de produits.
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
            'statut',
            'est_verifie',
        ]


class EtablissementSerializer(serializers.ModelSerializer):
    """
    Serializer complet d'un établissement (Restaurant ou Vendeur à domicile).
    Protection des données sensibles du propriétaire (jamais de password/hash).
    """
    proprietaire_nom = serializers.SerializerMethodField()

    class Meta:
        model = Etablissement
        fields = [
            'id',
            'nom',
            'type_etablissement',
            'proprietaire',
            'proprietaire_nom',
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
            'date_creation',
        ]
        read_only_fields = ['id', 'proprietaire', 'note_moyenne', 'nombre_avis', 'date_creation']

    def get_proprietaire_nom(self, obj) -> str:
        if obj.proprietaire:
            return obj.proprietaire.get_full_name()
        return ''

    def validate_latitude(self, value):
        if value is not None and not (-90 <= value <= 90):
            raise serializers.ValidationError(_("La latitude doit être comprise entre -90 et 90 degrees."))
        return value

    def validate_longitude(self, value):
        if value is not None and not (-180 <= value <= 180):
            raise serializers.ValidationError(_("La longitude doit être comprise entre -180 et 180 degrees."))
        return value


class VarianteProduitSerializer(serializers.ModelSerializer):
    """
    Serializer pour les variantes/portions d'un plat.
    """
    class Meta:
        model = VarianteProduit
        fields = ['id', 'produit', 'titre', 'sous_titre', 'surcout_prix', 'est_requis', 'ordre']
        read_only_fields = ['id']

    def validate_surcout_prix(self, value):
        if value < 0:
            raise serializers.ValidationError(_("Le surcoût de la variante doit être supérieur ou égal à 0."))
        return value


class OptionProduitSerializer(serializers.ModelSerializer):
    """
    Serializer pour les sauces et suppléments d'un plat.
    """
    class Meta:
        model = OptionProduit
        fields = ['id', 'produit', 'type_option', 'titre', 'sous_titre', 'surcout_prix', 'est_inclus', 'ordre']
        read_only_fields = ['id']

    def validate_surcout_prix(self, value):
        if value < 0:
            raise serializers.ValidationError(_("Le surcoût de l'option doit être supérieur ou égal à 0."))
        return value


class ProduitListSerializer(serializers.ModelSerializer):
    """
    Serializer léger destiné aux listes de plats et au feed d'actualité.
    Masque les données internes de stock vendeur et évite de charger inutilement les sous-options.
    """
    etablissement = EtablissementSimplifieSerializer(read_only=True)
    categorie = CategorieSerializer(read_only=True)

    class Meta:
        model = Produit
        fields = [
            'id',
            'nom',
            'description',
            'prix_base',
            'image_url',
            'est_disponible',
            'temps_preparation',
            'nombre_likes',
            'tags',
            'categorie',
            'etablissement',
        ]
        read_only_fields = ['id', 'nombre_likes']


class ProduitDetailSerializer(serializers.ModelSerializer):
    """
    Serializer complet pour l'écran de détail d'un plat (/product/:id).
    Embrique les variantes, sauces et suppléments demandés par l'interface Angular.
    """
    etablissement = EtablissementSerializer(read_only=True)
    categorie = CategorieSerializer(read_only=True)
    variantes = VarianteProduitSerializer(many=True, read_only=True)
    sauces = serializers.SerializerMethodField()
    supplements = serializers.SerializerMethodField()

    class Meta:
        model = Produit
        fields = [
            'id',
            'nom',
            'description',
            'prix_base',
            'image_url',
            'images_galerie',
            'est_disponible',
            'temps_preparation',
            'nombre_likes',
            'tags',
            'categorie',
            'etablissement',
            'variantes',
            'sauces',
            'supplements',
        ]
        read_only_fields = ['id', 'nombre_likes']

    def get_sauces(self, obj):
        sauces_options = obj.options.filter(type_option=OptionProduit.TYPE_SAUCE)
        return OptionProduitSerializer(sauces_options, many=True).data

    def get_supplements(self, obj):
        supplements_options = obj.options.filter(type_option=OptionProduit.TYPE_SUPPLEMENT)
        return OptionProduitSerializer(supplements_options, many=True).data

    def validate_prix_base(self, value):
        if value < 0:
            raise serializers.ValidationError(_("Le prix de base doit être supérieur ou égal à 0."))
        return value


class PublicationFeedSerializer(serializers.ModelSerializer):
    """
    Serializer pour les posts verticaux du Feed TikTok-style.
    """
    etablissement = EtablissementSimplifieSerializer(read_only=True)
    produit = ProduitListSerializer(read_only=True)
    is_liked = serializers.SerializerMethodField()
    nombre_likes = serializers.SerializerMethodField()

    class Meta:
        model = PublicationFeed
        fields = [
            'id',
            'etablissement',
            'produit',
            'media_url',
            'cloudinary_public_id',
            'type_media',
            'duree_video',
            'max_duree_secondes',
            'nombre_likes',
            'is_liked',
            'nombre_partages',
            'date_publication',
        ]
        read_only_fields = ['id', 'nombre_likes', 'nombre_partages', 'date_publication']

    def get_nombre_likes(self, obj) -> int:
        return LikeProduit.objects.filter(publication=obj).count()

    def get_is_liked(self, obj) -> bool:
        request = self.context.get('request')
        if request and request.user and request.user.is_authenticated:
            return LikeProduit.objects.filter(utilisateur=request.user, publication=obj).exists()
        return False


class LikeProduitSerializer(serializers.ModelSerializer):
    """
    Serializer pour enregistrer ou retirer un Like client.
    Garantit l'association avec request.user sans impersonnalisation.
    """
    produit_detail = ProduitListSerializer(source='produit', read_only=True)
    publication_feed = PublicationFeedSerializer(source='publication', read_only=True)

    class Meta:
        model = LikeProduit
        fields = ['id', 'utilisateur', 'produit', 'publication', 'produit_detail', 'publication_feed', 'date_creation']
        read_only_fields = ['id', 'utilisateur', 'date_creation']

    def validate(self, attrs):
        produit = attrs.get('produit')
        publication = attrs.get('publication')

        if not produit and not publication:
            raise serializers.ValidationError(_("Un Like doit cibler un produit ou une publication."))

        request = self.context.get('request')
        user = request.user if request else None

        if user and user.is_authenticated:
            if produit and LikeProduit.objects.filter(utilisateur=user, produit=produit).exists():
                raise serializers.ValidationError(_("Vous avez déjà aimé ce produit."))
            if publication and LikeProduit.objects.filter(utilisateur=user, publication=publication).exists():
                raise serializers.ValidationError(_("Vous avez déjà aimé cette publication."))

        return attrs
