from django.urls import path
from apps.orders.views import (
    PanierView, PanierItemListView, PanierItemDetailView,
    AdresseLivraisonListView, AdresseLivraisonDetailView, AdresseLivraisonSetDefaultView,
    CheckoutView, CommandeListView, CommandeDetailView, EstimateDeliveryView
)
from apps.orders.views_planning import (
    PlanningListCreateView, PlanningDetailView
)

app_name = 'orders'

urlpatterns = [
    # Panier Client
    path('cart/', PanierView.as_view(), name='cart'),
    path('cart/items/', PanierItemListView.as_view(), name='cart-items-list'),
    path('cart/items/<int:pk>/', PanierItemDetailView.as_view(), name='cart-item-detail'),

    # Adresses de livraison
    path('addresses/', AdresseLivraisonListView.as_view(), name='address-list'),
    path('addresses/<int:pk>/', AdresseLivraisonDetailView.as_view(), name='address-detail'),
    path('addresses/<int:pk>/set-default/', AdresseLivraisonSetDefaultView.as_view(), name='address-set-default'),

    # Planning Client
    path('planning/', PlanningListCreateView.as_view(), name='planning-list-create'),
    path('planning/<int:pk>/', PlanningDetailView.as_view(), name='planning-detail'),

    # Commandes, Checkout & Estimation
    path('estimate-delivery/', EstimateDeliveryView.as_view(), name='estimate-delivery'),
    path('checkout/', CheckoutView.as_view(), name='checkout'),
    path('', CommandeListView.as_view(), name='order-list'),
    path('<int:pk>/', CommandeDetailView.as_view(), name='order-detail'),
]
