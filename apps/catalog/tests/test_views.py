from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from apps.users.models import Utilisateur
from apps.catalog.models import (
    Categorie,
    Etablissement,
    Produit,
    VarianteProduit,
    OptionProduit,
    PublicationFeed,
    LikeProduit
)


class CatalogViewsTestCase(APITestCase):

    def setUp(self):
        # Clients et utilisateurs
        self.user_client = Utilisateur.objects.create_user(
            email="client.view@ayyou.sn",
            numero_telephone="+221774445566",
            prenom="Moussa",
            nom="Ndiaye",
            password="Password123!"
        )

        self.other_client = Utilisateur.objects.create_user(
            email="other.client@ayyou.sn",
            numero_telephone="+221775556677",
            prenom="Fatou",
            nom="Sene",
            password="Password123!"
        )

        self.proprietaire = Utilisateur.objects.create_user(
            email="owner.view@ayyou.sn",
            numero_telephone="+221776667788",
            prenom="Ibrahima",
            nom="Diallo",
            password="OwnerPassword123!"
        )

        # Catégories (1 active, 1 inactive pour tester le filtrage)
        self.cat_active1 = Categorie.objects.create(
            nom="Burgers Teranga",
            slug="burgers-teranga",
            icone="burger",
            est_active=True,
            ordre=1
        )
        self.cat_active2 = Categorie.objects.create(
            nom="Plats Nationaux",
            slug="plats-nationaux",
            icone="utensils",
            est_active=True,
            ordre=2
        )
        self.cat_inactive = Categorie.objects.create(
            nom="Catégorie Masquée",
            slug="categorie-masquee",
            icone="eye-off",
            est_active=False,
            ordre=3
        )

        # Établissements
        self.restaurant = Etablissement.objects.create(
            nom="Chez Loutcha Plateau",
            type_etablissement=Etablissement.TYPE_RESTAURANT,
            proprietaire=self.proprietaire,
            adresse="Rue Félix Faure, Dakar",
            latitude=14.6698,
            longitude=-17.4381,
            specialite="Cuisine Sénégalaise",
            statut=Etablissement.STATUT_OUVERT,
            est_verifie=True
        )

        self.vendeur = Etablissement.objects.create(
            nom="Délices d'Awa (Vendeur à Domicile)",
            type_etablissement=Etablissement.TYPE_VENDEUR,
            adresse="Almadies, Dakar",
            specialite="Pâtisserie & Gâteaux",
            statut=Etablissement.STATUT_OUVERT,
            est_verifie=True
        )

        # Produit
        self.produit = Produit.objects.create(
            etablissement=self.restaurant,
            categorie=self.cat_active2,
            nom="Thiéboudienne Rouge Penda Mbaye",
            description="Riz au poisson Tiof avec légumes de saison",
            prix_base=4500.00,
            image_url="https://ayyou.sn/images/thieb.jpg",
            est_disponible=True,
            stock_disponible=80,
            stock_ayyou_reserve=25,
            temps_preparation="20 min"
        )

        self.produit_indisponible = Produit.objects.create(
            etablissement=self.vendeur,
            categorie=self.cat_active1,
            nom="Burger Yassa Épuisé",
            description="Burger avec poulet mariné au citron et oignons",
            prix_base=3500.00,
            image_url="https://ayyou.sn/images/burger.jpg",
            est_disponible=False,
            stock_disponible=0,
            stock_ayyou_reserve=0
        )

        # Variante & Options
        self.variante = VarianteProduit.objects.create(
            produit=self.produit,
            titre="Grand Format Tiof XL",
            surcout_prix=1500.00,
            est_requis=False
        )

        self.sauce = OptionProduit.objects.create(
            produit=self.produit,
            type_option=OptionProduit.TYPE_SAUCE,
            titre="Sauce Beugueul",
            surcout_prix=0.00,
            est_inclus=True
        )

        self.supplement = OptionProduit.objects.create(
            produit=self.produit,
            type_option=OptionProduit.TYPE_SUPPLEMENT,
            titre="Supplément Xoogn",
            surcout_prix=500.00,
            est_inclus=False
        )

        # Feed
        self.publication = PublicationFeed.objects.create(
            etablissement=self.restaurant,
            produit=self.produit,
            media_url="https://ayyou.sn/feed/video1.mp4",
            type_media=PublicationFeed.TYPE_MEDIA_VIDEO,
            duree_video="1:15"
        )

    # ------------------------------------------------------------------
    # CATÉGORIES (1 - 3)
    # ------------------------------------------------------------------
    def test_01_get_categories_success(self):
        url = reverse('catalog:categorie-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_02_only_active_categories_appear(self):
        url = reverse('catalog:categorie-list')
        response = self.client.get(url)
        slugs = [c['slug'] for c in response.data]
        self.assertIn('burgers-teranga', slugs)
        self.assertIn('plats-nationaux', slugs)
        self.assertNotIn('categorie-masquee', slugs)

    def test_03_categories_ordering(self):
        url = reverse('catalog:categorie-list')
        response = self.client.get(url)
        self.assertEqual(response.data[0]['slug'], 'burgers-teranga')
        self.assertEqual(response.data[1]['slug'], 'plats-nationaux')

    # ------------------------------------------------------------------
    # ÉTABLISSEMENTS (4 - 9)
    # ------------------------------------------------------------------
    def test_04_list_establishments_paginated(self):
        url = reverse('catalog:etablissement-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('results', response.data)
        self.assertEqual(response.data['count'], 2)

    def test_05_detail_establishment(self):
        url = reverse('catalog:etablissement-detail', kwargs={'pk': self.restaurant.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['nom'], "Chez Loutcha Plateau")

    def test_06_distinguishes_restaurant_and_vendeur(self):
        url = reverse('catalog:etablissement-list')
        response = self.client.get(url)
        results = response.data['results']
        types = [e['type_etablissement'] for e in results]
        self.assertIn('RESTAURANT', types)
        self.assertIn('VENDEUR', types)

    def test_07_no_sensitive_owner_data_exposed(self):
        url = reverse('catalog:etablissement-detail', kwargs={'pk': self.restaurant.pk})
        response = self.client.get(url)
        self.assertNotIn('password', response.data)
        self.assertNotIn('user_password', response.data)
        self.assertEqual(response.data['proprietaire_nom'], "Ibrahima Diallo")

    def test_08_search_establishment_by_name(self):
        url = reverse('catalog:etablissement-list') + '?search=Loutcha'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['nom'], "Chez Loutcha Plateau")

    def test_09_filter_establishment_by_type(self):
        url = reverse('catalog:etablissement-list') + '?type_etablissement=VENDEUR'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['type_etablissement'], "VENDEUR")

    # ------------------------------------------------------------------
    # PRODUITS (10 - 16)
    # ------------------------------------------------------------------
    def test_10_list_products_paginated(self):
        url = reverse('catalog:produit-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('results', response.data)
        self.assertEqual(response.data['count'], 2)

    def test_11_detail_product(self):
        url = reverse('catalog:produit-detail', kwargs={'pk': self.produit.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['nom'], "Thiéboudienne Rouge Penda Mbaye")

    def test_12_filter_disponibilite_product(self):
        url = reverse('catalog:produit-list') + '?est_disponible=true'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['nom'], "Thiéboudienne Rouge Penda Mbaye")

    def test_13_filter_product_by_category(self):
        url = reverse('catalog:produit-list') + '?categorie=burgers-teranga'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['nom'], "Burger Yassa Épuisé")

    def test_14_filter_product_by_establishment(self):
        url = reverse('catalog:produit-list') + f'?etablissement={self.restaurant.pk}'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)

    def test_15_search_product(self):
        url = reverse('catalog:produit-list') + '?search=Thiéboudienne'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)

    def test_16_internal_stocks_not_exposed(self):
        url_list = reverse('catalog:produit-list')
        res_list = self.client.get(url_list)
        first_item = res_list.data['results'][0]
        self.assertNotIn('stock_disponible', first_item)
        self.assertNotIn('stock_ayyou_reserve', first_item)

        url_detail = reverse('catalog:produit-detail', kwargs={'pk': self.produit.pk})
        res_detail = self.client.get(url_detail)
        self.assertNotIn('stock_disponible', res_detail.data)
        self.assertNotIn('stock_ayyou_reserve', res_detail.data)

    # ------------------------------------------------------------------
    # VARIANTES & OPTIONS (17 - 19)
    # ------------------------------------------------------------------
    def test_17_variantes_in_product_detail(self):
        url = reverse('catalog:produit-detail', kwargs={'pk': self.produit.pk})
        response = self.client.get(url)
        self.assertIn('variantes', response.data)
        self.assertEqual(len(response.data['variantes']), 1)
        self.assertEqual(response.data['variantes'][0]['titre'], "Grand Format Tiof XL")

    def test_18_sauces_separated_in_product_detail(self):
        url = reverse('catalog:produit-detail', kwargs={'pk': self.produit.pk})
        response = self.client.get(url)
        self.assertIn('sauces', response.data)
        self.assertEqual(len(response.data['sauces']), 1)
        self.assertEqual(response.data['sauces'][0]['titre'], "Sauce Beugueul")

    def test_19_supplements_separated_in_product_detail(self):
        url = reverse('catalog:produit-detail', kwargs={'pk': self.produit.pk})
        response = self.client.get(url)
        self.assertIn('supplements', response.data)
        self.assertEqual(len(response.data['supplements']), 1)
        self.assertEqual(response.data['supplements'][0]['titre'], "Supplément Xoogn")

    # ------------------------------------------------------------------
    # FEED (20 - 22)
    # ------------------------------------------------------------------
    def test_20_list_feed_paginated(self):
        url = reverse('catalog:publication-feed-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('results', response.data)
        self.assertEqual(response.data['count'], 1)

    def test_21_is_liked_calculated_for_authenticated_user(self):
        LikeProduit.objects.create(utilisateur=self.user_client, publication=self.publication)
        url = reverse('catalog:publication-feed-list')

        # Authentifié -> is_liked True
        self.client.force_authenticate(user=self.user_client)
        res_auth = self.client.get(url)
        self.assertTrue(res_auth.data['results'][0]['is_liked'])

    def test_22_is_liked_false_for_unauthenticated_user(self):
        url = reverse('catalog:publication-feed-list')
        self.client.force_authenticate(user=None)
        res_anon = self.client.get(url)
        self.assertFalse(res_anon.data['results'][0]['is_liked'])

    # ------------------------------------------------------------------
    # LIKES (23 - 26)
    # ------------------------------------------------------------------
    def test_23_create_like_authenticated_success(self):
        url = reverse('catalog:like-list-create-delete')
        self.client.force_authenticate(user=self.user_client)
        response = self.client.post(url, {'produit': self.produit.pk})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Vérification incrément nombre_likes
        self.produit.refresh_from_db()
        self.assertEqual(self.produit.nombre_likes, 1)

    def test_24_delete_like_authenticated_success(self):
        like = LikeProduit.objects.create(utilisateur=self.user_client, produit=self.produit)
        Produit.objects.filter(pk=self.produit.pk).update(nombre_likes=1)

        url = reverse('catalog:like-detail', kwargs={'pk': like.pk})
        self.client.force_authenticate(user=self.user_client)
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        # Vérification décrément nombre_likes
        self.produit.refresh_from_db()
        self.assertEqual(self.produit.nombre_likes, 0)

    def test_25_duplicate_like_prevented(self):
        LikeProduit.objects.create(utilisateur=self.user_client, produit=self.produit)
        url = reverse('catalog:like-list-create-delete')
        self.client.force_authenticate(user=self.user_client)
        response = self.client.post(url, {'produit': self.produit.pk})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_26_unauthenticated_like_creation_denied(self):
        url = reverse('catalog:like-list-create-delete')
        self.client.force_authenticate(user=None)
        response = self.client.post(url, {'produit': self.produit.pk})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    # ------------------------------------------------------------------
    # SÉCURITÉ & DONNÉES SENSIBLES (27 - 28)
    # ------------------------------------------------------------------
    def test_27_personal_like_endpoint_requires_jwt_auth(self):
        url = reverse('catalog:like-list-create-delete')
        self.client.force_authenticate(user=None)
        res_post = self.client.post(url, {'produit': self.produit.pk})
        res_del = self.client.delete(url, {'produit': self.produit.pk})
        self.assertEqual(res_post.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(res_del.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_28_no_passwords_or_hashes_exposed(self):
        urls = [
            reverse('catalog:categorie-list'),
            reverse('catalog:etablissement-list'),
            reverse('catalog:etablissement-detail', kwargs={'pk': self.restaurant.pk}),
            reverse('catalog:produit-list'),
            reverse('catalog:produit-detail', kwargs={'pk': self.produit.pk}),
            reverse('catalog:publication-feed-list'),
        ]
        for url in urls:
            res = self.client.get(url)
            content_str = str(res.content)
            self.assertNotIn('password', content_str)
            self.assertNotIn('pbkdf2', content_str)
            self.assertNotIn('otp', content_str)
