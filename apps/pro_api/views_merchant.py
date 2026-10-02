from rest_framework import status, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.db.models import Q, Sum
from django.utils import timezone
from decimal import Decimal

from django.core.exceptions import ValidationError
from apps.catalog.models import Etablissement, Produit
from apps.catalog.services import CloudinaryFeedService

from apps.orders.models import SousCommande, Commande
from apps.deliveries.services import DeliveryService
from .permissions import IsApprovedMerchant
from .serializers_merchant import (
    MerchantEtablissementSerializer,
    MerchantProduitSerializer,
    MerchantSousCommandeSerializer
)


def get_merchant_etablissement(user) -> Etablissement:
    """
    Récupère l'établissement appartenant à l'utilisateur connecté.
    Priorise un établissement validé, sinon renvoie le premier établissement du marchand.
    """
    etab = Etablissement.objects.filter(proprietaire=user, statut_verification=Etablissement.STATUT_VALIDE).first()
    if not etab:
        etab = get_object_or_404(Etablissement, proprietaire=user)
    return etab


def is_subscription_active(etablissement: Etablissement, user=None) -> bool:
    """
    Vérifie si l'établissement possède un abonnement PRO actif et non expiré.
    Les comptes SuperAdmin sont exemptés.
    """
    if user and getattr(user, 'is_superuser', False):
        return True
    if not etablissement:
        return False
    if etablissement.statut_abonnement != Etablissement.STATUT_ABONNEMENT_ACTIF:
        return False
    if not etablissement.date_expiration_abonnement or etablissement.date_expiration_abonnement <= timezone.now():
        return False
    return True



