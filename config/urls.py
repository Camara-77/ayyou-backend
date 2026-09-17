from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/auth/', include('apps.authentication.urls', namespace='authentication')),
    path('api/users/', include('apps.users.urls', namespace='users')),
    path('api/catalog/', include('apps.catalog.urls', namespace='catalog')),
    path('api/orders/', include('apps.orders.urls', namespace='orders')),
    path('api/payments/', include('apps.payments.urls', namespace='payments')),
    path('api/deliveries/', include('apps.deliveries.urls', namespace='deliveries')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
