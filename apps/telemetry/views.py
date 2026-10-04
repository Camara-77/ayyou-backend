import json
from rest_framework import permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
from .serializers import VideoEventLogSerializer, VideoEventBatchSerializer
from .models import VideoEventLog


class VideoEventCreateView(APIView):
    """
    Endpoint de collecte de la télémétrie des vidéos du feed.
    Supporte la réception d'un événement unique ou d'une liste d'événements (batch).
    Accessible à la fois aux utilisateurs connectés et aux visiteurs anonymes (AllowAny).
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        if isinstance(request.data, list):
            serializer = VideoEventLogSerializer(data=request.data, many=True, context={'request': request})
            if serializer.is_valid():
                serializer.save()
                return Response({'status': 'success', 'count': len(serializer.data)}, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        serializer = VideoEventLogSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class VideoEventBatchCreateView(APIView):
    """
    Endpoint d'envoi groupé (batch) d'événements de télémétrie.
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = VideoEventBatchSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response({'status': 'success', 'message': 'Événements enregistrés avec succès'}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


