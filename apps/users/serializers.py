from rest_framework import serializers
from django.utils.translation import gettext_lazy as _
from .models import Utilisateur, ProfilClient, ProfilLivreur, DocumentLivreur


class ProfilClientSerializer(serializers.ModelSerializer):
    """
    Serializer pour le profil spécifique au Client AYYOU.
    """
    class Meta:
        model = ProfilClient
        fields = [
            'id',
            'photo_avatar',
            'adresse_principale',
            'latitude',
            'longitude',
            'date_naissance',
            'notifications_activees',
            'date_creation',
            'date_modification',
        ]
        read_only_fields = ['id', 'date_creation', 'date_modification']


class UserProfileSerializer(serializers.ModelSerializer):
    """
    Serializer complet pour la consultation et la mise à jour du profil du client connecté.
    Gère la mise à jour des champs de l'Utilisateur et de son ProfilClient lié.
    """
    profil_client = ProfilClientSerializer(required=False)
    nom_complet = serializers.SerializerMethodField()
    available_modes = serializers.SerializerMethodField()
    has_driver_profile = serializers.SerializerMethodField()

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
            'available_modes',
            'has_driver_profile',
            'est_actif',
            'est_verifie',
            'derniere_connexion',
            'date_creation',
            'profil_client',
        ]
        read_only_fields = [
            'id',
            'numero_telephone',
            'mode_actif',
            'available_modes',
            'has_driver_profile',
            'est_actif',
            'est_verifie',
            'derniere_connexion',
            'date_creation',
        ]

    def get_nom_complet(self, obj) -> str:
        return obj.get_full_name()

    def get_available_modes(self, obj) -> list:
        from .models import Role
        modes = [Utilisateur.MODE_CLIENT]
        if (
            hasattr(obj, 'profil_livreur') and
            obj.profil_livreur is not None and
            obj.roles_attribues.filter(role__nom=Role.LIVREUR).exists()
        ):
            modes.append(Utilisateur.MODE_LIVREUR)
        return modes

    def get_has_driver_profile(self, obj) -> bool:
        from .models import Role
        return (
            hasattr(obj, 'profil_livreur') and
            obj.profil_livreur is not None and
            obj.roles_attribues.filter(role__nom=Role.LIVREUR).exists()
        )


    def validate_email(self, value):
        if value:
            value = value.strip().lower()
            # Vérifier l'unicité de l'email si modifié par l'utilisateur connecté
            user_id = self.instance.id if self.instance else None
            if Utilisateur.objects.filter(email=value).exclude(id=user_id).exists():
                raise serializers.ValidationError(_("Cette adresse email est déjà utilisée par un autre compte."))
        return value

    def update(self, instance, validated_data):
        profil_data = validated_data.pop('profil_client', None)

        # Mettre à jour les champs directs de l'utilisateur
        for attr, value in validated_data.items():
            if attr in ['prenom', 'nom', 'email']:
                setattr(instance, attr, value)

        instance.save()

        # Mettre à jour les champs du ProfilClient lié s'ils sont fournis
        if profil_data is not None:
            profil, _ = ProfilClient.objects.get_or_create(utilisateur=instance)
            for attr, value in profil_data.items():
                setattr(profil, attr, value)
            profil.save()

        return instance


class UserLocationSerializer(serializers.Serializer):
    """
    Serializer pour la mise à jour rapide de la géolocalisation et adresse du client.
    """
    latitude = serializers.DecimalField(max_digits=10, decimal_places=7, required=False, allow_null=True)
    longitude = serializers.DecimalField(max_digits=10, decimal_places=7, required=False, allow_null=True)
    adresse_principale = serializers.CharField(max_length=255, required=False, allow_blank=True)

    def validate_latitude(self, value):
        if value is not None and not (-90 <= value <= 90):
            raise serializers.ValidationError(_("La latitude doit être comprise entre -90 et 90 degrés."))
        return value

    def validate_longitude(self, value):
        if value is not None and not (-180 <= value <= 180):
            raise serializers.ValidationError(_("La longitude doit être comprise entre -180 et 180 degrés."))
        return value


