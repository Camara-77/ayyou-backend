from django.urls import path
from .views import (
    VideoEventCreateView,
    VideoEventBatchCreateView,
    RecommendationScoringSimulationView,
)

app_name = 'telemetry'

urlpatterns = [
    path('video-event/', VideoEventCreateView.as_view(), name='video-event-create'),
    path('video-event/batch/', VideoEventBatchCreateView.as_view(), name='video-event-batch-create'),
    path('scoring/simulate/', RecommendationScoringSimulationView.as_view(), name='scoring-simulate'),
]
