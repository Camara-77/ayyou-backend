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

    # Informations Établissements & Articles à récupérer
    etablissements = serializers.SerializerMethodField()

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
            'etablissements',
            'token_qr',
            'code_validation',
            'est_validee',
            'methode_validation',
            'methode_validation_display',
            'date_validation',
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
            'created_at',
            'updated_at'
        ]

    def get_livreur_nom_complet(self, obj) -> str | None:
        if obj.livreur and obj.livreur.utilisateur:
            return obj.livreur.utilisateur.get_full_name()
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
        return res


class ValidateQrSerializer(serializers.Serializer):
    token_qr = serializers.CharField(max_length=128, required=True)


class ValidateCodeSerializer(serializers.Serializer):
    commande = serializers.IntegerField(required=True)
    code_validation = serializers.CharField(max_length=6, min_length=6, required=True)
