import os
import uuid
from django.db import transaction
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from rest_framework import serializers
from django.utils.translation import gettext_lazy as _
from apps.users.models import Utilisateur, Role, UtilisateurRole, ProfilLivreur, DocumentLivreur
from apps.catalog.models import Etablissement, DocumentEtablissement


def save_pro_file(uploaded_file, subfolder='documents'):
    if not uploaded_file:
        return None
    ext = os.path.splitext(uploaded_file.name)[1].lower()
    valid_exts = ['.pdf', '.jpg', '.jpeg', '.png', '.webp']
    if ext not in valid_exts:
        raise serializers.ValidationError(_(f"Format de fichier non autorisé ({ext}). Formats acceptés: PDF, JPG, PNG, WEBP."))
    if uploaded_file.size > 10 * 1024 * 1024:
        raise serializers.ValidationError(_("Fichier trop volumineux. La taille maximale autorisée est de 10 Mo."))

    safe_name = f"{uuid.uuid4().hex[:12]}_{os.path.basename(uploaded_file.name)}"
    relative_path = os.path.join('pro_uploads', subfolder, safe_name)
    saved_path = default_storage.save(relative_path, ContentFile(uploaded_file.read()))
    url = default_storage.url(saved_path)
    return url if url.startswith('/') or url.startswith('http') else f"/{url}"


class RestaurantRegistrationSerializer(serializers.Serializer):
    email = serializers.EmailField()
    numero_telephone = serializers.CharField(max_length=30)
    password = serializers.CharField(write_only=True, min_length=6)
    password_confirm = serializers.CharField(write_only=True, min_length=6)
    prenom = serializers.CharField(max_length=150)
    nom = serializers.CharField(max_length=150)

    nom_etablissement = serializers.CharField(max_length=200)
    adresse = serializers.CharField(max_length=255)
    slogan = serializers.CharField(max_length=255, required=False, allow_blank=True, default='')
    specialite = serializers.CharField(max_length=150, required=False, allow_blank=True, default='')
    telephone_etablissement = serializers.CharField(max_length=30, required=False, allow_blank=True, default='')

    # Files
    ninea_file = serializers.FileField(required=False, write_only=True, allow_null=True)
    hygiene_file = serializers.FileField(required=False, write_only=True, allow_null=True)
    photo_facade = serializers.FileField(required=False, write_only=True, allow_null=True)
    photo_interior = serializers.FileField(required=False, write_only=True, allow_null=True)
    photo_dining = serializers.FileField(required=False, write_only=True, allow_null=True)
    photo_kitchen = serializers.FileField(required=False, write_only=True, allow_null=True)

    def validate_email(self, value):
        email = value.strip().lower()
        if Utilisateur.objects.filter(email=email).exists():
            raise serializers.ValidationError(_("Un utilisateur avec cet email existe déjà."))
        return email

    def validate_numero_telephone(self, value):
        phone = value.strip()
        if Utilisateur.objects.filter(numero_telephone=phone).exists():
            raise serializers.ValidationError(_("Ce numéro de téléphone est déjà utilisé."))
        return phone

    def validate(self, attrs):
        if attrs.get('password') != attrs.get('password_confirm'):
            raise serializers.ValidationError({"password_confirm": _("Les mots de passe ne correspondent pas.")})
        return attrs

    def create(self, validated_data):
        email = validated_data['email']
        phone = validated_data['numero_telephone']
        password = validated_data['password']
        prenom = validated_data['prenom']
        nom = validated_data['nom']

        ninea_file = validated_data.get('ninea_file')
        hygiene_file = validated_data.get('hygiene_file')
        photo_facade = validated_data.get('photo_facade')
        photo_interior = validated_data.get('photo_interior')
        photo_dining = validated_data.get('photo_dining')
        photo_kitchen = validated_data.get('photo_kitchen')

        with transaction.atomic():
            # 1. Créer l'utilisateur
            user = Utilisateur.objects.create_user(
                email=email,
                numero_telephone=phone,
                password=password,
                prenom=prenom,
                nom=nom,
                est_actif=True,
                est_verifie=True
            )

            # 2. Attribuer le rôle RESTAURANT
            role_resto, _ = Role.objects.get_or_create(
                nom=Role.RESTAURANT,
                defaults={'description': 'Gestionnaire de Restaurant'}
            )
            UtilisateurRole.objects.create(utilisateur=user, role=role_resto)

            facade_url = save_pro_file(photo_facade, 'photos') if photo_facade else None

            # 3. Créer l'Etablissement avec statut EN_ATTENTE
            etablissement = Etablissement.objects.create(
                nom=validated_data['nom_etablissement'],
                type_etablissement=Etablissement.TYPE_RESTAURANT,
                proprietaire=user,
                adresse=validated_data['adresse'],
                slogan=validated_data.get('slogan', ''),
                specialite=validated_data.get('specialite', ''),
                telephone=validated_data.get('telephone_etablissement', '') or phone,
                couverture_url=facade_url,
                statut_verification=Etablissement.STATUT_EN_ATTENTE,
                est_verifie=False
            )

            # 4. Sauvegarder les documents justificatifs
            if ninea_file:
                url = save_pro_file(ninea_file, 'documents')
                if url:
                    DocumentEtablissement.objects.create(
                        etablissement=etablissement,
                        type_document=DocumentEtablissement.TYPE_REGISTRE_COMMERCE,
                        fichier_url_ou_reference=url,
                        statut=DocumentEtablissement.STATUT_EN_ATTENTE
                    )

            if hygiene_file:
                url = save_pro_file(hygiene_file, 'documents')
                if url:
                    DocumentEtablissement.objects.create(
                        etablissement=etablissement,
                        type_document=DocumentEtablissement.TYPE_CERTIFICAT_HYGIENE,
                        fichier_url_ou_reference=url,
                        statut=DocumentEtablissement.STATUT_EN_ATTENTE
                    )

            for photo_obj, label in [(photo_interior, 'Photo Intérieur'), (photo_dining, 'Photo Salle'), (photo_kitchen, 'Photo Cuisine')]:
                if photo_obj:
                    url = save_pro_file(photo_obj, 'photos')
                    if url:
                        DocumentEtablissement.objects.create(
                            etablissement=etablissement,
                            type_document=DocumentEtablissement.TYPE_AUTRE,
                            fichier_url_ou_reference=url,
                            commentaire=label,
                            statut=DocumentEtablissement.STATUT_EN_ATTENTE
                        )

        return {
            'user': user,
            'etablissement': etablissement,
            'statut_verification': Etablissement.STATUT_EN_ATTENTE,
            'type_etablissement': Etablissement.TYPE_RESTAURANT
        }


