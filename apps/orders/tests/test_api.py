from rest_framework.test import APITestCase
from rest_framework import status
from decimal import Decimal

from apps.users.models import Utilisateur, ProfilClient
from apps.catalog.models import Categorie, Etablissement, Produit, VarianteProduit, OptionProduit
from apps.orders.models import (
    Panier, PanierItem, Commande, SousCommande,
    LigneCommande, LigneCommandeVariante, LigneCommandeOption, AdresseLivraison
)


class CartAndOrderAPITestCase(APITestCase):

    def setUp(self):
        # Client 1
        self.client_user = Utilisateur.objects.create_user(
            email='moussa.client@ayyou.sn',
            numero_telephone='+221770000001',
            password='Password123!',
            prenom='Moussa',
            nom='Diop'
        )
        self.client_profile = ProfilClient.objects.create(
            utilisateur=self.client_user,
            adresse_principale='Plateau, Dakar'
        )

        # Client 2 (Awa)
        self.other_user = Utilisateur.objects.create_user(
            email='awa.client@ayyou.sn',
            numero_telephone='+221770000002',
            password='Password123!',
            prenom='Awa',
            nom='Ndiaye'
        )
        self.other_profile = ProfilClient.objects.create(
            utilisateur=self.other_user,
            adresse_principale='Almadies, Dakar'
        )

        # Vendor
        self.vendor_user = Utilisateur.objects.create_user(
            email='vendor@ayyou.sn',
            numero_telephone='+221770000003',
            password='Password123!',
            prenom='Modou',
            nom='Sall'
        )

        # Category
        self.category = Categorie.objects.create(
            slug='plats-nationaux',
            nom='Plats Nationaux',
            ordre=1
        )

        # Establishment A (Restaurant)
        self.etablissement_a = Etablissement.objects.create(
            nom='Chez Loutcha',
            type_etablissement=Etablissement.TYPE_RESTAURANT,
            proprietaire=self.vendor_user,
            statut=Etablissement.STATUT_OUVERT,
            adresse='Plateau, Dakar'
        )

        # Establishment B (Vendor)
        self.etablissement_b = Etablissement.objects.create(
            nom='Pâtisserie & Brunch Dakar',
            type_etablissement=Etablissement.TYPE_VENDEUR,
            proprietaire=self.vendor_user,
            statut=Etablissement.STATUT_OUVERT,
            adresse='Ngor, Dakar'
        )

        # Product 1 (Chez Loutcha) - 4500 FCFA
        self.produit_1 = Produit.objects.create(
            etablissement=self.etablissement_a,
            categorie=self.category,
            nom='Thiéboudienne Rouge',
            prix_base=Decimal('4500.00'),
            image_url='https://example.com/thiebou.jpg',
            est_disponible=True
        )

        # Required Variant for Product 1
        self.variante_req = VarianteProduit.objects.create(
            produit=self.produit_1,
            titre='Portion Normale',
            surcout_prix=Decimal('0.00'),
            est_requis=True
        )
        self.variante_xl = VarianteProduit.objects.create(
            produit=self.produit_1,
            titre='Portion XL Tiof',
            surcout_prix=Decimal('1500.00'),
            est_requis=False
        )

        # Option for Product 1
        self.option_xoogn = OptionProduit.objects.create(
            produit=self.produit_1,
            type_option=OptionProduit.TYPE_SUPPLEMENT,
            titre='Croûte de riz (Xoogn)',
            surcout_prix=Decimal('500.00')
        )

        # Product 2 (Pâtisserie) - 1000 FCFA
        self.produit_2 = Produit.objects.create(
            etablissement=self.etablissement_b,
            categorie=self.category,
            nom='Jus de Bissap Frais',
            prix_base=Decimal('1000.00'),
            image_url='https://example.com/bissap.jpg',
            est_disponible=True
        )

        # Unavailable Product 3
        self.produit_indisponible = Produit.objects.create(
            etablissement=self.etablissement_a,
            categorie=self.category,
            nom='Homard Grillé Off',
            prix_base=Decimal('15000.00'),
            image_url='https://example.com/homard.jpg',
            est_disponible=False
        )

        # URLs
        self.cart_url = '/api/orders/cart/'
        self.cart_items_url = '/api/orders/cart/items/'
        self.addresses_url = '/api/orders/addresses/'
        self.checkout_url = '/api/orders/checkout/'
        self.orders_url = '/api/orders/'

    # ------------------------------------------------------------------
    # 1. AUTHENTIFICATION & PANIER GET/DELETE
    # ------------------------------------------------------------------

    def test_01_get_cart_non_authentifie_refuse(self):
        """Un utilisateur non authentifié ne peut pas lire le panier."""
        response = self.client.get(self.cart_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_02_get_cart_authentifie_reussi(self):
        """Un utilisateur connecté obtient son panier actif vide par défaut."""
        self.client.force_authenticate(user=self.client_user)
        response = self.client.get(self.cart_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['actif'])
        self.assertEqual(response.data['nombre_articles'], 0)
        self.assertEqual(response.data['total_panier'], '0.00')

    # ------------------------------------------------------------------
    # 2. AJOUT PRODUITS AU PANIER (POST /api/orders/cart/items/)
    # ------------------------------------------------------------------

    def test_03_ajout_produit_valide(self):
        """Ajout d'un produit avec variante et option valides."""
        self.client.force_authenticate(user=self.client_user)
        payload = {
            'produit': self.produit_1.id,
            'quantite': 2,
            'variante': self.variante_xl.id,
            'options': [self.option_xoogn.id]
        }
        response = self.client.post(self.cart_items_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        # Prix unitaire = 4500 + 1500 + 500 = 6500 x 2 = 13000
        self.assertEqual(response.data['total_panier'], '13000.00')
        self.assertEqual(response.data['nombre_articles'], 2)

    def test_04_ajout_quantite_invalide_refuse(self):
        """Refus de l'ajout si la quantité est < 1."""
        self.client.force_authenticate(user=self.client_user)
        payload = {'produit': self.produit_1.id, 'quantite': 0}
        response = self.client.post(self.cart_items_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_05_ajout_produit_indisponible_refuse(self):
        """Refus de l'ajout d'un produit indisponible."""
        self.client.force_authenticate(user=self.client_user)
        payload = {'produit': self.produit_indisponible.id, 'quantite': 1}
        response = self.client.post(self.cart_items_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_06_ajout_variante_invalide_refuse(self):
        """Refus si la variante n'existe pas ou n'appartient pas au produit."""
        self.client.force_authenticate(user=self.client_user)
        payload = {'produit': self.produit_2.id, 'variante': self.variante_xl.id}
        response = self.client.post(self.cart_items_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_07_securite_prix_calcule_cote_serveur(self):
        """Même si le client envoie un prix falsifié dans le JSON, le serveur utilise le prix catalogue."""
        self.client.force_authenticate(user=self.client_user)
        payload = {
            'produit': self.produit_1.id,
            'quantite': 1,
            'variante': self.variante_req.id,
            'prix_unitaire': '1.00'  # Falsification ignorée
        }
        response = self.client.post(self.cart_items_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['total_panier'], '4500.00')

    # ------------------------------------------------------------------
    # 3. MODIFICATION & SUPPRESSION ARTICLES DU PANIER
    # ------------------------------------------------------------------

    def test_08_modification_quantite_article(self):
        """Mise à jour de la quantité via PATCH /api/orders/cart/items/{id}/."""
        self.client.force_authenticate(user=self.client_user)
        panier = Panier.objects.create(utilisateur=self.client_user, actif=True)
        item = PanierItem.objects.create(
            panier=panier, produit=self.produit_2, quantite=1, prix_unitaire=Decimal('1000.00')
        )

        item_url = f'/api/orders/cart/items/{item.id}/'
        response = self.client.patch(item_url, {'quantite': 5}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['total_panier'], '5000.00')

    def test_09_suppression_article_du_panier(self):
        """Suppression d'un article via DELETE /api/orders/cart/items/{id}/."""
        self.client.force_authenticate(user=self.client_user)
        panier = Panier.objects.create(utilisateur=self.client_user, actif=True)
        item = PanierItem.objects.create(
            panier=panier, produit=self.produit_2, quantite=1, prix_unitaire=Decimal('1000.00')
        )

        item_url = f'/api/orders/cart/items/{item.id}/'
        response = self.client.delete(item_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['nombre_articles'], 0)

    def test_10_isolation_panier_autre_utilisateur(self):
        """Un utilisateur ne peut pas modifier ni supprimer un article du panier d'autrui."""
        panier_other = Panier.objects.create(utilisateur=self.other_user, actif=True)
        item_other = PanierItem.objects.create(
            panier=panier_other, produit=self.produit_2, quantite=1, prix_unitaire=Decimal('1000.00')
        )

        self.client.force_authenticate(user=self.client_user)
        item_url = f'/api/orders/cart/items/{item_other.id}/'
        response = self.client.patch(item_url, {'quantite': 10}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_11_vidage_complet_panier(self):
        """DELETE /api/orders/cart/ vide le panier entièrement."""
        self.client.force_authenticate(user=self.client_user)
        panier = Panier.objects.create(utilisateur=self.client_user, actif=True)
        PanierItem.objects.create(panier=panier, produit=self.produit_1, quantite=1, prix_unitaire=Decimal('4500.00'))
        PanierItem.objects.create(panier=panier, produit=self.produit_2, quantite=2, prix_unitaire=Decimal('1000.00'))

        response = self.client.delete(self.cart_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['nombre_articles'], 0)

    # ------------------------------------------------------------------
    # 4. CARNET D'ADRESSES REST API
    # ------------------------------------------------------------------

    def test_12_gestion_carnet_adresses(self):
        """Test du CRUD complet sur les adresses de livraison."""
        self.client.force_authenticate(user=self.client_user)

        # 1. Création
        addr_data = {
            'titre': 'Maison',
            'adresse': 'Villa 44, Point E, Dakar',
            'latitude': '14.7000000',
            'longitude': '-17.4500000',
            'instructions': 'Portail noir',
            'est_defaut': True
        }
        res_create = self.client.post(self.addresses_url, addr_data, format='json')
        self.assertEqual(res_create.status_code, status.HTTP_201_CREATED)
        addr_id = res_create.data['id']

        # 2. Liste
        res_list = self.client.get(self.addresses_url)
        self.assertEqual(res_list.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res_list.data), 1)

        # 3. Mettre par défaut
        res_defaut = self.client.post(f'/api/orders/addresses/{addr_id}/set-default/')
        self.assertEqual(res_defaut.status_code, status.HTTP_200_OK)
        self.assertTrue(res_defaut.data['est_defaut'])

        # 4. Suppression
        res_del = self.client.delete(f'/api/orders/addresses/{addr_id}/')
        self.assertEqual(res_del.status_code, status.HTTP_204_NO_CONTENT)

    # ------------------------------------------------------------------
    # 5. CHECKOUT & COMMANDE MULTI-ÉTABLISSEMENTS
    # ------------------------------------------------------------------

    def test_13_checkout_panier_vide_refuse(self):
        """Checkout refusé si le panier est vide."""
        self.client.force_authenticate(user=self.client_user)
        payload = {
            'adresse_livraison': '10 Rue Carnot, Dakar',
            'destinataire': {'nom': 'Moussa Diop', 'telephone': '+221770000001'}
        }
        response = self.client.post(self.checkout_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_14_ajout_multi_etablissements_refuse(self):
        """Ajout d'un produit d'un second établissement refusé (Règle AYYOU 1 seul établissement par panier)."""
        self.client.force_authenticate(user=self.client_user)

        # 1. Ajouter Produit 1 (Restaurant A)
        res1 = self.client.post(self.cart_items_url, {
            'produit': self.produit_1.id,
            'quantite': 1,
            'variante': self.variante_xl.id,
            'options': [self.option_xoogn.id]
        }, format='json')
        self.assertEqual(res1.status_code, status.HTTP_201_CREATED)

        # 2. Essayer d'ajouter Produit 2 (Vendor B) -> Refusé HTTP 400
        res2 = self.client.post(self.cart_items_url, {
            'produit': self.produit_2.id,
            'quantite': 2
        }, format='json')
        self.assertEqual(res2.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(res2.data.get('code'), 'CART_DIFFERENT_ESTABLISHMENT')

    def test_15_historique_commandes_et_isolation(self):
        """Consultation de l'historique des commandes et étanchéité entre clients."""
        # Client 1 passe une commande
        self.client.force_authenticate(user=self.client_user)
        self.client.post(self.cart_items_url, {'produit': self.produit_2.id, 'quantite': 1}, format='json')
        res_ck = self.client.post(self.checkout_url, {'adresse_livraison': 'Dakar'}, format='json')
        cmd_id = res_ck.data['id']

        # Client 1 consulte son historique
        res_hist = self.client.get(self.orders_url)
        self.assertEqual(res_hist.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res_hist.data), 1)

        # Client 2 ne voit pas la commande de Client 1
        self.client.force_authenticate(user=self.other_user)
        res_other_hist = self.client.get(self.orders_url)
        self.assertEqual(res_other_hist.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res_other_hist.data), 0)

        # Client 2 essaye d'accéder directement au détail de la commande de Client 1
        res_other_detail = self.client.get(f'/api/orders/{cmd_id}/')
        self.assertEqual(res_other_detail.status_code, status.HTTP_404_NOT_FOUND)
