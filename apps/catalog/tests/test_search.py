from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from apps.catalog.models import Categorie, Etablissement, Produit
from apps.catalog.search_engine import CatalogSearchEngine, normalize_text, strip_accents

class CatalogSearchEngineTestCase(TestCase):
    def setUp(self):
        self.cat_senegal = Categorie.objects.create(nom="Cuisine sénégalaise", slug="senegalaise", est_active=True)
        self.cat_fastfood = Categorie.objects.create(nom="Fast-Food", slug="fastfood", est_active=True)
        self.cat_boissons = Categorie.objects.create(nom="Jus & Boissons", slug="boissons", est_active=True)

        from django.utils import timezone
        future_date = timezone.now() + timezone.timedelta(days=30)

        self.etab_teranga = Etablissement.objects.create(
            nom="Teranga Saveurs",
            type_etablissement="RESTAURANT",
            specialite="Cuisine Sénégalaise & Grillades",
            adresse="Dakar Plateau",
            statut_abonnement=Etablissement.STATUT_ABONNEMENT_ACTIF,
            date_expiration_abonnement=future_date
        )
        self.etab_burger = Etablissement.objects.create(
            nom="Food Corner Burger",
            type_etablissement="RESTAURANT",
            specialite="Burgers & Fast Food",
            adresse="Almadies",
            statut_abonnement=Etablissement.STATUT_ABONNEMENT_ACTIF,
            date_expiration_abonnement=future_date
        )

        self.p_burger = Produit.objects.create(
            nom="Classic Cheeseburger Gourmet",
            description="Délicieux burger avec fromage cheddar et sauce spéciale maison",
            prix_base=4500,
            etablissement=self.etab_burger,
            categorie=self.cat_fastfood,
            est_disponible=True
        )
        self.p_thieb = Produit.objects.create(
            nom="Thiéboudienne Rouge Penda Mbaye",
            description="Riz au poisson thiof braisé avec légumes traditionnels sénégalais",
            prix_base=3500,
            etablissement=self.etab_teranga,
            categorie=self.cat_senegal,
            est_disponible=True
        )
        self.p_mafe = Produit.objects.create(
            nom="Mafé Bœuf Fait Maison",
            description="Sauce pâte d'arachide onctueuse au bœuf avec riz blanc",
            prix_base=3000,
            etablissement=self.etab_teranga,
            categorie=self.cat_senegal,
            est_disponible=True
        )
        self.p_bissap = Produit.objects.create(
            nom="Jus de Bissap Rouge Glacé",
            description="Boisson locale à l'hibiscus et menthe fraîche",
            prix_base=1000,
            etablissement=self.etab_teranga,
            categorie=self.cat_boissons,
            est_disponible=True
        )

    def test_strip_accents_and_normalize(self):
        self.assertEqual(strip_accents("Thiéboudienne"), "Thieboudienne")
        self.assertTrue("mafe" in normalize_text("Mafé Bœuf!"))

    def test_search_hamburger_matches_cheeseburger(self):
        prods = CatalogSearchEngine.search_produits(Produit.objects.all(), "hamburger")
        self.assertIn(self.p_burger, prods)

    def test_search_hambuger_typo_matches_cheeseburger(self):
        prods = CatalogSearchEngine.search_produits(Produit.objects.all(), "hambuger")
        self.assertIn(self.p_burger, prods)

    def test_search_mafe_unaccented_matches_mafe(self):
        prods = CatalogSearchEngine.search_produits(Produit.objects.all(), "mafe")
        self.assertIn(self.p_mafe, prods)

    def test_search_thieboudienne_unaccented_matches_thieb(self):
        prods = CatalogSearchEngine.search_produits(Produit.objects.all(), "thieboudienne")
        self.assertIn(self.p_thieb, prods)

    def test_search_partial_prefix(self):
        prods = CatalogSearchEngine.search_produits(Produit.objects.all(), "thié")
        self.assertIn(self.p_thieb, prods)

    def test_products_api_endpoint(self):
        url = reverse('catalog:produit-list')
        response = self.client.get(url, {'search': 'hamburger'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data.get('results', response.data)
        self.assertTrue(len(results) > 0)
        self.assertEqual(results[0]['nom'], self.p_burger.nom)

    def test_establishments_api_endpoint(self):
        url = reverse('catalog:etablissement-list')
        response = self.client.get(url, {'search': 'burger'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data.get('results', response.data)
        self.assertTrue(len(results) > 0)
        self.assertEqual(results[0]['nom'], self.etab_burger.nom)
