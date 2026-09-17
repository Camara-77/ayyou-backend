from rest_framework import status, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from .serializers import RegisterSerializer, VerifyOtpSerializer, LoginSerializer
from .services import RegistrationService, OtpService, LoginService


class RegisterView(APIView):
    """
    API d'inscription Client AYYOU.
    POST /api/auth/register/
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = RegisterSerializer(data=request.data)

        if not serializer.is_valid():
            errors = serializer.errors
            # Vérifier si l'erreur concerne un conflit d'unicité (email ou téléphone) pour le code HTTP 409
            is_conflict = False
            for field in ['email', 'numero_telephone']:
                if field in errors:
                    for err in errors[field]:
                        if 'déjà' in str(err).lower() or 'already' in str(err).lower():
                            is_conflict = True
                            break

            status_code = status.HTTP_409_CONFLICT if is_conflict else status.HTTP_400_BAD_REQUEST
            return Response({'errors': errors}, status=status_code)

        # Déclencher le service d'inscription atomique
        user = RegistrationService.register_client(serializer.validated_data)

        return Response(
            {
                "message": "Inscription réussie. Un code de vérification a été envoyé par SMS.",
                "verification_required": True,
                "verification_type": "VERIFICATION_TELEPHONE"
            },
            status=status.HTTP_201_CREATED
        )


class VerifyOtpView(APIView):
    """
    API de vérification du code OTP SMS Client.
    POST /api/auth/verify-otp/
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = VerifyOtpSerializer(data=request.data)

        if not serializer.is_valid():
            return Response({'errors': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

        numero_telephone = serializer.validated_data['numero_telephone']
        code = serializer.validated_data['code']

        try:
            utilisateur, otp = OtpService.verify_otp_code(numero_telephone, code)
        except ValidationError as exc:
            return Response({'errors': exc.detail}, status=status.HTTP_400_BAD_REQUEST)

        return Response(
            {
                "message": "Numéro de téléphone vérifié avec succès.",
                "verified": True
            },
            status=status.HTTP_200_OK
        )


class LoginView(APIView):
    """
    API de connexion Client AYYOU via Email ou Téléphone + Mot de Passe.
    Génère les tokens JWT Access et Refresh.
    POST /api/auth/login/
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = LoginSerializer(data=request.data)

        if not serializer.is_valid():
            return Response({'errors': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

        identifier = serializer.validated_data['identifier']
        password = serializer.validated_data['password']

        try:
            auth_data = LoginService.authenticate_client(identifier, password)
        except ValidationError as exc:
            # Si le compte n'est pas vérifié, retourner HTTP 403 Forbidden avec détails
            if isinstance(exc.detail, dict) and exc.detail.get('verification_required'):
                return Response({'errors': exc.detail}, status=status.HTTP_403_FORBIDDEN)
            return Response({'errors': exc.detail}, status=status.HTTP_400_BAD_REQUEST)

        return Response(auth_data, status=status.HTTP_200_OK)

