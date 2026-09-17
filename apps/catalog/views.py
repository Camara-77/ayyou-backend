from rest_framework import status, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django.shortcuts import get_object_or_404
from django.db.models import Q, F
from django.utils.translation import gettext_lazy as _

from .models import (
    Categorie,
    Etablissement,
    Produit,
    PublicationFeed,
    LikeProduit
)
from .serializers import (
    CategorieSerializer,
    EtablissementSerializer,
    ProduitListSerializer,
    ProduitDetailSerializer,
    PublicationFeedSerializer,
    LikeProduitSerializer
)


class StandardCatalogPagination(PageNumberPagination):
    """
    Pagination standard pour la consultation des listes du catalogue AYYOU.
    """
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100


class CategorieListView(APIView):
    """
    GET /api/catalog/categories/
    Liste les catégories actives disponibles pour le Client.
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        categories = Categorie.objects.filter(est_active=True).order_by('ordre', 'nom')
        serializer = CategorieSerializer(categories, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class EtablissementListView(APIView):
    """
    GET /api/catalog/establishments/
    Liste les établissements (Restaurants et Vendeurs à domicile) avec filtres.
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        queryset = Etablissement.objects.select_related('proprietaire').all().order_by('-date_creation')

        # Filtre type d'établissement (RESTAURANT / VENDEUR)
        type_etablissement = request.query_params.get('type_etablissement')
        if type_etablissement:
            queryset = queryset.filter(type_etablissement=type_etablissement.upper())

        # Filtre statut (open / closed)
        statut = request.query_params.get('statut')
        if statut:
            queryset = queryset.filter(statut=statut)

        # Filtre spécialité
        specialite = request.query_params.get('specialite')
        if specialite:
            queryset = queryset.filter(specialite__icontains=specialite)

        # Recherche textuelle par nom / adresse
        search = request.query_params.get('search') or request.query_params.get('q') or request.query_params.get('nom')
        if search:
            queryset = queryset.filter(
                Q(nom__icontains=search) | Q(adresse__icontains=search) | Q(specialite__icontains=search)
            )

        paginator = StandardCatalogPagination()
        page = paginator.paginate_queryset(queryset, request, view=self)
        if page is not None:
            serializer = EtablissementSerializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)

        serializer = EtablissementSerializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class EtablissementDetailView(APIView):
    """
    GET /api/catalog/establishments/{id}/
    Détail public d'un établissement.
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request, pk):
        etablissement = get_object_or_404(Etablissement.objects.select_related('proprietaire'), pk=pk)
        serializer = EtablissementSerializer(etablissement)
        return Response(serializer.data, status=status.HTTP_200_OK)


class ProduitListView(APIView):
    """
    GET /api/catalog/products/
    Liste les plats et produits du catalogue AYYOU.
    Masque impérativement les champs de stock vendeur.
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        queryset = Produit.objects.select_related('etablissement', 'categorie').all().order_by('-date_creation')

        # Filtre par catégorie (ID ou Slug)
        categorie = request.query_params.get('categorie')
        if categorie:
            if categorie.isdigit():
                queryset = queryset.filter(categorie_id=int(categorie))
            else:
                queryset = queryset.filter(categorie__slug=categorie)

        # Filtre par établissement
        etablissement = request.query_params.get('etablissement')
        if etablissement and etablissement.isdigit():
            queryset = queryset.filter(etablissement_id=int(etablissement))

        # Filtre par disponibilité
        est_disponible = request.query_params.get('est_disponible')
        if est_disponible is not None:
            if est_disponible.lower() in ['true', '1']:
                queryset = queryset.filter(est_disponible=True)
            elif est_disponible.lower() in ['false', '0']:
                queryset = queryset.filter(est_disponible=False)

        # Recherche textuelle par nom / description / tags
        search = request.query_params.get('search') or request.query_params.get('q') or request.query_params.get('nom')
        if search:
            queryset = queryset.filter(
                Q(nom__icontains=search) | Q(description__icontains=search)
            )

        paginator = StandardCatalogPagination()
        page = paginator.paginate_queryset(queryset, request, view=self)
        if page is not None:
            serializer = ProduitListSerializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)

        serializer = ProduitListSerializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class ProduitDetailView(APIView):
    """
    GET /api/catalog/products/{id}/
    Fiche détail d'un plat/produit avec ses variantes, sauces et suppléments.
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request, pk):
        queryset = Produit.objects.select_related('etablissement', 'categorie').prefetch_related('variantes', 'options')
        produit = get_object_or_404(queryset, pk=pk)
        serializer = ProduitDetailSerializer(produit)
        return Response(serializer.data, status=status.HTTP_200_OK)


class PublicationFeedListView(APIView):
    """
    GET /api/catalog/feed/
    Liste des publications photo/vidéo pour le Feed style TikTok.
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        queryset = PublicationFeed.objects.select_related(
            'etablissement', 'produit', 'produit__etablissement', 'produit__categorie'
        ).all().order_by('-date_publication')

        paginator = StandardCatalogPagination()
        page = paginator.paginate_queryset(queryset, request, view=self)
        if page is not None:
            serializer = PublicationFeedSerializer(page, many=True, context={'request': request})
            return paginator.get_paginated_response(serializer.data)

        serializer = PublicationFeedSerializer(queryset, many=True, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)