class DocumentLivreurSerializer(serializers.ModelSerializer):
    """
    Serializer pour les documents justificatifs d'un livreur.
    """
    type_document_display = serializers.CharField(source='get_type_document_display', read_only=True)
    statut_display = serializers.CharField(source='get_statut_display', read_only=True)

    class Meta:
        model = DocumentLivreur
        fields = [
            'id',
            'type_document',
            'type_document_display',
            'fichier_url_ou_reference',
            'statut',
            'statut_display',
            'date_verification',
            'commentaire',
            'date_creation',
            'date_modification',
        ]
        read_only_fields = ['id', 'statut', 'date_verification', 'date_creation', 'date_modification']


class ProfilLivreurSerializer(serializers.ModelSerializer):
    """
    Serializer pour la consultation et la mise à jour du profil Livreur AYYOU Pro.
    Gère la mise à jour des informations de l'Utilisateur et du ProfilLivreur.
    """
    prenom = serializers.CharField(source='utilisateur.prenom', required=False)
    nom = serializers.CharField(source='utilisateur.nom', required=False)
    email = serializers.CharField(source='utilisateur.email', required=False)
    numero_telephone = serializers.CharField(source='utilisateur.numero_telephone', required=False)
    est_verifie = serializers.BooleanField(source='utilisateur.est_verifie', read_only=True)
    matricule = serializers.ReadOnlyField()
    documents = DocumentLivreurSerializer(many=True, read_only=True)
    statut_verification_display = serializers.CharField(source='get_statut_verification_display', read_only=True)
    type_vehicule_display = serializers.CharField(source='get_type_vehicule_display', read_only=True)

    class Meta:
        model = ProfilLivreur
        fields = [
            'id',
            'prenom',
            'nom',
            'email',
            'numero_telephone',
            'est_verifie',
            'matricule',
            'statut_verification',
            'statut_verification_display',
            'est_disponible',
            'latitude_actuelle',
            'longitude_actuelle',
            'date_derniere_position',
            'type_vehicule',
            'type_vehicule_display',
            'marque',
            'modele',
            'immatriculation',
            'photo_avatar',
            'date_expiration_assurance',
            'statut_assurance',
            'equipements_certifies',
            'secteur_intervention',
            'type_compte_reversement',
            'numero_reversement',
            'comptes_reversement',
            'documents',
            'date_creation',
            'date_modification',
        ]
        read_only_fields = ['id', 'statut_verification', 'matricule', 'est_verifie', 'date_creation', 'date_modification']

    def validate_email(self, value):
        if value:
            value = value.strip().lower()
            user = self.instance.utilisateur if self.instance else None
            user_id = user.id if user else None
            if Utilisateur.objects.filter(email=value).exclude(id=user_id).exists():
                raise serializers.ValidationError(_("Cette adresse email est déjà utilisée par un autre compte."))
        return value

    def validate_numero_telephone(self, value):
        if value:
            value = value.strip()
            user = self.instance.utilisateur if self.instance else None
            user_id = user.id if user else None
            if Utilisateur.objects.filter(numero_telephone=value).exclude(id=user_id).exists():
                raise serializers.ValidationError(_("Ce numéro de téléphone est déjà utilisé par un autre compte."))
        return value

    def update(self, instance, validated_data):
        utilisateur_data = validated_data.pop('utilisateur', {})

        # Mettre à jour l'utilisateur lié
        utilisateur = instance.utilisateur
        updated_user = False
        for attr in ['prenom', 'nom', 'email', 'numero_telephone']:
            if attr in utilisateur_data:
                setattr(utilisateur, attr, utilisateur_data[attr])
                updated_user = True

        if updated_user:
            utilisateur.save()

        # Mettre à jour le profil livreur
        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.save()
        return instance

