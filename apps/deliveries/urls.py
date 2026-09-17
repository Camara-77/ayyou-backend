from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.deliveries.views import LivraisonViewSet

app_name = 'deliveries'

router = DefaultRouter()
router.register(r'', LivraisonViewSet, basename='livraison')

urlpatterns = [
    path('', include(router.urls)),
]
