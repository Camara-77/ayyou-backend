from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

from apps.ai.views import AITranscribeView

from django.http import JsonResponse
from django.views.static import serve
from django.urls import re_path

def health_check(request):
    return JsonResponse({"status": "ok", "service": "ayyou-backend"})

urlpatterns = [
    path('api/health/', health_check, name='health_check'),
    path('admin/', admin.site.urls),
    path('api/auth/', include('apps.authentication.urls', namespace='authentication')),
    path('api/users/', include('apps.users.urls', namespace='users')),
    path('api/catalog/', include('apps.catalog.urls', namespace='catalog')),
    path('api/orders/', include('apps.orders.urls', namespace='orders')),
    path('api/payments/', include('apps.payments.urls', namespace='payments')),
    path('api/deliveries/', include('apps.deliveries.urls', namespace='deliveries')),
    path('api/admin/', include('apps.admin_panel.urls', namespace='admin_panel')),
    path('api/pro/', include('apps.pro_api.urls', namespace='pro_api')),
    path('api/notifications/', include('apps.notifications.urls', namespace='notifications')),
    path('api/ai/', include('apps.ai.urls', namespace='ai')),
    path('api/telemetry/', include('apps.telemetry.urls', namespace='telemetry')),
    path('api/search/voice/', AITranscribeView.as_view(), name='search_voice'),
    re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
    re_path(r'^static/(?P<path>.*)$', serve, {'document_root': settings.STATIC_ROOT}),
]
