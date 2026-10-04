from rest_framework import status, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from .serializers import UserProfileSerializer, UserLocationSerializer, UserPhoneUpdateSerializer
from .models import ProfilClient


class UserPhoneUpdateView(APIView):
    """
    API de mise à jour sécurisée du numéro de téléphone du compte utilisateur.
    PATCH /api/users/me/phone/
    POST /api/users/me/phone/
    """
    permission_classes = [permissions.IsAuthenticated]

    def patch(self, request, *args, **kwargs):
        return self._update_phone(request)

    def post(self, request, *args, **kwargs):
        return self._update_phone(request)

    def _update_phone(self, request):
        serializer = UserPhoneUpdateSerializer(data=request.data, context={'request': request})
        if not serializer.is_valid():
            return Response({'errors': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

        new_phone = serializer.validated_data['numero_telephone']
        request.user.numero_telephone = new_phone
        request.user.save(update_fields=['numero_telephone', 'date_modification'])

        profile_serializer = UserProfileSerializer(request.user)
        return Response(
            {
                "message": "Numéro de téléphone mis à jour avec succès.",
                "user": profile_serializer.data
            },
            status=status.HTTP_200_OK
        )


class UserProfileView(APIView):
    """
    API d'affichage et de mise à jour du profil du client connecté.
    GET /api/users/me/
    PUT /api/users/me/
    PATCH /api/users/me/
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        # S'assurer que le ProfilClient existe pour l'utilisateur
        ProfilClient.objects.get_or_create(utilisateur=request.user)
        serializer = UserProfileSerializer(request.user)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def put(self, request, *args, **kwargs):
        return self._update_profile(request, partial=False)

    def patch(self, request, *args, **kwargs):
        return self._update_profile(request, partial=True)

    def _update_profile(self, request, partial=False):
        ProfilClient.objects.get_or_create(utilisateur=request.user)
        serializer = UserProfileSerializer(request.user, data=request.data, partial=partial)

        if not serializer.is_valid():
            return Response({'errors': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)


class UserLocationView(APIView):
    """
    API rapide de mise à jour de la géolocalisation et adresse principale.
    POST /api/users/me/location/
    PATCH /api/users/me/location/
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        return self._update_location(request)

    def patch(self, request, *args, **kwargs):
        return self._update_location(request)

    def _update_location(self, request):
        serializer = UserLocationSerializer(data=request.data)

        if not serializer.is_valid():
            return Response({'errors': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

        profil, _ = ProfilClient.objects.get_or_create(utilisateur=request.user)

        data = serializer.validated_data
        if 'latitude' in data:
            profil.latitude = data['latitude']
        if 'longitude' in data:
            profil.longitude = data['longitude']
        if 'adresse_principale' in data:
            profil.adresse_principale = data['adresse_principale']

        profil.save()

        profile_serializer = UserProfileSerializer(request.user)
        return Response(
            {
                "message": "Géolocalisation mise à jour avec succès.",
                "user": profile_serializer.data
            },
            status=status.HTTP_200_OK
        )


class UserModesView(APIView):
    """
    API de consultation des modes de l'utilisateur connecté.
    GET /api/users/me/modes/
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        from .models import Utilisateur, Role
        user = request.user
        has_driver = (
            hasattr(user, 'profil_livreur') and
            user.profil_livreur is not None and
            user.roles_attribues.filter(role__nom=Role.LIVREUR).exists()
        )
        available_modes = [Utilisateur.MODE_CLIENT]
        if has_driver:
            available_modes.append(Utilisateur.MODE_LIVREUR)

        driver_status = user.profil_livreur.statut_verification if has_driver else None

        return Response(
            {
                "active_mode": user.mode_actif,
                "available_modes": available_modes,
                "can_switch_to_driver": has_driver,
                "driver_status": driver_status
            },
            status=status.HTTP_200_OK
        )


class UserModeSwitchView(APIView):
    """
    API de basculement du mode actif de l'utilisateur (CLIENT ↔ LIVREUR).
    PATCH /api/users/me/mode/
    POST /api/users/me/mode/
    """
    permission_classes = [permissions.IsAuthenticated]

    def patch(self, request, *args, **kwargs):
        return self._switch_mode(request)

    def post(self, request, *args, **kwargs):
        return self._switch_mode(request)

    def _switch_mode(self, request):
        from .models import Utilisateur, Role
        user = request.user
        requested_mode = request.data.get('mode', '').upper()

        if requested_mode not in [Utilisateur.MODE_CLIENT, Utilisateur.MODE_LIVREUR]:
            return Response(
                {'detail': "Mode invalide. Les choix valides sont 'CLIENT' ou 'LIVREUR'."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if requested_mode == Utilisateur.MODE_LIVREUR:
            has_driver = (
                hasattr(user, 'profil_livreur') and
                user.profil_livreur is not None and
                user.roles_attribues.filter(role__nom=Role.LIVREUR).exists()
            )
            if not has_driver:
                return Response(
                    {'detail': "Vous ne possédez pas le rôle ou profil livreur."},
                    status=status.HTTP_403_FORBIDDEN
                )

            user.mode_actif = Utilisateur.MODE_LIVREUR
            user.save(update_fields=['mode_actif'])

        elif requested_mode == Utilisateur.MODE_CLIENT:
            user.mode_actif = Utilisateur.MODE_CLIENT
            user.save(update_fields=['mode_actif'])

            # Si le livreur passe en mode Client, il ne doit pas être sélectionné pour de nouvelles courses
            if hasattr(user, 'profil_livreur') and user.profil_livreur and user.profil_livreur.est_disponible:
                user.profil_livreur.est_disponible = False
                user.profil_livreur.save(update_fields=['est_disponible'])

        profile_serializer = UserProfileSerializer(user)
        return Response(
            {
                "message": f"Passage en mode {user.mode_actif} réussi.",
                "active_mode": user.mode_actif,
                "user": profile_serializer.data
            },
            status=status.HTTP_200_OK
        )

