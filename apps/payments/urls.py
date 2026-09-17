from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.payments.views import PaiementViewSet, FactureViewSet

app_name = 'payments'

router = DefaultRouter()
router.register(r'transactions', PaiementViewSet, basename='paiement')
router.register(r'invoices', FactureViewSet, basename='facture')

urlpatterns = [
    path('', include(router.urls)),
]
