from django.urls import path
from .views import (
    CategorieListView,
    EtablissementListView,
    EtablissementDetailView,
    ProduitListView,
    ProduitDetailView,
    PublicationFeedListView,
    PublicationFeedDetailView,
    LikeProduitView,
    LikeProduitDetailView,
    AbonnementListView,
    AbonnementDetailView
)

app_name = 'catalog'

urlpatterns = [
    # Catégories
    path('categories/', CategorieListView.as_view(), name='categorie-list'),

    # Établissements (Restaurants et Vendeurs)
    path('establishments/', EtablissementListView.as_view(), name='etablissement-list'),
    path('establishments/<int:pk>/', EtablissementDetailView.as_view(), name='etablissement-detail'),

    # Produits / Plats
    path('products/', ProduitListView.as_view(), name='produit-list'),
    path('products/<int:pk>/', ProduitDetailView.as_view(), name='produit-detail'),

    # Feed social
    path('feed/', PublicationFeedListView.as_view(), name='publication-feed-list'),
    path('feed/<int:pk>/', PublicationFeedDetailView.as_view(), name='publication-feed-detail'),

    # Likes client
    path('likes/', LikeProduitView.as_view(), name='like-list-create-delete'),
    path('likes/<int:pk>/', LikeProduitDetailView.as_view(), name='like-detail'),

    # Abonnements client
    path('subscriptions/', AbonnementListView.as_view(), name='subscription-list-create-delete'),
    path('subscriptions/<int:pk>/', AbonnementDetailView.as_view(), name='subscription-detail'),
]