class MerchantProfileView(APIView):
    """
    GET /api/pro/merchant/profile/
    PATCH /api/pro/merchant/profile/
    Permet au professionnel connecté de consulter et mettre à jour le profil de son propre établissement.
    """
    permission_classes = [IsAuthenticated, IsApprovedMerchant]

    def get(self, request):
        etablissement = get_merchant_etablissement(request.user)
        serializer = MerchantEtablissementSerializer(etablissement)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def patch(self, request):
        etablissement = get_merchant_etablissement(request.user)
        serializer = MerchantEtablissementSerializer(etablissement, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class MerchantProductListView(APIView):
    """
    GET /api/pro/merchant/products/
    POST /api/pro/merchant/products/
    Liste tous les produits appartenant à l'établissement du marchand connecté,
    ou crée un nouveau produit rattaché automatiquement à son établissement.
    """
    permission_classes = [IsAuthenticated, IsApprovedMerchant]

    def get(self, request):
        etablissement = get_merchant_etablissement(request.user)
        queryset = Produit.objects.filter(etablissement=etablissement).select_related('categorie').prefetch_related('variantes', 'options').order_by('-date_creation')

        # Filtres optionnels
        categorie = request.query_params.get('categorie')
        if categorie:
            if categorie.isdigit():
                queryset = queryset.filter(categorie_id=int(categorie))
            else:
                queryset = queryset.filter(categorie__slug=categorie)

        est_disponible = request.query_params.get('est_disponible')
        if est_disponible is not None:
            if est_disponible.lower() in ['true', '1']:
                queryset = queryset.filter(est_disponible=True)
            elif est_disponible.lower() in ['false', '0']:
                queryset = queryset.filter(est_disponible=False)

        search = request.query_params.get('search') or request.query_params.get('q')
        if search:
            queryset = queryset.filter(Q(nom__icontains=search) | Q(description__icontains=search))

        serializer = MerchantProduitSerializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        etablissement = get_merchant_etablissement(request.user)
        if not is_subscription_active(etablissement, request.user):
            return Response(
                {"detail": "Votre abonnement PRO est expiré. Veuillez le renouveler pour ajouter des produits au menu."},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = MerchantProduitSerializer(data=request.data)
        if serializer.is_valid():
            produit = serializer.save(etablissement=etablissement)
            return Response(MerchantProduitSerializer(produit).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class MerchantProductDetailView(APIView):
    """
    GET /api/pro/merchant/products/{id}/
    PUT/PATCH /api/pro/merchant/products/{id}/
    DELETE /api/pro/merchant/products/{id}/
    Gestion CRUD d'un produit appartenant au marchand connecté.
    Garantit l'isolation multi-tenant (renvoie 404 si le produit appartient à un autre marchand).
    """
    permission_classes = [IsAuthenticated, IsApprovedMerchant]

    def get_object(self, request, pk):
        etablissement = get_merchant_etablissement(request.user)
        return get_object_or_404(
            Produit.objects.select_related('categorie').prefetch_related('variantes', 'options'),
            pk=pk,
            etablissement=etablissement
        )

    def get(self, request, pk):
        produit = self.get_object(request, pk)
        serializer = MerchantProduitSerializer(produit)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def put(self, request, pk):
        produit = self.get_object(request, pk)
        if not is_subscription_active(produit.etablissement, request.user):
            return Response(
                {"detail": "Votre abonnement PRO est expiré. Veuillez le renouveler pour modifier votre menu."},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = MerchantProduitSerializer(produit, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def patch(self, request, pk):
        produit = self.get_object(request, pk)
        if not is_subscription_active(produit.etablissement, request.user):
            return Response(
                {"detail": "Votre abonnement PRO est expiré. Veuillez le renouveler pour modifier votre menu."},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = MerchantProduitSerializer(produit, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        produit = self.get_object(request, pk)
        if not is_subscription_active(produit.etablissement, request.user):
            return Response(
                {"detail": "Votre abonnement PRO est expiré. Veuillez le renouveler pour modifier votre menu."},
                status=status.HTTP_403_FORBIDDEN
            )

        produit.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class MerchantProductToggleView(APIView):
    """
    PATCH /api/pro/merchant/products/{id}/toggle-disponibilite/
    Bascule rapidement l'état est_disponible d'un plat du marchand.
    """
    permission_classes = [IsAuthenticated, IsApprovedMerchant]

    def patch(self, request, pk):
        etablissement = get_merchant_etablissement(request.user)
        if not is_subscription_active(etablissement, request.user):
            return Response(
                {"detail": "Votre abonnement PRO est expiré. Veuillez le renouveler pour modifier la disponibilité de vos produits."},
                status=status.HTTP_403_FORBIDDEN
            )

        produit = get_object_or_404(Produit, pk=pk, etablissement=etablissement)
        produit.est_disponible = not produit.est_disponible
        produit.save(update_fields=['est_disponible', 'date_modification'])


        return Response({
            'id': produit.id,
            'nom': produit.nom,
            'est_disponible': produit.est_disponible,
            'message': f"Le produit '{produit.nom}' est désormais {'disponible' if produit.est_disponible else 'indisponible'}."
        }, status=status.HTTP_200_OK)


class MerchantStatsView(APIView):
    """
    GET /api/pro/merchant/stats/
    Calcul en temps réel des indicateurs KPI du Dashboard professionnel pour l'établissement du marchand.
    """
    permission_classes = [IsAuthenticated, IsApprovedMerchant]

    def get(self, request):
        etablissement = get_merchant_etablissement(request.user)
        today = timezone.now().date()

        # Requetes sur les sous-commandes de l'établissement
        sous_commandes_today = SousCommande.objects.filter(
            etablissement=etablissement,
            date_creation__date=today
        )

        today_orders_count = sous_commandes_today.count()

        # Recette aujourd'hui (sous-commandes validées / payées / livrées)
        statuts_valides = [
            Commande.STATUT_PAYEE,
            Commande.STATUT_EN_PREPARATION,
            Commande.STATUT_PRETE,
            Commande.STATUT_EN_LIVRAISON,
            Commande.STATUT_LIVREE
        ]
        recette_aggreg = sous_commandes_today.filter(
            statut__in=statuts_valides
        ).aggregate(total_recette=Sum('total'))

        today_revenue_fcfa = float(recette_aggreg['total_recette'] or Decimal('0.00'))

        # Commandes prioritaires / urgentes (en attente de confirmation)
        urgent_orders_count = SousCommande.objects.filter(
            etablissement=etablissement,
            statut=Commande.STATUT_BROUILLON
        ).count()

        # Produits du catalogue
        produits_etab = Produit.objects.filter(etablissement=etablissement)
        active_products_count = produits_etab.filter(est_disponible=True).count()
        out_of_stock_products_count = produits_etab.filter(stock_ayyou_reserve__lte=0).count()

        return Response({
            'etablissement_id': etablissement.id,
            'etablissement_nom': etablissement.nom,
            'todayOrdersCount': today_orders_count,
            'todayRevenueFcfa': today_revenue_fcfa,
            'todayRevenue': today_revenue_fcfa,
            'pickupOrdersCount': 0,
            'urgentOrdersCount': urgent_orders_count,
            'activeProductsCount': active_products_count,
            'outOfStockProductsCount': out_of_stock_products_count,
            'rating': float(etablissement.note_moyenne),
            'ratingCount': etablissement.nombre_avis,
            'statut_etablissement': etablissement.statut,
        }, status=status.HTTP_200_OK)


class MerchantOrderListView(APIView):
    """
    GET /api/pro/merchant/orders/
    Liste les sous-commandes destinées à l'établissement du marchand connecté.
    Isolation multi-tenant : filtré strictly par etablissement__proprietaire = request.user.
    """
    permission_classes = [IsAuthenticated, IsApprovedMerchant]

    def get(self, request):
        etablissement = get_merchant_etablissement(request.user)
        queryset = SousCommande.objects.filter(
            etablissement=etablissement
        ).select_related(
            'commande', 'commande__utilisateur', 'etablissement'
        ).prefetch_related(
            'lignes', 'lignes__variante_snapshot', 'lignes__options_snapshot'
        ).order_by('-date_creation')

        # Filtres optionnels
        statut = request.query_params.get('statut')
        if statut:
            queryset = queryset.filter(statut=statut)

        search = request.query_params.get('search') or request.query_params.get('q')
        if search:
            queryset = queryset.filter(
                Q(commande__numero_commande__icontains=search) |
                Q(commande__nom_destinataire__icontains=search) |
                Q(commande__utilisateur__nom__icontains=search) |
                Q(commande__utilisateur__prenom__icontains=search)
            )

        date_str = request.query_params.get('date')
        if date_str == 'today':
            queryset = queryset.filter(date_creation__date=timezone.now().date())

        serializer = MerchantSousCommandeSerializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class MerchantOrderDetailView(APIView):
    """
    GET /api/pro/merchant/orders/{id}/
    Détail d'une sous-commande du marchand connecté.
    Isolation multi-tenant : renvoie 404 NOT FOUND si la commande n'appartient pas au marchand.
    """
    permission_classes = [IsAuthenticated, IsApprovedMerchant]

    def get(self, request, pk):
        etablissement = get_merchant_etablissement(request.user)
        sous_commande = get_object_or_404(
            SousCommande.objects.select_related(
                'commande', 'commande__utilisateur', 'etablissement'
            ).prefetch_related(
                'lignes', 'lignes__variante_snapshot', 'lignes__options_snapshot'
            ),
            pk=pk,
            etablissement=etablissement
        )
        serializer = MerchantSousCommandeSerializer(sous_commande)
        return Response(serializer.data, status=status.HTTP_200_OK)


class MerchantOrderStatusUpdateView(APIView):
    """
    PATCH /api/pro/merchant/orders/{id}/status/
    Permet au marchand d'accepter / mettre à jour le statut de préparation de sa sous-commande.
    Transitions autorisées marchand :
    - BROUILLON / EN_ATTENTE_PAIEMENT / PAYEE -> EN_PREPARATION ou ANNULEE
    - EN_PREPARATION -> PRETE ou ANNULEE
    """
    permission_classes = [IsAuthenticated, IsApprovedMerchant]

    def patch(self, request, pk):
        etablissement = get_merchant_etablissement(request.user)
        sous_commande = get_object_or_404(
            SousCommande.objects.select_related('commande'),
            pk=pk,
            etablissement=etablissement
        )

        nouveau_statut = request.data.get('statut')
        if not nouveau_statut:
            return Response(
                {"detail": "Le champ 'statut' est requis."},
                status=status.HTTP_400_BAD_REQUEST
            )

        statut_actuel = sous_commande.statut
        transitions_valides = {
            Commande.STATUT_PAYEE: [Commande.STATUT_EN_PREPARATION, Commande.STATUT_ANNULEE],
            Commande.STATUT_BROUILLON: [Commande.STATUT_EN_PREPARATION, Commande.STATUT_ANNULEE],
            Commande.STATUT_EN_ATTENTE_PAIEMENT: [Commande.STATUT_EN_PREPARATION, Commande.STATUT_ANNULEE],
            Commande.STATUT_EN_PREPARATION: [Commande.STATUT_PRETE, Commande.STATUT_ANNULEE],
        }

        autorises = transitions_valides.get(statut_actuel, [])
        if nouveau_statut not in autorises:
            return Response({
                "detail": f"Transition non autorisée du statut '{statut_actuel}' vers '{nouveau_statut}'.",
                "actuel": statut_actuel,
                "demande": nouveau_statut,
                "transitions_possibles": autorises
            }, status=status.HTTP_400_BAD_REQUEST)

        sous_commande.statut = nouveau_statut
        sous_commande.save(update_fields=['statut', 'date_modification'])

        # Synchronisation centralisée de la Commande principale et de la Livraison via DeliveryService
        DeliveryService.synchroniser_statuts_apres_sous_commande(sous_commande)

        serializer = MerchantSousCommandeSerializer(sous_commande)
        return Response(serializer.data, status=status.HTTP_200_OK)


class MerchantImageUploadView(APIView):
    """
    POST /api/pro/merchant/upload-image/
    Téléverse une photo de plat/produit vers Cloudinary (dossier ayyou/products/) pour l'établissement du marchand connecté.
    """
    permission_classes = [IsAuthenticated, IsApprovedMerchant]

    def post(self, request):
        etablissement = get_merchant_etablissement(request.user)
        if not is_subscription_active(etablissement, request.user):
            return Response(
                {"detail": "Votre abonnement PRO est expiré. Veuillez le renouveler pour téléverser des images."},
                status=status.HTTP_403_FORBIDDEN
            )

        image_file = request.FILES.get('image_file') or request.FILES.get('file') or request.FILES.get('image')


        if not image_file:
            return Response(
                {"detail": "Veuillez fournir un fichier image valide (image_file)."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            res = CloudinaryFeedService.upload_product_image(image_file)
            return Response({
                "image_url": res["image_url"],
                "cloudinary_public_id": res.get("cloudinary_public_id", ""),
                "etablissement_id": etablissement.id
            }, status=status.HTTP_201_CREATED)
        except ValidationError as e:
            return Response({"detail": str(e.message if hasattr(e, 'message') else e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"detail": f"Erreur lors du téléversement de l'image: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)


