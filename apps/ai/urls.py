from django.urls import path
from .views import AIChatView, AITranscribeView

app_name = 'ai'

urlpatterns = [
    path('chat/', AIChatView.as_view(), name='chat'),
    path('transcribe/', AITranscribeView.as_view(), name='transcribe'),
]
