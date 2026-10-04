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


from .models import PushSubscription, PushNotificationPreference


class PushSubscriptionSerializer(serializers.ModelSerializer):
    """
    Sérialiseur pour enregistrer et gérer une souscription Web Push PWA (VAPID).
    """
    keys = serializers.DictField(write_only=True, required=False)

    class Meta:
        model = PushSubscription
        fields = ['id', 'endpoint', 'p256dh', 'auth', 'keys', 'user_agent', 'is_active', 'created_at']
        read_only_fields = ['id', 'is_active', 'created_at']

    def create(self, validated_data):
        keys = validated_data.pop('keys', {})
        if keys:
            validated_data['p256dh'] = keys.get('p256dh', '')
            validated_data['auth'] = keys.get('auth', '')
        return super().create(validated_data)


class PushNotificationPreferenceSerializer(serializers.ModelSerializer):
    """
    Sérialiseur pour la gestion des préférences de notifications Push utilisateur.
    """
    class Meta:
        model = PushNotificationPreference
        fields = ['push_rappels_planning', 'push_publications_video', 'updated_at']
        read_only_fields = ['updated_at']

