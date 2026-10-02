from rest_framework import status, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from .serializers import RegisterSerializer, VerifyOtpSerializer, LoginSerializer
from .services import RegistrationService, OtpService, LoginService


class RegisterView(APIView):
    """
    API REST d'inscription des nouveaux clients AYYOU.
    Endpoint : POST /api/auth/register/
    Accès : Public (AllowAny). Aucun token JWT requis.
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        """
        Reçoit et traite le formulaire JSON d'inscription Client.
        - Valide les types, la complexité du mot de passe et l'unicité via RegisterSerializer.
        - En cas d'erreur d'unicité (email/téléphone déjà utilisé), renvoie HTTP 409 CONFLICT.
        - En cas d'erreur de syntaxe ou mot de passe faible, renvoie HTTP 400 BAD REQUEST.
        - En cas de succès, déclenche le service transactionnel atomique et renvoie HTTP 201 CREATED.
        """
        # Step 1 : Instanciation du serializer avec les données JSON transmises par Angular
        serializer = RegisterSerializer(data=request.data)

        # Step 2 : Validation des règles métier et vérification de la validité des champs
        if not serializer.is_valid():
            errors = serializer.errors

            # Analyser si l'échec de validation est dû à une tentative de doublon d'email ou de téléphone
            is_conflict = False
            for field in ['email', 'numero_telephone']:
                if field in errors:
                    for err in errors[field]:
                        if 'déjà' in str(err).lower() or 'already' in str(err).lower():
                            is_conflict = True
                            break

            # Utiliser HTTP 409 Conflict pour les doublons et HTTP 400 Bad Request pour les erreurs de format
            status_code = status.HTTP_409_CONFLICT if is_conflict else status.HTTP_400_BAD_REQUEST
            return Response({'errors': errors}, status=status_code)

        # Step 3 : Exécution du service métier transactionnel (Utilisateur + ProfilClient + Role CLIENT + OTP SMS)
        user = RegistrationService.register_client(serializer.validated_data)

        # Step 4 : Retour de la réponse HTTP 201 Created indiquant la nécessité de vérifier l'OTP SMS
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


class GoogleAuthView(APIView):
    """
    API de connexion Client via Google OAuth ID Token.
    POST /api/auth/google/
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        token = request.data.get('token')
        if not token:
            return Response({'errors': {'token': ['Le token Google est obligatoire.']}}, status=status.HTTP_400_BAD_REQUEST)

        try:
            auth_data = LoginService.authenticate_google(token)
            return Response(auth_data, status=status.HTTP_200_OK)
        except ValidationError as exc:
            return Response({'errors': exc.detail}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as exc:
            return Response({'errors': {'detail': str(exc)}}, status=status.HTTP_400_BAD_REQUEST)


