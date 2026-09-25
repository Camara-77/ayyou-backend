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
        """
        if getattr(self, 'swagger_fake_view', False):
            return Notification.objects.none()
        return NotificationService.get_notifications_utilisateur(self.request.user)

    @action(detail=False, methods=['get'], url_path='unread-count')
    def unread_count(self, request):
        """
        GET /api/notifications/unread-count/
        Retourne le nombre total de notifications non lues pour l'utilisateur connecté.
        """
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
