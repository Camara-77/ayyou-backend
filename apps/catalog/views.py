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
from .services import CloudinaryFeedService
from .search_engine import CatalogSearchEngine


class StandardCatalogPagination(PageNumberPagination):
    """
    Pagination standard pour la consultation des listes du catalogue AYYOU.
    """
    page_size = 50
    page_size_query_param = 'page_size'
    max_page_size = 200


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
    Masque automatiquement les établissements dont l'abonnement n'est pas ACTIF pour les clients public.
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        from django.utils import timezone
        queryset = Etablissement.objects.select_related('proprietaire').all().order_by('-date_creation')

        # Filtrage strict de visibilité publique par abonnement PRO
        if not (request.user.is_authenticated and request.user.is_superuser):
            queryset = queryset.filter(
                statut_abonnement=Etablissement.STATUT_ABONNEMENT_ACTIF,
                date_expiration_abonnement__gt=timezone.now()
            )

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

        # Recherche textuelle intelligente & tolérante
        search = request.query_params.get('search') or request.query_params.get('q') or request.query_params.get('nom')
        if search:
            queryset_list = CatalogSearchEngine.search_etablissements(queryset, search)
        else:
            queryset_list = list(queryset)

        paginator = StandardCatalogPagination()
        page = paginator.paginate_queryset(queryset_list, request, view=self)
        if page is not None:
            serializer = EtablissementSerializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)

        serializer = EtablissementSerializer(queryset_list, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class EtablissementDetailView(APIView):
    """
    GET /api/catalog/establishments/{id}/
    Détail public d'un établissement.
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request, pk):
        from django.utils import timezone
        from django.http import Http404

        etablissement = get_object_or_404(Etablissement.objects.select_related('proprietaire'), pk=pk)

        # Vérification d'accès : SuperAdmin ou Propriétaire peuvent consulter même si inactif
        if not (request.user.is_authenticated and (request.user.is_superuser or etablissement.proprietaire == request.user)):
            now = timezone.now()
            if etablissement.statut_abonnement != Etablissement.STATUT_ABONNEMENT_ACTIF or not etablissement.date_expiration_abonnement or etablissement.date_expiration_abonnement <= now:
                raise Http404("Établissement non disponible ou abonnement expiré.")

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
        from django.utils import timezone
        queryset = Produit.objects.select_related('etablissement', 'categorie').all().order_by('-date_creation')

        # Filtrage strict de visibilité publique par abonnement PRO de l'établissement
        if not (request.user.is_authenticated and request.user.is_superuser):
            queryset = queryset.filter(
                etablissement__statut_abonnement=Etablissement.STATUT_ABONNEMENT_ACTIF,
                etablissement__date_expiration_abonnement__gt=timezone.now()
            )

        # Filtre par catégorie (ID, Slug ou Nom)
        categorie = request.query_params.get('categorie')
        if categorie:
            if categorie.isdigit():
                queryset = queryset.filter(Q(categorie_id=int(categorie)) | Q(categorie__nom__icontains=categorie))
            else:
                queryset = queryset.filter(Q(categorie__slug=categorie) | Q(categorie__nom__icontains=categorie))

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

        # Recherche textuelle intelligente & tolérante
        search = request.query_params.get('search') or request.query_params.get('q') or request.query_params.get('nom')
        if search:
            queryset_list = CatalogSearchEngine.search_produits(queryset, search)
        else:
            queryset_list = list(queryset)

        paginator = StandardCatalogPagination()
        page = paginator.paginate_queryset(queryset_list, request, view=self)
        if page is not None:
            serializer = ProduitListSerializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)

        serializer = ProduitListSerializer(queryset_list, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class ProduitDetailView(APIView):
    """
    GET /api/catalog/products/{id}/
    Fiche détail d'un plat/produit avec ses variantes, sauces et suppléments.
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request, pk):
        from django.utils import timezone
        from django.http import Http404

        queryset = Produit.objects.select_related('etablissement', 'categorie').prefetch_related('variantes', 'options')
        produit = get_object_or_404(queryset, pk=pk)

        # Vérification d'accès : SuperAdmin ou Propriétaire de l'établissement
        if not (request.user.is_authenticated and (request.user.is_superuser or produit.etablissement.proprietaire == request.user)):
            now = timezone.now()
            if produit.etablissement.statut_abonnement != Etablissement.STATUT_ABONNEMENT_ACTIF or not produit.etablissement.date_expiration_abonnement or produit.etablissement.date_expiration_abonnement <= now:
                raise Http404("Produit non disponible ou abonnement établissement expiré.")

        serializer = ProduitDetailSerializer(produit)
        return Response(serializer.data, status=status.HTTP_200_OK)


