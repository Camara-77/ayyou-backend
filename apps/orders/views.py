from rest_framework import status, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from django.core.exceptions import ValidationError

from apps.orders.models import Panier, PanierItem, Commande, AdresseLivraison
from apps.orders.services import CartService, OrderService
from apps.orders.serializers import (
    PanierSerializer, PanierItemSerializer, AddCartItemSerializer,
    UpdateCartItemSerializer, CheckoutSerializer, CommandeSerializer,
    AdresseLivraisonSerializer
)


class PanierView(APIView):
    """
    GET /api/orders/cart/ : Récupère le panier actif du Client connecté.
    DELETE /api/orders/cart/ : Vide intégralement le panier actif.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        panier = CartService.get_or_create_active_cart(request.user)
        serializer = PanierSerializer(panier)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def delete(self, request):
        CartService.clear_cart(request.user)
        panier = CartService.get_or_create_active_cart(request.user)
        serializer = PanierSerializer(panier)
        return Response(serializer.data, status=status.HTTP_200_OK)


class PanierItemListView(APIView):
    """
    POST /api/orders/cart/items/ : Ajoute un produit au panier actif.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = AddCartItemSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        try:
            item = CartService.add_item_to_cart(
                utilisateur=request.user,
                produit_id=data['produit'],
                quantite=data.get('quantite', 1),
                variante_id=data.get('variante'),
                option_ids=data.get('options', [])
            )
        except ValidationError as err:
            return Response(
                {'detail': err.message if hasattr(err, 'message') else str(err)},
                status=status.HTTP_400_BAD_REQUEST
            )

        panier = CartService.get_or_create_active_cart(request.user)
        return Response(PanierSerializer(panier).data, status=status.HTTP_201_CREATED)


class PanierItemDetailView(APIView):
    """
    PATCH /api/orders/cart/items/{id}/ : Modifie la quantité d'un article.
    DELETE /api/orders/cart/items/{id}/ : Supprime un article du panier.
    """
    permission_classes = [permissions.IsAuthenticated]

    def patch(self, request, pk):
        serializer = UpdateCartItemSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        quantite = serializer.validated_data['quantite']
        try:
            CartService.update_item_quantity(request.user, pk, quantite)
        except ValidationError as err:
            return Response(
                {'detail': err.message if hasattr(err, 'message') else str(err)},
                status=status.HTTP_400_BAD_REQUEST
            )

        panier = CartService.get_or_create_active_cart(request.user)
        return Response(PanierSerializer(panier).data, status=status.HTTP_200_OK)

    def delete(self, request, pk):
        try:
            CartService.remove_item(request.user, pk)
        except ValidationError as err:
            return Response(
                {'detail': err.message if hasattr(err, 'message') else str(err)},
                status=status.HTTP_400_BAD_REQUEST
            )

        panier = CartService.get_or_create_active_cart(request.user)
        return Response(PanierSerializer(panier).data, status=status.HTTP_200_OK)


