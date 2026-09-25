from rest_framework import serializers
from .models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    """
    SÉRIALISEUR REST DRF pour le modèle Notification AYYOU.
    Expose les détails de la notification et ses traductions lisibles.
    """
    type_notification_display = serializers.CharField(source='get_type_notification_display', read_only=True)
    canal_display = serializers.CharField(source='get_canal_display', read_only=True)
    statut_display = serializers.CharField(source='get_statut_display', read_only=True)

    class Meta:
        model = Notification
        fields = [
            'id',
            'type_notification',
            'type_notification_display',
            'canal',
            'canal_display',
            'titre',
            'message',
            'statut',
            'statut_display',
            'est_lu',
            'date_lecture',
            'reference_type',
            'reference_id',
            'metadata',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id',
            'type_notification',
            'type_notification_display',
            'canal',
            'canal_display',
            'titre',
            'message',
            'statut',
            'statut_display',
            'est_lu',
            'date_lecture',
            'reference_type',
            'reference_id',
            'metadata',
            'created_at',
            'updated_at',
        ]
