from django.urls import path
from .views import (
    VideoEventCreateView,
    VideoEventBatchCreateView,
)

app_name = 'telemetry'

urlpatterns = [
    path('video-event/', VideoEventCreateView.as_view(), name='video-event-create'),
    path('video-event/batch/', VideoEventBatchCreateView.as_view(), name='video-event-batch-create'),
]