class VendeurRegistrationSerializer(serializers.Serializer):
    email = serializers.EmailField()
    numero_telephone = serializers.CharField(max_length=30)
    password = serializers.CharField(write_only=True, min_length=6)
    password_confirm = serializers.CharField(write_only=True, min_length=6)
    prenom = serializers.CharField(max_length=150)
    nom = serializers.CharField(max_length=150)

    nom_etablissement = serializers.CharField(max_length=200)
    adresse = serializers.CharField(max_length=255)
    slogan = serializers.CharField(max_length=255, required=False, allow_blank=True, default='')
    specialite = serializers.CharField(max_length=150, required=False, allow_blank=True, default='')
    telephone_etablissement = serializers.CharField(max_length=30, required=False, allow_blank=True, default='')

    # Files
    ninea_file = serializers.FileField(required=False, write_only=True, allow_null=True)
    hygiene_file = serializers.FileField(required=False, write_only=True, allow_null=True)
    photo_facade = serializers.FileField(required=False, write_only=True, allow_null=True)
    photo_stock = serializers.FileField(required=False, write_only=True, allow_null=True)
    photo_products = serializers.FileField(required=False, write_only=True, allow_null=True)

    def validate_email(self, value):
        email = value.strip().lower()
        if Utilisateur.objects.filter(email=email).exists():
            raise serializers.ValidationError(_("Un utilisateur avec cet email existe déjà."))
        return email

    def validate_numero_telephone(self, value):
        phone = value.strip()
        if Utilisateur.objects.filter(numero_telephone=phone).exists():
            raise serializers.ValidationError(_("Ce numéro de téléphone est déjà utilisé."))
        return phone

    def validate(self, attrs):
        if attrs.get('password') != attrs.get('password_confirm'):
            raise serializers.ValidationError({"password_confirm": _("Les mots de passe ne correspondent pas.")})
        return attrs

    def create(self, validated_data):
        email = validated_data['email']
        phone = validated_data['numero_telephone']
        password = validated_data['password']
        prenom = validated_data['prenom']
        nom = validated_data['nom']

        ninea_file = validated_data.get('ninea_file')
        hygiene_file = validated_data.get('hygiene_file')
        photo_facade = validated_data.get('photo_facade')
        photo_stock = validated_data.get('photo_stock')
        photo_products = validated_data.get('photo_products')

        with transaction.atomic():
            # 1. Créer l'utilisateur
            user = Utilisateur.objects.create_user(
                email=email,
                numero_telephone=phone,
                password=password,
                prenom=prenom,
                nom=nom,
                est_actif=True,
                est_verifie=True
            )

            # 2. Attribuer le rôle VENDEUR
            role_vendeur, _ = Role.objects.get_or_create(
                nom=Role.VENDEUR,
                defaults={'description': 'Vendeur à domicile / Commerce'}
            )
            UtilisateurRole.objects.create(utilisateur=user, role=role_vendeur)

            facade_url = save_pro_file(photo_facade, 'photos') if photo_facade else None

            # 3. Créer l'Etablissement avec statut EN_ATTENTE
            etablissement = Etablissement.objects.create(
                nom=validated_data['nom_etablissement'],
                type_etablissement=Etablissement.TYPE_VENDEUR,
                proprietaire=user,
                adresse=validated_data['adresse'],
                slogan=validated_data.get('slogan', ''),
                specialite=validated_data.get('specialite', ''),
                telephone=validated_data.get('telephone_etablissement', '') or phone,
                couverture_url=facade_url,
                statut_verification=Etablissement.STATUT_EN_ATTENTE,
                est_verifie=False
            )

            # 4. Sauvegarder les documents justificatifs
            if ninea_file:
                url = save_pro_file(ninea_file, 'documents')
                if url:
                    DocumentEtablissement.objects.create(
                        etablissement=etablissement,
                        type_document=DocumentEtablissement.TYPE_REGISTRE_COMMERCE,
                        fichier_url_ou_reference=url,
                        statut=DocumentEtablissement.STATUT_EN_ATTENTE
                    )

            if hygiene_file:
                url = save_pro_file(hygiene_file, 'documents')
                if url:
                    DocumentEtablissement.objects.create(
                        etablissement=etablissement,
                        type_document=DocumentEtablissement.TYPE_CERTIFICAT_HYGIENE,
                        fichier_url_ou_reference=url,
                        statut=DocumentEtablissement.STATUT_EN_ATTENTE
                    )

            for photo_obj, label in [(photo_stock, 'Photo Stock'), (photo_products, 'Photo Produits')]:
                if photo_obj:
                    url = save_pro_file(photo_obj, 'photos')
                    if url:
                        DocumentEtablissement.objects.create(
                            etablissement=etablissement,
                            type_document=DocumentEtablissement.TYPE_AUTRE,
                            fichier_url_ou_reference=url,
                            commentaire=label,
                            statut=DocumentEtablissement.STATUT_EN_ATTENTE
                        )

        return {
            'user': user,
            'etablissement': etablissement,
            'statut_verification': Etablissement.STATUT_EN_ATTENTE,
            'type_etablissement': Etablissement.TYPE_VENDEUR
        }


