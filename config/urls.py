from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

from apps.ai.views import AITranscribeView

urlpatterns = [
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
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
