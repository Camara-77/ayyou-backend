from rest_framework import serializers
from apps.users.models import Utilisateur, ProfilClient, ProfilLivreur, DocumentLivreur, Role
from apps.catalog.models import Etablissement, DocumentEtablissement, Produit, Categorie
from apps.orders.models import Commande, SousCommande
from apps.deliveries.models import Livraison
from apps.payments.models import Paiement
from apps.admin_panel.models import AuditLog


class AuditLogSerializer(serializers.ModelSerializer):
    administrateur_nom = serializers.SerializerMethodField()

    class Meta:
        model = AuditLog
        fields = [
            'id',
            'administrateur',
            'administrateur_nom',
            'admin_email',
            'action',
            'ressource',
            'resource_id',
            'ip_address',
            'statut',
            'details',
            'timestamp',
        ]
        read_only_fields = fields

    def get_administrateur_nom(self, obj):
        if obj.administrateur:
            return obj.administrateur.get_full_name()
        return obj.admin_email or 'Système'


class AdminUserSerializer(serializers.ModelSerializer):
    nom_complet = serializers.CharField(source='get_full_name', read_only=True)
    roles = serializers.SerializerMethodField()
    statut_livreur = serializers.SerializerMethodField()
    nombre_etablissements = serializers.SerializerMethodField()

    class Meta:
        model = Utilisateur
        fields = [
            'id',
            'email',
            'numero_telephone',
            'prenom',
            'nom',
            'nom_complet',
            'mode_actif',
            'est_actif',
            'est_verifie',
            'is_staff',
            'is_superuser',
            'derniere_connexion',
            'date_creation',
            'roles',
            'statut_livreur',
            'nombre_etablissements',
        ]
        read_only_fields = ['id', 'derniere_connexion', 'date_creation']

    def get_roles(self, obj):
        return list(obj.roles_attribues.values_list('role__nom', flat=True))

    def get_statut_livreur(self, obj):
        if hasattr(obj, 'profil_livreur') and obj.profil_livreur:
            return obj.profil_livreur.statut_verification
        return None

    def get_nombre_etablissements(self, obj):
        return obj.etablissements.count()


class AdminCandidateDetailsSerializer(serializers.ModelSerializer):
    nom_complet = serializers.CharField(source='get_full_name', read_only=True)

    class Meta:
        model = Utilisateur
        fields = [
            'id',
            'prenom',
            'nom',
            'nom_complet',
            'email',
            'numero_telephone',
        ]
        read_only_fields = fields


class DocumentEtablissementSerializer(serializers.ModelSerializer):
    fichier_url = serializers.SerializerMethodField()

    class Meta:
        model = DocumentEtablissement
        fields = [
            'id',
            'type_document',
            'statut',
            'commentaire',
            'fichier_url',
            'fichier_url_ou_reference',
            'date_verification',
            'date_creation',
        ]
        read_only_fields = fields

    def get_fichier_url(self, obj):
        url = obj.fichier_url_ou_reference or ''
        if not url:
            return ''
        if url.startswith('http://') or url.startswith('https://'):
            return url
        request = self.context.get('request')
        if request is not None:
            return request.build_absolute_uri(url)
        return url


class DocumentLivreurSerializer(serializers.ModelSerializer):
    fichier_url = serializers.SerializerMethodField()

    class Meta:
        model = DocumentLivreur
        fields = [
            'id',
            'type_document',
            'statut',
            'commentaire',
            'fichier_url',
            'fichier_url_ou_reference',
            'date_verification',
            'date_creation',
        ]
        read_only_fields = fields

    def get_fichier_url(self, obj):
        url = obj.fichier_url_ou_reference or ''
        if not url:
            return ''
        if url.startswith('http://') or url.startswith('https://'):
            return url
        request = self.context.get('request')
        if request is not None:
            return request.build_absolute_uri(url)
        return url