class LivreurRegistrationSerializer(serializers.Serializer):
    email = serializers.EmailField()
    numero_telephone = serializers.CharField(max_length=30)
    password = serializers.CharField(write_only=True, min_length=6)
    password_confirm = serializers.CharField(write_only=True, min_length=6)
    prenom = serializers.CharField(max_length=150)
    nom = serializers.CharField(max_length=150)

    type_vehicule = serializers.ChoiceField(
        choices=ProfilLivreur.CHOIX_TYPE_VEHICULE,
        default=ProfilLivreur.VEHICULE_MOTO
    )
    marque = serializers.CharField(max_length=100, required=False, allow_blank=True, default='')
    modele = serializers.CharField(max_length=100, required=False, allow_blank=True, default='')
    immatriculation = serializers.CharField(max_length=50, required=False, allow_blank=True, default='')

    # Files
    cni_file = serializers.FileField(required=False, write_only=True, allow_null=True)
    permis_file = serializers.FileField(required=False, write_only=True, allow_null=True)
    casier_file = serializers.FileField(required=False, write_only=True, allow_null=True)
    carte_grise_file = serializers.FileField(required=False, write_only=True, allow_null=True)

    def validate_email(self, value):
        email = value.strip().lower()
        if Utilisateur.objects.filter(email=email).exists():
            raise serializers.ValidationError(_("Un utilisateur avec cet email existe déjà."))
        return email

    def validate_numero_telephone(self, value):
        phone = value.strip()
        if Utilisateur.objects.filter(numero_telephone=phone).exists():
            raise serializers.ValidationError(_("Ce numéro de téléphone est déjà utilisé."))
        return phone

    def validate(self, attrs):
        if attrs.get('password') != attrs.get('password_confirm'):
            raise serializers.ValidationError({"password_confirm": _("Les mots de passe ne correspondent pas.")})
        return attrs

    def create(self, validated_data):
        email = validated_data['email']
        phone = validated_data['numero_telephone']
        password = validated_data['password']
        prenom = validated_data['prenom']
        nom = validated_data['nom']

        cni_file = validated_data.get('cni_file')
        permis_file = validated_data.get('permis_file')
        casier_file = validated_data.get('casier_file')
        carte_grise_file = validated_data.get('carte_grise_file')

        with transaction.atomic():
            # 1. Créer l'utilisateur
            user = Utilisateur.objects.create_user(
                email=email,
                numero_telephone=phone,
                password=password,
                prenom=prenom,
                nom=nom,
                est_actif=True,
                est_verifie=True,
                mode_actif=Utilisateur.MODE_LIVREUR
            )

            # 2. Attribuer le rôle LIVREUR
            role_livreur, _ = Role.objects.get_or_create(
                nom=Role.LIVREUR,
                defaults={'description': 'Livreur partenaire AYYOU'}
            )
            UtilisateurRole.objects.create(utilisateur=user, role=role_livreur)

            # 3. Créer le ProfilLivreur avec statut EN_ATTENTE
            profil_livreur = ProfilLivreur.objects.create(
                utilisateur=user,
                statut_verification=ProfilLivreur.STATUT_EN_ATTENTE,
                est_disponible=False,
                type_vehicule=validated_data.get('type_vehicule', ProfilLivreur.VEHICULE_MOTO),
                marque=validated_data.get('marque', ''),
                modele=validated_data.get('modele', ''),
                immatriculation=validated_data.get('immatriculation', '')
            )

            # 4. Sauvegarder les documents justificatifs
            if cni_file:
                url = save_pro_file(cni_file, 'documents')
                if url:
                    DocumentLivreur.objects.create(
                        profil_livreur=profil_livreur,
                        type_document=DocumentLivreur.TYPE_PIECE_IDENTITE,
                        fichier_url_ou_reference=url,
                        statut=DocumentLivreur.STATUT_EN_ATTENTE
                    )

            if permis_file:
                url = save_pro_file(permis_file, 'documents')
                if url:
                    DocumentLivreur.objects.create(
                        profil_livreur=profil_livreur,
                        type_document=DocumentLivreur.TYPE_PERMIS_CONDUIRE,
                        fichier_url_ou_reference=url,
                        statut=DocumentLivreur.STATUT_EN_ATTENTE
                    )

            if carte_grise_file:
                url = save_pro_file(carte_grise_file, 'documents')
                if url:
                    DocumentLivreur.objects.create(
                        profil_livreur=profil_livreur,
                        type_document=DocumentLivreur.TYPE_CARTE_GRISE,
                        fichier_url_ou_reference=url,
                        statut=DocumentLivreur.STATUT_EN_ATTENTE
                    )

            if casier_file:
                url = save_pro_file(casier_file, 'documents')
                if url:
                    DocumentLivreur.objects.create(
                        profil_livreur=profil_livreur,
                        type_document=DocumentLivreur.TYPE_AUTRE,
                        fichier_url_ou_reference=url,
                        commentaire='Casier Judiciaire (B3)',
                        statut=DocumentLivreur.STATUT_EN_ATTENTE
                    )

        return {
            'user': user,
            'profil_livreur': profil_livreur,
            'statut_verification': ProfilLivreur.STATUT_EN_ATTENTE
        }


