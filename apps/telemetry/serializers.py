from rest_framework import serializers
from .models import VideoEventLog
from apps.catalog.models import PublicationFeed


class VideoEventLogSerializer(serializers.ModelSerializer):
    publication_id = serializers.PrimaryKeyRelatedField(
        queryset=PublicationFeed.objects.all(),
        source='publication',
        write_only=True
    )

    class Meta:
        model = VideoEventLog
        fields = [
            'id',
            'publication_id',
            'session_id',
            'event_type',
            'watch_time_seconds',
            'video_duration_seconds',
            'progress_percent',
            'feed_position',
            'metadata',
            'created_at',
        ]
        read_only_fields = ['id', 'created_at']

    def create(self, validated_data):
        request = self.context.get('request')
        if request and hasattr(request, 'user') and request.user.is_authenticated:
            validated_data['utilisateur'] = request.user
        return super().create(validated_data)


class VideoEventBatchSerializer(serializers.Serializer):
    events = VideoEventLogSerializer(many=True)

    def create(self, validated_data):
        request = self.context.get('request')
        user = request.user if (request and hasattr(request, 'user') and request.user.is_authenticated) else None
        
        event_logs = []
        for event_data in validated_data['events']:
            if user:
                event_data['utilisateur'] = user
            event_logs.append(VideoEventLog(**event_data))
        
        return VideoEventLog.objects.bulk_create(event_logs)
