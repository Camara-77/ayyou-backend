from rest_framework import serializers
from .models import AIConversation, AIMessage


class AIMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = AIMessage
        fields = [
            'id',
            'conversation',
            'role',
            'type_message',
            'content',
            'user_text',
            'image_url',
            'data_payload',
            'date_creation',
        ]
        read_only_fields = ['id', 'date_creation']


class AIConversationSerializer(serializers.ModelSerializer):
    messages = AIMessageSerializer(many=True, read_only=True)
    messages_count = serializers.IntegerField(source='messages.count', read_only=True)
    last_message = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = AIConversation
        fields = [
            'id',
            'titre',
            'context_data',
            'messages_count',
            'last_message',
            'messages',
            'date_creation',
            'date_modification',
        ]
        read_only_fields = ['id', 'date_creation', 'date_modification']

    def get_last_message(self, obj):
        last_msg = obj.messages.last()
        if last_msg:
            return {
                "id": last_msg.id,
                "role": last_msg.role,
                "content": last_msg.content or last_msg.user_text,
                "date_creation": last_msg.date_creation
            }
        return None