class AdminDriverSerializer(serializers.ModelSerializer):
    utilisateur_id = serializers.IntegerField(source='utilisateur.id', read_only=True)
    prenom = serializers.CharField(source='utilisateur.prenom', read_only=True)
    nom = serializers.CharField(source='utilisateur.nom', read_only=True)
    nom_complet = serializers.CharField(source='utilisateur.get_full_name', read_only=True)
    email = serializers.EmailField(source='utilisateur.email', read_only=True)
    telephone = serializers.CharField(source='utilisateur.numero_telephone', read_only=True)
    is_active = serializers.BooleanField(source='utilisateur.est_actif', read_only=True)
    candidat = AdminCandidateDetailsSerializer(source='utilisateur', read_only=True)
    documents = DocumentLivreurSerializer(many=True, read_only=True)

    class Meta:
        model = ProfilLivreur
        fields = [
            'id',
            'utilisateur_id',
            'prenom',
            'nom',
            'nom_complet',
            'email',
            'telephone',
            'candidat',
            'is_active',
            'statut_verification',
            'est_disponible',
            'type_vehicule',
            'marque',
            'modele',
            'immatriculation',
            'latitude_actuelle',
            'longitude_actuelle',
            'date_derniere_position',
            'documents',
            'date_creation',
        ]
        read_only_fields = fields


class AdminBusinessSerializer(serializers.ModelSerializer):
    proprietaire_id = serializers.IntegerField(source='proprietaire.id', read_only=True, allow_null=True)
    proprietaire_prenom = serializers.CharField(source='proprietaire.prenom', read_only=True, allow_null=True)
    proprietaire_nom = serializers.CharField(source='proprietaire.nom', read_only=True, allow_null=True)
    proprietaire_nom_complet = serializers.SerializerMethodField()
    proprietaire_email = serializers.CharField(source='proprietaire.email', read_only=True, allow_null=True)
    proprietaire_telephone = serializers.CharField(source='proprietaire.numero_telephone', read_only=True, allow_null=True)
    candidat = AdminCandidateDetailsSerializer(source='proprietaire', read_only=True)

    type_display = serializers.CharField(source='get_type_etablissement_display', read_only=True)
    nombre_produits = serializers.SerializerMethodField()
    documents = DocumentEtablissementSerializer(many=True, read_only=True)
    logo = serializers.SerializerMethodField()
    couverture = serializers.SerializerMethodField()

    class Meta:
        model = Etablissement
        fields = [
            'id',
            'nom',
            'type_etablissement',
            'type_display',
            'proprietaire_id',
            'proprietaire_prenom',
            'proprietaire_nom',
            'proprietaire_nom_complet',
            'proprietaire_email',
            'proprietaire_telephone',
            'candidat',
            'logo_url',
            'couverture_url',
            'logo',
            'couverture',
            'slogan',
            'description',
            'adresse',
            'latitude',
            'longitude',
            'note_moyenne',
            'nombre_avis',
            'statut',
            'statut_verification',
            'heure_fermeture',
            'telephone',
            'specialite',
            'nombre_videos',
            'est_verifie',
            'nombre_produits',
            'documents',
            'date_creation',
        ]
        read_only_fields = ['id', 'note_moyenne', 'nombre_avis', 'nombre_videos', 'date_creation']

    def get_proprietaire_nom_complet(self, obj):
        if obj.proprietaire:
            return obj.proprietaire.get_full_name()
        return None

    def get_nombre_produits(self, obj):
        return obj.produits.count()

    def get_logo(self, obj):
        url = obj.logo_url
        if not url:
            return None
        if url.startswith('http://') or url.startswith('https://'):
            return url
        request = self.context.get('request')
        return request.build_absolute_uri(url) if request else url

    def get_couverture(self, obj):
        url = obj.couverture_url
        if not url:
            return None
        if url.startswith('http://') or url.startswith('https://'):
            return url
        request = self.context.get('request')
        return request.build_absolute_uri(url) if request else url



