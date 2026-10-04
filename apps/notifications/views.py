from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from .models import Notification
from .serializers import NotificationSerializer
from .permissions import IsNotificationOwner
from .services import NotificationService


class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet REST DRF pour la gestion In-App des notifications utilisateur AYYOU.
    Sécurité : Strictement isolé à l'utilisateur connecté via QuerySet et permissions.
    """
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated, IsNotificationOwner]

    def get_queryset(self):
        """
        Garantit qu'un utilisateur ne peut accéder qu'à ses propres notifications.
        Exécute le traitement automatique des rappels de repas planifiés en temps réel.
        """
        if getattr(self, 'swagger_fake_view', False):
            return Notification.objects.none()
        if self.request.user and self.request.user.is_authenticated:
            NotificationService.traiter_rappels_repas_planifies(self.request.user)
        return NotificationService.get_notifications_utilisateur(self.request.user)

    @action(detail=False, methods=['get'], url_path='unread-count')
    def unread_count(self, request):
        """
        GET /api/notifications/unread-count/
        Retourne le nombre total de notifications non lues pour l'utilisateur connecté.
        """
        if request.user and request.user.is_authenticated:
            NotificationService.traiter_rappels_repas_planifies(request.user)
        count = NotificationService.get_nombre_non_lues(request.user)
        return Response({'unread_count': count}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post', 'patch'], url_path='read')
    def mark_as_read(self, request, pk=None):
        """
        POST/PATCH /api/notifications/{id}/read/
        Marque une notification spécifique comme lue.
        """
        notification = self.get_object()
        notification.marquer_comme_lu()
        serializer = self.get_serializer(notification)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='mark-as-read')
    def mark_as_read_alt(self, request, pk=None):
        """
        POST /api/notifications/{id}/mark-as-read/
        Alias pour marquer une notification comme lue.
        """
        return self.mark_as_read(request, pk)

    @action(detail=False, methods=['post'], url_path='mark-all-read')
    def mark_all_as_read(self, request):
        """
        POST /api/notifications/mark-all-read/
        Marque toutes les notifications non lues de l'utilisateur connecté comme lues.
        """
        updated_count = NotificationService.marquer_tout_comme_lu(request.user)
        return Response({
            'detail': f'{updated_count} notification(s) marquée(s) comme lue(s).',
            'updated_count': updated_count
        }, status=status.HTTP_200_OK)


from rest_framework.views import APIView
from .models import PushSubscription, PushNotificationPreference
from .serializers import PushSubscriptionSerializer, PushNotificationPreferenceSerializer
from .webpush_service import VAPID_PUBLIC_KEY


class VapidPublicKeyView(APIView):
    """
    GET /api/notifications/vapid-public-key/
    Retourne la clé publique VAPID pour l'abonnement PWA côté frontend.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({'public_key': VAPID_PUBLIC_KEY}, status=status.HTTP_200_OK)


class PushSubscribeView(APIView):
    """
    POST /api/notifications/push-subscribe/
    Enregistre ou met à jour une souscription Web Push VAPID pour l'utilisateur connecté.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        endpoint = request.data.get('endpoint')
        if not endpoint:
            return Response({'error': 'L\'endpoint Push est obligatoire.'}, status=status.HTTP_400_BAD_REQUEST)

        keys = request.data.get('keys', {})
        p256dh = request.data.get('p256dh') or keys.get('p256dh', '')
        auth = request.data.get('auth') or keys.get('auth', '')
        user_agent = request.META.get('HTTP_USER_AGENT', '')[:255]

        subscription, created = PushSubscription.objects.update_or_create(
            utilisateur=request.user,
            endpoint=endpoint,
            defaults={
                'p256dh': p256dh,
                'auth': auth,
                'user_agent': user_agent,
                'is_active': True
            }
        )

        serializer = PushSubscriptionSerializer(subscription)
        status_code = status.HTTP_201_CREATED if created else status.HTTP_200_OK
        return Response(serializer.data, status=status_code)


class PushUnsubscribeView(APIView):
    """
    POST /api/notifications/push-unsubscribe/
    Désactive ou supprime l'abonnement Web Push spécifié par son endpoint.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        endpoint = request.data.get('endpoint')
        if not endpoint:
            return Response({'error': 'L\'endpoint Push est obligatoire.'}, status=status.HTTP_400_BAD_REQUEST)

        updated_count = PushSubscription.objects.filter(
            utilisateur=request.user,
            endpoint=endpoint
        ).update(is_active=False)

        return Response({
            'detail': 'Abonnement Push désactivé avec succès.',
            'unsubscribed_count': updated_count
        }, status=status.HTTP_200_OK)


class PushPreferencesView(APIView):
    """
    GET / PATCH /api/notifications/push-preferences/
    Consulte ou met à jour les préférences de notifications Push [ON/OFF] de l'utilisateur.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        pref, _ = PushNotificationPreference.objects.get_or_create(utilisateur=request.user)
        serializer = PushNotificationPreferenceSerializer(pref)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def patch(self, request):
        pref, _ = PushNotificationPreference.objects.get_or_create(utilisateur=request.user)
        serializer = PushNotificationPreferenceSerializer(pref, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

