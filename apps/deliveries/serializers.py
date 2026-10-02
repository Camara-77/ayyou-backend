from rest_framework import serializers
from apps.deliveries.models import Livraison


class LivraisonSerializer(serializers.ModelSerializer):
    commande_reference = serializers.ReadOnlyField(source='commande.numero_commande')
    statut_display = serializers.ReadOnlyField(source='get_statut_display')
    methode_validation_display = serializers.ReadOnlyField(source='get_methode_validation_display')

    # Informations Financières & Instructions
    frais_livraison = serializers.ReadOnlyField(source='commande.frais_livraison')
    total_commande = serializers.ReadOnlyField(source='commande.total')
    instructions_livraison = serializers.ReadOnlyField(source='commande.instructions_livraison')

    # Informations Destinataire (Client)
    nom_destinataire = serializers.ReadOnlyField(source='commande.nom_destinataire')
    telephone_destinataire = serializers.ReadOnlyField(source='commande.telephone_destinataire')
    adresse_livraison = serializers.ReadOnlyField(source='commande.adresse_livraison')
    latitude_livraison = serializers.ReadOnlyField(source='commande.latitude_livraison')
    longitude_livraison = serializers.ReadOnlyField(source='commande.longitude_livraison')

    # Informations Livreur
    livreur_id = serializers.ReadOnlyField(source='livreur.id', allow_null=True)
    livreur_nom_complet = serializers.SerializerMethodField()
    livreur_telephone = serializers.ReadOnlyField(source='livreur.utilisateur.numero_telephone', allow_null=True)
    livreur_vehicule = serializers.SerializerMethodField()
    livreur_immatriculation = serializers.ReadOnlyField(source='livreur.immatriculation', allow_null=True)
    livreur_photo = serializers.ReadOnlyField(source='livreur.photo_avatar', allow_null=True)
    livreur_latitude = serializers.ReadOnlyField(source='livreur.latitude_actuelle', allow_null=True)
    livreur_longitude = serializers.ReadOnlyField(source='livreur.longitude_actuelle', allow_null=True)
    livreur_derniere_position_date = serializers.ReadOnlyField(source='livreur.date_derniere_position', allow_null=True)
    acceptance_deadline = serializers.SerializerMethodField()
    etablissements = serializers.SerializerMethodField()
    date_attribution = serializers.DateTimeField(read_only=True)
    phase_attribution = serializers.IntegerField(read_only=True)

    class Meta:
        model = Livraison
        fields = [
            'id',
            'commande',
            'commande_reference',
            'statut',
            'statut_display',
            'frais_livraison',
            'total_commande',
            'instructions_livraison',
            'nom_destinataire',
            'telephone_destinataire',
            'adresse_livraison',
            'latitude_livraison',
            'longitude_livraison',
            'livreur',
            'livreur_id',
            'livreur_nom_complet',
            'livreur_telephone',
            'livreur_vehicule',
            'livreur_immatriculation',
            'livreur_photo',
            'livreur_latitude',
            'livreur_longitude',
            'livreur_derniere_position_date',
            'etablissements',
            'token_qr',
            'code_validation',
            'est_validee',
            'methode_validation',
            'methode_validation_display',
            'date_validation',
            'date_attribution',
            'phase_attribution',
            'acceptance_deadline',
            'created_at',
            'updated_at'
        ]
        read_only_fields = [
            'id',
            'commande',
            'livreur',
            'token_qr',
            'code_validation',
            'est_validee',
            'methode_validation',
            'date_validation',
            'date_attribution',
            'phase_attribution',
            'acceptance_deadline',
            'created_at',
            'updated_at'
        ]

    def get_acceptance_deadline(self, obj) -> str | None:
        from datetime import timedelta
        # Le délai d'acceptation de 90 secondes s'applique en phase d'attribution si non acceptée
        if obj.statut in [Livraison.STATUT_EN_ATTENTE, Livraison.STATUT_AFFECTEE] and obj.date_attribution:
            deadline = obj.date_attribution + timedelta(seconds=90)
            return deadline.isoformat()
        return None

    def get_livreur_nom_complet(self, obj) -> str | None:
        if obj.livreur and obj.livreur.utilisateur:
            return obj.livreur.utilisateur.get_full_name()
        return None

    def get_livreur_vehicule(self, obj) -> str | None:
        if obj.livreur:
            modele = getattr(obj.livreur, 'modele', '') or getattr(obj.livreur, 'type_vehicule', '') or ''
            marque = getattr(obj.livreur, 'marque', '') or ''
            res = f"{marque} {modele}".strip()
            return res if res else "Moto AYYOU"
        return None

    def get_etablissements(self, obj):
        res = []
        if not hasattr(obj, 'commande') or not obj.commande:
            return res

        for sc in obj.commande.sous_commandes.all():
            etab = sc.etablissement
            lignes_data = []
            for ligne in sc.lignes.all():
                lignes_data.append({
                    'id': ligne.id,
                    'nom_produit': ligne.nom_produit_snapshot,
                    'quantite': ligne.quantite
                })
            res.append({
                'id': etab.id,
                'nom': etab.nom,
                'adresse': etab.adresse,
                'telephone': etab.telephone,
                'latitude': str(etab.latitude) if etab.latitude is not None else None,
                'longitude': str(etab.longitude) if etab.longitude is not None else None,
                'lignes': lignes_data
            })
    def to_representation(self, instance):
        ret = super().to_representation(instance)
        request = self.context.get('request')
        if request and hasattr(request, 'user') and request.user.is_authenticated:
            user = request.user
            is_driver = (
                hasattr(user, 'profil_livreur') and user.profil_livreur is not None
            )
            query_params = getattr(request, 'query_params', getattr(request, 'GET', {}))
            as_client = query_params.get('as') == 'client'
            is_owner = (instance.commande and instance.commande.utilisateur_id == user.id)

            # Ne JAMAIS exposer le PIN ou le QR Code au livreur dans les charges utiles d'API
            if (is_driver and not as_client) and not is_owner:
                ret.pop('code_validation', None)
                ret.pop('token_qr', None)
        return ret


class ValidateQrSerializer(serializers.Serializer):
    token_qr = serializers.CharField(max_length=128, required=True)


class ValidateCodeSerializer(serializers.Serializer):
    commande = serializers.IntegerField(required=True)
    code_validation = serializers.CharField(max_length=4, min_length=4, required=True)