class PublicationFeedListView(APIView):
    """
    GET /api/catalog/feed/
    Liste des publications photo/vidéo pour le Feed style TikTok.
    POST /api/catalog/feed/
    Publication d'une vidéo/photo dans le Feed AYYOU par un RESTAURANT ou VENDEUR.
    """
    permission_classes = [permissions.AllowAny]

    def get_permissions(self):
        if self.request.method == 'POST':
            return [permissions.IsAuthenticated()]
        return [permissions.AllowAny()]

    def get(self, request):
        from django.utils import timezone
        queryset = PublicationFeed.objects.select_related(
            'etablissement', 'produit', 'produit__etablissement', 'produit__categorie'
        ).all().order_by('-date_publication')

        # Filtrage strict de visibilité publique par abonnement PRO de l'établissement
        if not (request.user.is_authenticated and request.user.is_superuser):
            queryset = queryset.filter(
                etablissement__statut_abonnement=Etablissement.STATUT_ABONNEMENT_ACTIF,
                etablissement__date_expiration_abonnement__gt=timezone.now()
            )

        # Filtre par établissement
        etablissement = request.query_params.get('etablissement') or request.query_params.get('etablissement_id')
        if etablissement and etablissement.isdigit():
            queryset = queryset.filter(etablissement_id=int(etablissement))

        paginator = StandardCatalogPagination()
        page = paginator.paginate_queryset(queryset, request, view=self)

        candidate_pubs = list(page) if page is not None else list(queryset)
        session_id = request.query_params.get('session_id') or request.headers.get('X-Session-ID')

        # 1. Expérimentation contrôlée (A/B Testing V3 vs Chronologique)
        final_pubs = candidate_pubs
        if candidate_pubs:
            try:
                from apps.telemetry.ml.experiment_service import RecommendationExperimentService
                final_pubs = RecommendationExperimentService.process_feed_candidates(
                    candidate_pubs=candidate_pubs,
                    user=request.user,
                    session_id=session_id
                )
            except Exception:
                final_pubs = candidate_pubs

        # 2. Exécution parallèle du Shadow Mode si activé dans les settings
        if candidate_pubs:
            try:
                from apps.telemetry.ml.shadow_service import RecommendationShadowService
                candidate_ids = [p.id for p in candidate_pubs]
                RecommendationShadowService.run_shadow_scoring(
                    publication_ids=candidate_ids,
                    user=request.user,
                    session_id=session_id
                )
            except Exception:
                pass

        if page is not None:
            serializer = PublicationFeedSerializer(final_pubs, many=True, context={'request': request})
            return paginator.get_paginated_response(serializer.data)

        serializer = PublicationFeedSerializer(final_pubs, many=True, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)


    def post(self, request):
        # Chercher l'établissement appartenant à l'utilisateur connecté (RESTAURANT ou VENDEUR)
        etablissement = Etablissement.objects.filter(proprietaire=request.user).first()
        if not etablissement:
            return Response(
                {"detail": _("Seul un établissement professionnel actif (Restaurant ou Vendeur) peut publier des vidéos.")},
                status=status.HTTP_403_FORBIDDEN
            )

        from django.utils import timezone
        if not request.user.is_superuser:
            if etablissement.statut_abonnement != Etablissement.STATUT_ABONNEMENT_ACTIF or not etablissement.date_expiration_abonnement or etablissement.date_expiration_abonnement <= timezone.now():
                return Response(
                    {"detail": _("Votre abonnement PRO est expiré. Veuillez le renouveler pour pouvoir publier des vidéos.")},
                    status=status.HTTP_403_FORBIDDEN
                )


        video_file = request.FILES.get('video_file') or request.FILES.get('file') or request.FILES.get('media')
        media_url = request.data.get('media_url')
        produit_id = request.data.get('produit_id') or request.data.get('produit')
        duree_secondes = request.data.get('duree_secondes') or request.data.get('duration')

        if duree_secondes:
            try:
                duree_secondes = int(duree_secondes)
            except (ValueError, TypeError):
                duree_secondes = None

        if duree_secondes and duree_secondes > 180:
            return Response(
                {"detail": _("La durée maximale de la vidéo est de 3 minutes (180 secondes).")},
                status=status.HTTP_400_BAD_REQUEST
            )

        upload_data = {}
        if video_file:
            try:
                upload_data = CloudinaryFeedService.upload_feed_video(video_file, duree_secondes=duree_secondes)
            except Exception as exc:
                return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        elif media_url:
            upload_data = {
                "media_url": media_url,
                "cloudinary_public_id": request.data.get('cloudinary_public_id', ''),
                "duree_video": "2:00"
            }
        else:
            return Response(
                {"detail": _("Veuillez fournir un fichier vidéo (video_file) ou une URL de média.")},
                status=status.HTTP_400_BAD_REQUEST
            )

        produit = None
        if produit_id:
            produit = Produit.objects.filter(pk=produit_id, etablissement=etablissement).first()

        publication = PublicationFeed.objects.create(
            etablissement=etablissement,
            produit=produit,
            media_url=upload_data["media_url"],
            cloudinary_public_id=upload_data.get("cloudinary_public_id", ""),
            type_media=PublicationFeed.TYPE_MEDIA_VIDEO,
            duree_video=upload_data.get("duree_video", "2:00"),
            max_duree_secondes=180
        )

        serializer = PublicationFeedSerializer(publication, context={'request': request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class PublicationFeedDetailView(APIView):
    """
    GET /api/catalog/feed/{id}/
    Récupère une publication vidéo spécifique du Feed.
    DELETE /api/catalog/feed/{id}/
    Supprime une publication vidéo du Feed et retire le fichier média sur Cloudinary.
    """
    def get_permissions(self):
        if self.request.method == 'GET':
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]

    def get(self, request, pk):
        from django.utils import timezone
        publication = get_object_or_404(
            PublicationFeed.objects.select_related('etablissement', 'produit'),
            pk=pk
        )

        # Vérification d'accès public : l'établissement doit avoir un abonnement actif sauf si superuser
        if not (request.user.is_authenticated and request.user.is_superuser):
            etab = publication.etablissement
            now = timezone.now()
            if etab.statut_abonnement != Etablissement.STATUT_ABONNEMENT_ACTIF or not etab.date_expiration_abonnement or etab.date_expiration_abonnement <= now:
                return Response(
                    {"detail": _("Cette vidéo n'est plus disponible.")},
                    status=status.HTTP_404_NOT_FOUND
                )

        serializer = PublicationFeedSerializer(publication, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    def delete(self, request, pk):
        publication = get_object_or_404(PublicationFeed.objects.select_related('etablissement'), pk=pk)

        # Vérifier la propriété de l'établissement
        if publication.etablissement.proprietaire != request.user:
            return Response(
                {"detail": _("Vous n'avez pas la permission de supprimer cette publication.")},
                status=status.HTTP_403_FORBIDDEN
            )

        # Supprimer le média de Cloudinary s'il possède un public_id
        if publication.cloudinary_public_id:
            CloudinaryFeedService.delete_feed_video(publication.cloudinary_public_id)

        publication.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class LikeProduitView(APIView):
    """
    GET /api/catalog/likes/
    POST /api/catalog/likes/
    DELETE /api/catalog/likes/
    Enregistrer, consulter ou retirer un Like client sur un produit ou une publication.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        likes = LikeProduit.objects.filter(utilisateur=request.user).select_related(
            'produit', 'produit__etablissement', 'produit__categorie',
            'publication', 'publication__etablissement', 'publication__produit'
        ).order_by('-date_creation')
        serializer = LikeProduitSerializer(likes, many=True, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        data = request.data.copy() if hasattr(request.data, 'copy') else dict(request.data)
        if 'publication_feed' in data and 'publication' not in data:
            data['publication'] = data['publication_feed']

        serializer = LikeProduitSerializer(data=data, context={'request': request})
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
        publication_id = (
            request.data.get('publication') or
            request.data.get('publication_feed') or
            request.query_params.get('publication') or
            request.query_params.get('publication_feed')
        )

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
