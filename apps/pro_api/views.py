from rest_framework import status, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated

from .permissions import IsProCandidate
from .serializers import (
    RestaurantRegistrationSerializer,
    VendeurRegistrationSerializer,
    LivreurRegistrationSerializer,
    ProApplicationStatusSerializer
)


class RegisterRestaurantView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RestaurantRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            result = serializer.save()
            return Response({
                'message': 'Candidature restaurant enregistrée avec succès. Votre dossier est en cours d\'examen par l\'équipe AYYOU.',
                'user_id': result['user'].id,
                'etablissement_id': result['etablissement'].id,
                'type_etablissement': result['type_etablissement'],
                'statut_verification': result['statut_verification']
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class RegisterVendeurView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = VendeurRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            result = serializer.save()
            return Response({
                'message': 'Candidature vendeur enregistrée avec succès. Votre dossier est en cours d\'examen par l\'équipe AYYOU.',
                'user_id': result['user'].id,
                'etablissement_id': result['etablissement'].id,
                'type_etablissement': result['type_etablissement'],
                'statut_verification': result['statut_verification']
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class RegisterLivreurView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LivreurRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            result = serializer.save()
            return Response({
                'message': 'Candidature livreur enregistrée avec succès. Votre dossier est en cours d\'examen par l\'équipe AYYOU.',
                'user_id': result['user'].id,
                'profil_livreur_id': result['profil_livreur'].id,
                'statut_verification': result['statut_verification']
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ProStatusView(APIView):
    permission_classes = [IsAuthenticated, IsProCandidate]

    def get(self, request):
        serializer = ProApplicationStatusSerializer(request.user)
        return Response(serializer.data, status=status.HTTP_200_OK)
