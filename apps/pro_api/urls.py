from django.urls import path
from .views import (
    RegisterRestaurantView,
    RegisterVendeurView,
    RegisterLivreurView,
    ProStatusView,
)
from .views_merchant import (
    MerchantProfileView,
    MerchantProductListView,
    MerchantProductDetailView,
    MerchantProductToggleView,
    MerchantStatsView,
    MerchantOrderListView,
    MerchantOrderDetailView,
    MerchantOrderStatusUpdateView,
    MerchantImageUploadView,
)

app_name = 'pro_api'

urlpatterns = [
    # Enregistrement & Statut Candidat PRO
    path('register/restaurant/', RegisterRestaurantView.as_view(), name='register_restaurant'),
    path('register/vendeur/', RegisterVendeurView.as_view(), name='register_vendeur'),
    path('register/livreur/', RegisterLivreurView.as_view(), name='register_livreur'),
    path('status/', ProStatusView.as_view(), name='pro_status'),

    # Espace Marchand PRO (Restaurant & Vendeur) - IsApprovedMerchant
    path('merchant/profile/', MerchantProfileView.as_view(), name='merchant_profile'),
    path('merchant/products/', MerchantProductListView.as_view(), name='merchant_products'),
    path('merchant/products/<int:pk>/', MerchantProductDetailView.as_view(), name='merchant_product_detail'),
    path('merchant/products/<int:pk>/toggle-disponibilite/', MerchantProductToggleView.as_view(), name='merchant_product_toggle'),
    path('merchant/upload-image/', MerchantImageUploadView.as_view(), name='merchant_upload_image'),
    path('merchant/stats/', MerchantStatsView.as_view(), name='merchant_stats'),

    # Commandes Marchand PRO
    path('merchant/orders/', MerchantOrderListView.as_view(), name='merchant_orders'),
    path('merchant/orders/<int:pk>/', MerchantOrderDetailView.as_view(), name='merchant_order_detail'),
    path('merchant/orders/<int:pk>/status/', MerchantOrderStatusUpdateView.as_view(), name='merchant_order_status_update'),
]


