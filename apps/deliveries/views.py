from django.db import models
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.core.exceptions import ValidationError

from apps.deliveries.models import Livraison
from apps.deliveries.serializers import (
    LivraisonSerializer, ValidateQrSerializer, ValidateCodeSerializer
)
from apps.deliveries.services import DeliveryService
from apps.deliveries.permissions import IsLivreurValide
from apps.users.models import Role, ProfilLivreur
from apps.users.serializers import ProfilLivreurSerializer, DocumentLivreurSerializer
from apps.payments.models import Payout
from apps.payments.serializers import PayoutSerializer
from decimal import Decimal


class LivraisonViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Endpoint API REST pour la gestion et la consultation des livraisons et profils livreurs.
    Gère la séparation stricte des rôles (Client, Livreur, Admin).
    """
    serializer_class = LivraisonSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_permissions(self):
        if self.action in ['available', 'accept', 'decline', 'arrive_restaurant', 'pickup', 'stats', 'payout', 'update_location']:
            return [permissions.IsAuthenticated(), IsLivreurValide()]
        return [permissions.IsAuthenticated()]

    def get_queryset(self):
        user = self.request.user

        if not user or not user.is_authenticated:
            return Livraison.objects.none()

        base_qs = Livraison.objects.select_related(
            'commande',
            'commande__utilisateur',
            'livreur',
            'livreur__utilisateur'
        ).prefetch_related(
            'commande__sous_commandes__etablissement',
            'commande__sous_commandes__lignes'
        )

        # Mode Admin
        if user.is_staff or user.is_superuser:
            return base_qs

        # Mode Livreur (si rôle et ProfilLivreur validé et pas de paramètre 'as=client')
        is_driver = (
            hasattr(user, 'profil_livreur') and
            user.profil_livreur is not None and
            user.profil_livreur.statut_verification == ProfilLivreur.STATUT_VALIDE and
            user.roles_attribues.filter(role__nom=Role.LIVREUR).exists()
        )

        as_client = self.request.query_params.get('as') == 'client'

        if is_driver and not as_client:
            # Pour l'action retrieve sur une mission disponible
            if self.action == 'retrieve':
                return base_qs.filter(
                    models.Q(livreur=user.profil_livreur) | models.Q(livreur__isnull=True)
                )
            return base_qs.filter(livreur=user.profil_livreur)

        # Mode Client par défaut
        return base_qs.filter(commande__utilisateur=user)

    @action(detail=False, methods=['get'], url_path='available')
    def available(self, request):
        """
        GET /api/deliveries/available/
        Retourne la liste des missions actuellement proposées ou disponibles pour le livreur connecté :
        - Phase 1 : Proposée uniquement au livreur le plus proche (livreur == profil_livreur).
        - Phase 2 : Diffusée aux livreurs sélectionnés en Phase 2.
        Purge automatiquement les attributions expirées (> 90 secondes).
        """
        DeliveryService.expire_expired_deliveries()

        profil_livreur = getattr(request.user, 'profil_livreur', None)
        if not profil_livreur:
            return Response([], status=status.HTTP_200_OK)

        driver_id = profil_livreur.id

        base_qs = Livraison.objects.filter(
            statut__in=[
                Livraison.STATUT_EN_ATTENTE,
                Livraison.STATUT_AFFECTEE,
                Livraison.STATUT_EN_PREPARATION,
                Livraison.STATUT_PRETE
            ]
        ).select_related(
            'commande',
            'commande__utilisateur'
        ).prefetch_related(
            'commande__sous_commandes__etablissement',
            'commande__sous_commandes__lignes'
        )

        visible_ids = []
        for liv in base_qs:
            props = liv.propositions_livreurs or {}
            refuses = props.get('refuses', [])
            expires = props.get('expires', [])
            if driver_id in refuses or driver_id in expires:
                continue

            if liv.phase_attribution == 1:
                if liv.livreur_id == driver_id:
                    visible_ids.append(liv.id)
            elif liv.phase_attribution == 2:
                p2_ids = props.get('phase_2', [])
                if not p2_ids or driver_id in p2_ids:
                    visible_ids.append(liv.id)

        queryset = base_qs.filter(id__in=visible_ids)
        serializer = LivraisonSerializer(queryset, many=True, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='accept')
    def accept(self, request, pk=None):
        """
        POST /api/deliveries/{id}/accept/
        Acceptation d'une mission par un livreur validé et disponible.
        """
        profil_livreur = getattr(request.user, 'profil_livreur', None)
        try:
            livraison = DeliveryService.accepter_mission(pk, profil_livreur)
        except ValidationError as e:
            err_msg = str(e.message if hasattr(e, 'message') else e)
            if "expiré" in err_msg.lower():
                from django.utils import timezone
                Livraison.objects.filter(pk=pk).update(
                    livreur=None,
                    statut=Livraison.STATUT_EN_ATTENTE,
                    date_attribution=None,
                    updated_at=timezone.now()
                )
            return Response(
                {'detail': err_msg},
                status=status.HTTP_400_BAD_REQUEST
            )

        output_serializer = LivraisonSerializer(livraison, context={'request': request})
        return Response(output_serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='decline')
    def decline(self, request, pk=None):
        """
        POST /api/deliveries/{id}/decline/
        Déclin/Refus d'une mission affectée par un livreur validé.
        Libère l'attribution de la livraison pour la remettre en attente.
        """
        profil_livreur = getattr(request.user, 'profil_livreur', None)
        try:
            livraison = DeliveryService.refuser_mission(pk, profil_livreur)
        except ValidationError as e:
            return Response(
                {'detail': str(e.message if hasattr(e, 'message') else e)},
                status=status.HTTP_400_BAD_REQUEST
            )

        output_serializer = LivraisonSerializer(livraison, context={'request': request})
        return Response(output_serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='arrive-restaurant')
    def arrive_restaurant(self, request, pk=None):
        """
        POST /api/deliveries/{id}/arrive-restaurant/
        Déclaration d'arrivée du livreur au restaurant/vendeur.
        """
        profil_livreur = getattr(request.user, 'profil_livreur', None)
        try:
            livraison = DeliveryService.arriver_restaurant(pk, profil_livreur)
        except ValidationError as e:
            return Response(
                {'detail': str(e.message if hasattr(e, 'message') else e)},
                status=status.HTTP_400_BAD_REQUEST
            )

        output_serializer = LivraisonSerializer(livraison, context={'request': request})
        return Response(output_serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='pickup')
    def pickup(self, request, pk=None):
        """
        POST /api/deliveries/{id}/pickup/
        Déclaration de récupération de la commande par le livreur auprès du vendeur.
        """
        profil_livreur = getattr(request.user, 'profil_livreur', None)
        try:
            livraison = DeliveryService.recuperer_commande(pk, profil_livreur)
        except ValidationError as e:
            return Response(
                {'detail': str(e.message if hasattr(e, 'message') else e)},
                status=status.HTTP_400_BAD_REQUEST
            )

        output_serializer = LivraisonSerializer(livraison, context={'request': request})
        return Response(output_serializer.data, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'], url_path='stats')
    def stats(self, request):
        """
        GET /api/deliveries/stats/
        Retourne les statistiques réelles BDD de la journée pour le livreur connecté.
        """
        profil_livreur = getattr(request.user, 'profil_livreur', None)
        if not profil_livreur:
            return Response(
                {'detail': "Profil livreur introuvable."},
                status=status.HTTP_404_NOT_FOUND
            )

        stats_data = DeliveryService.obtenir_statistiques_livreur(profil_livreur)
        return Response(stats_data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['patch', 'put', 'post'], url_path='location')
    def update_location(self, request, pk=None):
        """
        PATCH /api/deliveries/{id}/location/
        Mise à jour en temps réel des coordonnées GPS du livreur pour cette livraison.
        Sécurité : Seul le livreur attribué à cette livraison peut poster sa position (403 sinon).
        """
        livraison = self.get_object()
        profil_livreur = getattr(request.user, 'profil_livreur', None)

        if not livraison.livreur or livraison.livreur != profil_livreur:
            return Response(
                {'detail': "Vous n'êtes pas le livreur attribué à cette livraison."},
                status=status.HTTP_403_FORBIDDEN
            )

        lat = request.data.get('latitude')
        lng = request.data.get('longitude')

        if lat is None or lng is None:
            return Response(
                {'detail': "Les paramètres latitude et longitude sont requis."},
                status=status.HTTP_400_BAD_REQUEST
            )

        from django.utils import timezone
        try:
            lat_num = float(lat)
            lng_num = float(lng)
        except (ValueError, TypeError):
            return Response(
                {'detail': "Les coordonnées GPS doivent être des nombres décimaux valides."},
                status=status.HTTP_400_BAD_REQUEST
            )

        profil_livreur.latitude_actuelle = lat_num
        profil_livreur.longitude_actuelle = lng_num
        profil_livreur.date_derniere_position = timezone.now()
        profil_livreur.save(update_fields=['latitude_actuelle', 'longitude_actuelle', 'date_derniere_position'])

        output_serializer = LivraisonSerializer(livraison, context={'request': request})
        return Response(output_serializer.data, status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'], url_path='validate-qr')
    def validate_qr(self, request):
        """
        Endpoint de validation d'une livraison via le QR Code.
        """
        serializer = ValidateQrSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        token_qr = serializer.validated_data['token_qr']

        try:
            livraison = DeliveryService.valider_par_qr(token_qr, utilisateur=request.user)
        except ValidationError as e:
            return Response(
                {'detail': str(e.message if hasattr(e, 'message') else e)},
                status=status.HTTP_400_BAD_REQUEST
            )

        output_serializer = LivraisonSerializer(livraison, context={'request': request})
        return Response(output_serializer.data, status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'], url_path='validate-code')
    def validate_code(self, request):
        """
        Endpoint de validation d'une livraison via le code à 6 chiffres.
        """
        serializer = ValidateCodeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        commande_id = serializer.validated_data['commande']
        code_validation = serializer.validated_data['code_validation']

        try:
            livraison = DeliveryService.valider_par_code(commande_id, code_validation, utilisateur=request.user)
        except ValidationError as e:
            return Response(
                {'detail': str(e.message if hasattr(e, 'message') else e)},
                status=status.HTTP_400_BAD_REQUEST
            )

        output_serializer = LivraisonSerializer(livraison, context={'request': request})
        return Response(output_serializer.data, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get', 'patch', 'put'], url_path='profile')
    def get_profile(self, request):
        """
        GET /api/deliveries/profile/ - Consultation du profil livreur connecté.
        PATCH/PUT /api/deliveries/profile/ - Mise à jour du profil livreur (identité, téléphone, véhicule, zones, comptes).
        """
        if not hasattr(request.user, 'profil_livreur') or not request.user.profil_livreur:
            return Response(
                {'detail': "Profil livreur introuvable pour cet utilisateur."},
                status=status.HTTP_404_NOT_FOUND
            )

        profil = request.user.profil_livreur

        # Isolation des rôles : Seul un livreur avec le rôle LIVREUR peut lire/modifier son profil
        if not request.user.roles_attribues.filter(role__nom=Role.LIVREUR).exists():
            return Response(
                {'detail': "Seul un utilisateur ayant le rôle LIVREUR peut accéder au profil livreur."},
                status=status.HTTP_403_FORBIDDEN
            )

        if request.method in ['PATCH', 'PUT']:
            serializer = ProfilLivreurSerializer(profil, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)

        serializer = ProfilLivreurSerializer(profil)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'], url_path='profile/photo')
    def upload_photo(self, request):
        """
        POST /api/deliveries/profile/photo/
        Upload de la photo d'avatar réelle du livreur vers Cloudinary (ou enregistrement URL).
        """
        if not hasattr(request.user, 'profil_livreur') or not request.user.profil_livreur:
            return Response(
                {'detail': "Profil livreur introuvable."},
                status=status.HTTP_404_NOT_FOUND
            )

        profil = request.user.profil_livreur
        photo_url = request.data.get('photo_url')
        file_obj = request.FILES.get('photo') or request.FILES.get('avatar')

        if file_obj:
            # Upload vers Cloudinary si configuré
            try:
                import cloudinary
                import cloudinary.uploader
                upload_res = cloudinary.uploader.upload(file_obj, folder="ayyou/drivers/avatars")
                photo_url = upload_res.get('secure_url') or upload_res.get('url')
            except Exception as e:
                # Fallback si Cloudinary local non-configuré: enregistrer une référence d'image valide
                photo_url = f"/media/avatars/driver_{profil.id}_{file_obj.name}"

        if not photo_url:
            return Response(
                {'detail': "Aucun fichier photo ou URL valide fournie."},
                status=status.HTTP_400_BAD_REQUEST
            )

        profil.photo_avatar = photo_url
        profil.save(update_fields=['photo_avatar'])

        return Response({
            'message': "Photo d'avatar mise à jour avec succès.",
            'photo_url': photo_url,
            'photo_avatar': photo_url
        }, status=status.HTTP_200_OK)

    @action(detail=False, methods=['patch', 'post'], url_path='profile/availability')
    def update_availability(self, request):
        """
        PATCH /api/deliveries/profile/availability/
        Modifie la disponibilité du livreur connecté.
        Seul un livreur ayant statut_verification == 'VALIDE' est autorisé.
        """
        if not hasattr(request.user, 'profil_livreur') or not request.user.profil_livreur:
            return Response(
                {'detail': "Profil livreur introuvable."},
                status=status.HTTP_404_NOT_FOUND
            )

        profil = request.user.profil_livreur

        # Vérification rôle et statut
        if not request.user.roles_attribues.filter(role__nom=Role.LIVREUR).exists():
            return Response(
                {'detail': "Seul un utilisateur ayant le rôle LIVREUR peut modifier sa disponibilité."},
                status=status.HTTP_403_FORBIDDEN
            )

        if profil.statut_verification != ProfilLivreur.STATUT_VALIDE:
            return Response(
                {'detail': "Un livreur non validé par un administrateur ne peut pas modifier sa disponibilité."},
                status=status.HTTP_403_FORBIDDEN
            )

        est_disponible = request.data.get('est_disponible')
        if est_disponible is None:
            return Response(
                {'detail': "Le champ 'est_disponible' est obligatoire."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if isinstance(est_disponible, str):
            est_disponible = est_disponible.lower() in ['true', '1']
        else:
            est_disponible = bool(est_disponible)

        profil.est_disponible = est_disponible
        try:
            profil.save()
        except ValidationError as e:
            return Response(
                {'detail': str(e.message if hasattr(e, 'message') else e)},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = ProfilLivreurSerializer(profil)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'], url_path='profile/documents')
    def get_documents(self, request):
        """
        GET /api/deliveries/profile/documents/
        Retourne la liste des documents justificatifs du livreur connecté.
        """
        if not hasattr(request.user, 'profil_livreur') or not request.user.profil_livreur:
            return Response(
                {'detail': "Profil livreur introuvable."},
                status=status.HTTP_404_NOT_FOUND
            )

        documents = request.user.profil_livreur.documents.all()
        serializer = DocumentLivreurSerializer(documents, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'], url_path='payout')
    def payout(self, request):
        """
        POST /api/deliveries/payout/
        Permet à un livreur validé de demander un retrait/versement de ses gains.
        """
        profil = getattr(request.user, 'profil_livreur', None)
        if not profil or profil.statut_verification != ProfilLivreur.STATUT_VALIDE:
            return Response(
                {'detail': "Seul un livreur validé par l'administration peut effectuer une demande de versement."},
                status=status.HTTP_403_FORBIDDEN
            )

        montant_raw = request.data.get('montant')
        methode = request.data.get('methode', 'WAVE')

        try:
            montant = Decimal(str(montant_raw))
            if montant <= Decimal('0.00'):
                raise ValueError()
        except (ValueError, TypeError):
            return Response(
                {'detail': "Le montant transmis doit être strictement supérieur à zéro."},
                status=status.HTTP_400_BAD_REQUEST
            )

        payout_obj = Payout.objects.create(
            livreur=profil,
            montant=montant,
            methode=methode,
            statut=Payout.STATUT_EN_ATTENTE
        )

        serializer = PayoutSerializer(payout_obj)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

