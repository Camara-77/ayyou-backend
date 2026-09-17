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


class LivraisonViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Endpoint API REST pour la gestion et la consultation des livraisons et profils livreurs.
    Gère la séparation stricte des rôles (Client, Livreur, Admin).
    """
    serializer_class = LivraisonSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_permissions(self):
        if self.action in ['available', 'accept', 'pickup']:
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
        Retourne la liste des missions actuellement disponibles (non affectées).
        """
        queryset = Livraison.objects.filter(
            livreur__isnull=True,
            statut__in=[
                Livraison.STATUT_EN_ATTENTE,
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

    @action(detail=False, methods=['get'], url_path='profile')
    def get_profile(self, request):
        """
        GET /api/deliveries/profile/
        Retourne les informations du profil livreur connecté.
        """
        if not hasattr(request.user, 'profil_livreur') or not request.user.profil_livreur:
            return Response(
                {'detail': "Profil livreur introuvable pour cet utilisateur."},
                status=status.HTTP_404_NOT_FOUND
            )
        serializer = ProfilLivreurSerializer(request.user.profil_livreur)
        return Response(serializer.data, status=status.HTTP_200_OK)

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