class LikeProduitView(APIView):
    """
    POST /api/catalog/likes/
    DELETE /api/catalog/likes/
    Enregistrer ou retirer un Like client sur un produit ou une publication.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = LikeProduitSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            like = serializer.save(utilisateur=request.user)
            # Incrémenter atomiquement le compteur de likes
            if like.produit:
                Produit.objects.filter(pk=like.produit.pk).update(nombre_likes=F('nombre_likes') + 1)
            elif like.publication:
                PublicationFeed.objects.filter(pk=like.publication.pk).update(nombre_likes=F('nombre_likes') + 1)

            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request):
        produit_id = request.data.get('produit') or request.query_params.get('produit')
        publication_id = request.data.get('publication') or request.query_params.get('publication')

        if not produit_id and not publication_id:
            return Response(
                {"detail": _("Veuillez préciser le paramètre 'produit' ou 'publication' à unliker.")},
                status=status.HTTP_400_BAD_REQUEST
            )

        like = None
        if produit_id:
            like = LikeProduit.objects.filter(utilisateur=request.user, produit_id=produit_id).first()
        elif publication_id:
            like = LikeProduit.objects.filter(utilisateur=request.user, publication_id=publication_id).first()

        if not like:
            return Response({"detail": _("Like introuvable.")}, status=status.HTTP_404_NOT_FOUND)

        # Décrémenter atomiquement le compteur
        if like.produit:
            Produit.objects.filter(pk=like.produit.pk, nombre_likes__gt=0).update(nombre_likes=F('nombre_likes') - 1)
        elif like.publication:
            PublicationFeed.objects.filter(pk=like.publication.pk, nombre_likes__gt=0).update(nombre_likes=F('nombre_likes') - 1)

        like.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class LikeProduitDetailView(APIView):
    """
    DELETE /api/catalog/likes/{id}/
    Suppression d'un Like direct par son identifiant ID.
    """
    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request, pk):
        like = get_object_or_404(LikeProduit, pk=pk)

        if like.utilisateur != request.user:
            return Response(
                {"detail": _("Vous n'avez pas la permission de supprimer ce Like.")},
                status=status.HTTP_403_FORBIDDEN
            )

        if like.produit:
            Produit.objects.filter(pk=like.produit.pk, nombre_likes__gt=0).update(nombre_likes=F('nombre_likes') - 1)
        elif like.publication:
            PublicationFeed.objects.filter(pk=like.publication.pk, nombre_likes__gt=0).update(nombre_likes=F('nombre_likes') - 1)

        like.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
