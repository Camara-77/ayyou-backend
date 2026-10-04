from django.urls import path
from .views import AIChatView, AITranscribeView
from .views_planning_ai import AIPlanningParseView, AIVisionAnalyzeView, AIConversationListView, AIConversationDetailView

app_name = 'ai'

urlpatterns = [
    path('chat/', AIChatView.as_view(), name='chat'),
    path('transcribe/', AITranscribeView.as_view(), name='transcribe'),
    path('planning-parse/', AIPlanningParseView.as_view(), name='planning-parse'),
    path('vision-analyze/', AIVisionAnalyzeView.as_view(), name='vision-analyze'),
    path('conversations/', AIConversationListView.as_view(), name='conversation-list'),
    path('conversations/<int:pk>/', AIConversationDetailView.as_view(), name='conversation-detail'),
]