class ProApplicationStatusSerializer(serializers.Serializer):
    user_id = serializers.IntegerField(source='id')
    email = serializers.EmailField()
    nom_complet = serializers.CharField(source='get_full_name')
    roles = serializers.SerializerMethodField()
    is_approved = serializers.SerializerMethodField()
    merchant_status = serializers.SerializerMethodField()
    driver_status = serializers.SerializerMethodField()
    etablissement = serializers.SerializerMethodField()
    profil_livreur = serializers.SerializerMethodField()

    def get_roles(self, obj):
        return list(obj.roles_attribues.values_list('role__nom', flat=True))

    def get_merchant_status(self, obj):
        etab = obj.etablissements.first()
        if etab:
            return etab.statut_verification
        return None

    def get_driver_status(self, obj):
        if hasattr(obj, 'profil_livreur') and obj.profil_livreur:
            return obj.profil_livreur.statut_verification
        return None

    def get_is_approved(self, obj):
        merchant_ok = obj.etablissements.filter(statut_verification='VALIDE').exists()
        driver_ok = hasattr(obj, 'profil_livreur') and obj.profil_livreur and obj.profil_livreur.statut_verification == 'VALIDE'
        return merchant_ok or driver_ok

    def get_etablissement(self, obj):
        etab = obj.etablissements.first()
        if etab:
            return {
                'id': etab.id,
                'nom': etab.nom,
                'type_etablissement': etab.type_etablissement,
                'statut_verification': etab.statut_verification,
                'est_verifie': etab.est_verifie,
                'adresse': etab.adresse
            }
        return None

    def get_profil_livreur(self, obj):
        if hasattr(obj, 'profil_livreur') and obj.profil_livreur:
            p = obj.profil_livreur
            return {
                'id': p.id,
                'statut_verification': p.statut_verification,
                'est_disponible': p.est_disponible,
                'type_vehicule': p.type_vehicule,
                'immatriculation': p.immatriculation
            }
        return None
