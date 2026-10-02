from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.payments.views import (
    PaiementViewSet, FactureViewSet,
    InitiatePaydunyaPaiementView, PaydunyaIPNView,
    InitiatePayTechPaiementView, PayTechIPNView,
    PayTechSuccessView, PayTechCancelView, PayTechConfirmFallbackView,
    InitiatePayTechSubscriptionView, SubscriptionStatusView,
    SubscriptionHistoryView, FactureAbonnementPdfView
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
    path('paytech/confirm-fallback/', PayTechConfirmFallbackView.as_view(), name='paytech-confirm-fallback'),
    
    # Endpoints Abonnement PRO
    path('subscription/initiate/', InitiatePayTechSubscriptionView.as_view(), name='subscription-initiate'),
    path('subscription/status/', SubscriptionStatusView.as_view(), name='subscription-status'),
    path('subscription/history/', SubscriptionHistoryView.as_view(), name='subscription-history'),
    path('subscription/invoices/<int:pk>/pdf/', FactureAbonnementPdfView.as_view(), name='subscription-invoice-pdf'),

    path('', include(router.urls)),
]