class AdresseLivraisonListView(APIView):
    """
    GET /api/orders/addresses/ : Liste les adresses de livraison du Client.
    POST /api/orders/addresses/ : Crée une nouvelle adresse.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        adresses = AdresseLivraison.objects.filter(utilisateur=request.user)
        serializer = AdresseLivraisonSerializer(adresses, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = AdresseLivraisonSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        if serializer.validated_data.get('est_defaut', False):
            AdresseLivraison.objects.filter(utilisateur=request.user).update(est_defaut=False)

        adresse = serializer.save(utilisateur=request.user)
        return Response(AdresseLivraisonSerializer(adresse).data, status=status.HTTP_201_CREATED)


class AdresseLivraisonDetailView(APIView):
    """
    GET/PATCH/DELETE /api/orders/addresses/{id}/ : Gestion d'une adresse spécifique.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self, pk, user):
        try:
            return AdresseLivraison.objects.get(id=pk, utilisateur=user)
        except AdresseLivraison.DoesNotExist:
            return None

    def get(self, request, pk):
        adresse = self.get_object(pk, request.user)
        if not adresse:
            return Response({'detail': 'Adresse non trouvée.'}, status=status.HTTP_404_NOT_FOUND)
        return Response(AdresseLivraisonSerializer(adresse).data, status=status.HTTP_200_OK)

    def patch(self, request, pk):
        adresse = self.get_object(pk, request.user)
        if not adresse:
            return Response({'detail': 'Adresse non trouvée.'}, status=status.HTTP_404_NOT_FOUND)

        serializer = AdresseLivraisonSerializer(adresse, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        if serializer.validated_data.get('est_defaut', False):
            AdresseLivraison.objects.filter(utilisateur=request.user).exclude(id=pk).update(est_defaut=False)

        updated_adresse = serializer.save()
        return Response(AdresseLivraisonSerializer(updated_adresse).data, status=status.HTTP_200_OK)

    def delete(self, request, pk):
        adresse = self.get_object(pk, request.user)
        if not adresse:
            return Response({'detail': 'Adresse non trouvée.'}, status=status.HTTP_404_NOT_FOUND)
        adresse.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class AdresseLivraisonSetDefaultView(APIView):
    """
    POST /api/orders/addresses/{id}/set-default/ : Définit l'adresse comme adresse par défaut.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        try:
            adresse = AdresseLivraison.objects.get(id=pk, utilisateur=request.user)
        except AdresseLivraison.DoesNotExist:
            return Response({'detail': 'Adresse non trouvée.'}, status=status.HTTP_404_NOT_FOUND)

        AdresseLivraison.objects.filter(utilisateur=request.user).update(est_defaut=False)
        adresse.est_defaut = True
        adresse.save()
        return Response(AdresseLivraisonSerializer(adresse).data, status=status.HTTP_200_OK)


class CheckoutView(APIView):
    """
    POST /api/orders/checkout/ : Transforme le panier actif du Client en Commande globale + SousCommandes.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = CheckoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        destinataire_info = data.get('destinataire', {})

        try:
            commande = OrderService.checkout(
                utilisateur=request.user,
                adresse_livraison=data['adresse_livraison'],
                latitude_livraison=data.get('latitude_livraison'),
                longitude_livraison=data.get('longitude_livraison'),
                instructions_livraison=data.get('instructions_livraison', ''),
                nom_destinataire=destinataire_info.get('nom', ''),
                telephone_destinataire=destinataire_info.get('telephone', '')
            )
        except ValidationError as err:
            return Response(
                {'detail': err.message if hasattr(err, 'message') else str(err)},
                status=status.HTTP_400_BAD_REQUEST
            )

        return Response(CommandeSerializer(commande).data, status=status.HTTP_201_CREATED)


class CommandeListView(APIView):
    """
    GET /api/orders/ : Liste l'historique des commandes du Client connecté.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        commandes = Commande.objects.filter(utilisateur=request.user).prefetch_related(
            'sous_commandes', 'sous_commandes__etablissement', 'sous_commandes__lignes',
            'sous_commandes__lignes__variante_snapshot', 'sous_commandes__lignes__options_snapshot'
        )
        serializer = CommandeSerializer(commandes, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class CommandeDetailView(APIView):
    """
    GET /api/orders/{id}/ : Consultation détaillée d'une commande spécifique.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        try:
            commande = Commande.objects.prefetch_related(
                'sous_commandes', 'sous_commandes__etablissement', 'sous_commandes__lignes',
                'sous_commandes__lignes__variante_snapshot', 'sous_commandes__lignes__options_snapshot'
            ).get(id=pk, utilisateur=request.user)
        except Commande.DoesNotExist:
            return Response({'detail': 'Commande non trouvée.'}, status=status.HTTP_404_NOT_FOUND)

        serializer = CommandeSerializer(commande)
        return Response(serializer.data, status=status.HTTP_200_OK)