class AdminCategorySerializer(serializers.ModelSerializer):
    nombre_produits = serializers.SerializerMethodField()
    slug = serializers.SlugField(required=False, allow_blank=True)

    class Meta:
        model = Categorie
        fields = [
            'id',
            'slug',
            'nom',
            'icone',
            'image_url',
            'est_active',
            'ordre',
            'nombre_produits',
            'date_creation',
        ]
        read_only_fields = ['id', 'date_creation']

    def get_nombre_produits(self, obj):
        return obj.produits.count()

    def create(self, validated_data):
        from django.utils.text import slugify
        if 'slug' not in validated_data or not validated_data['slug']:
            base_slug = slugify(validated_data.get('nom', 'cat'))
            slug = base_slug
            num = 1
            while Categorie.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{num}"
                num += 1
            validated_data['slug'] = slug
        return super().create(validated_data)


class AdminCatalogProductSerializer(serializers.ModelSerializer):
    etablissement_nom = serializers.CharField(source='etablissement.nom', read_only=True)
    categorie_nom = serializers.CharField(source='categorie.nom', read_only=True, allow_null=True)

    class Meta:
        model = Produit
        fields = [
            'id',
            'etablissement',
            'etablissement_nom',
            'categorie',
            'categorie_nom',
            'nom',
            'description',
            'prix_base',
            'stock_disponible',
            'stock_ayyou_reserve',
            'est_disponible',
            'temps_preparation',
            'nombre_likes',
            'image_url',
            'date_creation',
        ]
        read_only_fields = ['id', 'date_creation']


class AdminOrderSerializer(serializers.ModelSerializer):
    client_nom = serializers.CharField(source='utilisateur.get_full_name', read_only=True)
    client_email = serializers.EmailField(source='utilisateur.email', read_only=True)
    statut_display = serializers.CharField(source='get_statut_display', read_only=True)
    livreur_nom = serializers.SerializerMethodField()

    class Meta:
        model = Commande
        fields = [
            'id',
            'numero_commande',
            'utilisateur',
            'client_nom',
            'client_email',
            'statut',
            'statut_display',
            'sous_total',
            'frais_livraison',
            'total',
            'adresse_livraison',
            'nom_destinataire',
            'telephone_destinataire',
            'livreur_nom',
            'date_creation',
            'date_modification',
        ]
        read_only_fields = fields

    def get_livreur_nom(self, obj):
        if hasattr(obj, 'livraison') and obj.livraison and obj.livraison.livreur:
            return obj.livraison.livreur.utilisateur.get_full_name()
        return None


class AdminDeliverySerializer(serializers.ModelSerializer):
    commande_numero = serializers.CharField(source='commande.numero_commande', read_only=True)
    livreur_nom = serializers.SerializerMethodField()
    statut_display = serializers.CharField(source='get_statut_display', read_only=True)

    class Meta:
        model = Livraison
        fields = [
            'id',
            'commande',
            'commande_numero',
            'livreur',
            'livreur_nom',
            'statut',
            'statut_display',
            'token_qr',
            'code_validation',
            'est_validee',
            'methode_validation',
            'date_validation',
            'created_at',
            'updated_at',
        ]
        read_only_fields = fields

    def get_livreur_nom(self, obj):
        if obj.livreur:
            return obj.livreur.utilisateur.get_full_name()
        return None


class AdminPaymentSerializer(serializers.ModelSerializer):
    commande_numero = serializers.CharField(source='commande.numero_commande', read_only=True)
    methode_display = serializers.CharField(source='get_methode_display', read_only=True)
    statut_display = serializers.CharField(source='get_statut_display', read_only=True)

    class Meta:
        model = Paiement
        fields = [
            'id',
            'commande',
            'commande_numero',
            'reference',
            'montant',
            'methode',
            'methode_display',
            'statut',
            'statut_display',
            'transaction_externe',
            'date_creation',
            'date_paiement',
            'metadata',
        ]
        read_only_fields = fields
