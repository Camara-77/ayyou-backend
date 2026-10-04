from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    NotificationViewSet,
    VapidPublicKeyView,
    PushSubscribeView,
    PushUnsubscribeView,
    PushPreferencesView
)

app_name = 'notifications'

router = DefaultRouter()
router.register('', NotificationViewSet, basename='notification')

urlpatterns = [
    path('vapid-public-key/', VapidPublicKeyView.as_view(), name='vapid-public-key'),
    path('push-subscribe/', PushSubscribeView.as_view(), name='push-subscribe'),
    path('push-unsubscribe/', PushUnsubscribeView.as_view(), name='push-unsubscribe'),
    path('push-preferences/', PushPreferencesView.as_view(), name='push-preferences'),
    path('', include(router.urls)),
]
