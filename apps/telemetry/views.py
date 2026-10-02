import json
from rest_framework import permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
from .serializers import VideoEventLogSerializer, VideoEventBatchSerializer
from .models import VideoEventLog
from apps.telemetry.ml.scoring import RecommendationScoringService


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


class RecommendationScoringSimulationView(APIView):
    """
    Endpoint de simulation HORS FEED permettant de tester le service de scoring LightGBM (V2/V3/Chronological).
    STRICTEMENT ISOLÉ DU FEED RÉEL EN PRODUCTION.
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        raw_data = request.data

        # Extraction robuste de publication_ids (dict, QueryDict, ou JSON str)
        publication_ids = []
        model_version = 'v2'

        if hasattr(raw_data, 'getlist') and raw_data.getlist('publication_ids'):
            publication_ids = raw_data.getlist('publication_ids')
            if hasattr(raw_data, 'get') and raw_data.get('model_version'):
                model_version = raw_data.get('model_version')
        elif isinstance(raw_data, dict):
            publication_ids = raw_data.get('publication_ids', [])
            model_version = raw_data.get('model_version', 'v2')
        elif isinstance(raw_data, str):
            try:
                parsed = json.loads(raw_data)
                if isinstance(parsed, dict):
                    publication_ids = parsed.get('publication_ids', [])
                    model_version = parsed.get('model_version', 'v2')
            except Exception:
                publication_ids = []

        if isinstance(publication_ids, (int, str)):
            publication_ids = [publication_ids]

        if not publication_ids or not isinstance(publication_ids, list):
            return Response(
                {'error': 'La liste publication_ids est requise et doit être une liste non vide.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        session_id = raw_data.get('session_id') if isinstance(raw_data, dict) else None
        user_id = request.user.id if (hasattr(request, 'user') and request.user.is_authenticated) else (raw_data.get('user_id') if isinstance(raw_data, dict) else None)

        try:
            mv_clean = str(model_version).lower().strip()
            if mv_clean == 'chronological':
                from apps.catalog.models import PublicationFeed
                pubs_map = {str(p.id): p for p in PublicationFeed.objects.filter(pk__in=publication_ids).select_related('produit', 'etablissement')}
                results = []
                for idx, pid in enumerate(publication_ids, start=1):
                    p_obj = pubs_map.get(str(pid))
                    dish_name = p_obj.produit.nom if (p_obj and p_obj.produit) else None
                    resto_name = p_obj.etablissement.nom if (p_obj and p_obj.etablissement) else None
                    dish_price = float(p_obj.produit.prix_base) if (p_obj and p_obj.produit) else 0.0
                    results.append({
                        'publication_id': str(pid),
                        'predicted_score': 0.0,
                        'dish_name': dish_name,
                        'resto_name': resto_name,
                        'dish_price': dish_price,
                        'rank': idx
                    })
                actual_model_version = 'chronological'
            else:
                results = RecommendationScoringService.score_candidates(
                    publication_ids=publication_ids,
                    user_id=user_id,
                    session_id=session_id,
                    model_version=mv_clean
                )
                actual_model_version = f"recommender_lgbm_{mv_clean}"

            return Response({
                'status': 'success',
                'model_version': actual_model_version,
                'candidates_count': len(results),
                'ranked_candidates': results
            }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({
                'error': f'Erreur lors du calcul du scoring : {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

