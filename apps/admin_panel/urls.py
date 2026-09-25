from django.urls import path, include
from rest_framework.routers import DefaultRouter

from apps.admin_panel.views import (
    AdminDashboardView,
    AdminPendingActionsView,
    AdminUserViewSet,
    AdminBusinessViewSet,
    AdminDriverViewSet,
    AdminOrderViewSet,
    AdminDeliveryViewSet,
    AdminCatalogViewSet,
    AdminCategoryViewSet,
    AdminPaymentViewSet,
    AdminAuditLogViewSet,
)

app_name = 'admin_panel'

router = DefaultRouter()
router.register('users', AdminUserViewSet, basename='user')
router.register('businesses', AdminBusinessViewSet, basename='business')
router.register('drivers', AdminDriverViewSet, basename='driver')
router.register('orders', AdminOrderViewSet, basename='order')
router.register('deliveries', AdminDeliveryViewSet, basename='delivery')
router.register('catalog/products', AdminCatalogViewSet, basename='catalog_product')
router.register('catalog/categories', AdminCategoryViewSet, basename='catalog_category')
router.register('payments', AdminPaymentViewSet, basename='payment')
router.register('audit-logs', AdminAuditLogViewSet, basename='audit_log')

urlpatterns = [
    path('dashboard/', AdminDashboardView.as_view(), name='dashboard'),
    path('dashboard/pending-actions/', AdminPendingActionsView.as_view(), name='pending_actions'),
    path('', include(router.urls)),
]
