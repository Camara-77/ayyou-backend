from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions, parsers
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.exceptions import AuthenticationFailed
from .services import AIService
from .transcription import TranscriptionService


class SafeJWTAuthentication(JWTAuthentication):
    """
    Classe d'authentification JWT sécurisée pour les endpoints publics IA.
    Si le token fourni est invalide ou correspond à un compte supprimé,
    l'authentification retourne None (mode Invité) au lieu de rejeter la requête avec une 401.
    """
    def authenticate(self, request):
        try:
            return super().authenticate(request)
        except AuthenticationFailed:
            return None


class AIChatView(APIView):
    """
    POST /api/ai/chat/
    Endpoint de discussion avec le Conseiller Gastronomique AYYOU Dakar.
    Accessible aux clients connectés et aux visiteurs invités (AllowAny).
    """
    authentication_classes = [SafeJWTAuthentication]
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        message = request.data.get('message', '').strip()
        context = request.data.get('context', {})
        history = request.data.get('history', [])

        if not message:
            return Response(
                {"detail": "Le champ 'message' est requis."},
                status=status.HTTP_400_BAD_REQUEST
            )

        user_name = "Client"
        if request.user and request.user.is_authenticated:
            user_name = getattr(request.user, 'prenom', None) or getattr(request.user, 'nom', None) or "Client"

        response_data = AIService.process_chat_message(
            message=message,
            user_name=user_name,
            context=context,
            history=history
        )

        return Response(response_data, status=status.HTTP_200_OK)


class AITranscribeView(APIView):
    """
    POST /api/ai/transcribe/
    Endpoint de transcription vocale (Audio -> Texte via Whisper).
    Accepte multipart/form-data avec le champ 'audio'.
    Accessible aux clients connectés et invités (AllowAny).
    """
    authentication_classes = [SafeJWTAuthentication]
    permission_classes = [permissions.AllowAny]
    parser_classes = [parsers.MultiPartParser, parsers.FormParser]

    def post(self, request):
        audio_file = request.FILES.get('audio')
        if not audio_file:
            return Response(
                {"status": "error", "message": "Aucun fichier audio n'a été reçu."},
                status=status.HTTP_200_OK
            )

        result = TranscriptionService.transcribe(audio_file)
        return Response(result, status=status.HTTP_200_OK)
