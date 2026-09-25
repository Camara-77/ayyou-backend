from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.payments.views import (
    PaiementViewSet, FactureViewSet,
    InitiatePaydunyaPaiementView, PaydunyaIPNView,
    InitiatePayTechPaiementView, PayTechIPNView,
    PayTechSuccessView, PayTechCancelView
)

app_name = 'payments'

router = DefaultRouter()
router.register(r'transactions', PaiementViewSet, basename='paiement')
router.register(r'invoices', FactureViewSet, basename='facture')

urlpatterns = [
    path('initiate/', InitiatePaydunyaPaiementView.as_view(), name='initiate-paydunya'),
    path('ipn/', PaydunyaIPNView.as_view(), name='paydunya-ipn'),
    path('paytech/initiate/', InitiatePayTechPaiementView.as_view(), name='initiate-paytech'),
    path('paytech/ipn/', PayTechIPNView.as_view(), name='paytech-ipn'),
    path('paytech/success/', PayTechSuccessView.as_view(), name='paytech-success'),
    path('paytech/cancel/', PayTechCancelView.as_view(), name='paytech-cancel'),
    path('', include(router.urls)),
]

