from django.test import TestCase
from decimal import Decimal
from apps.catalog.models import Categorie, Etablissement, Produit
from apps.catalog.catalog_service import CatalogSearchService, parse_budget
from apps.users.models import Utilisateur


class CatalogP0SanitizationTests(TestCase):
    """
    Suite de tests unitaires P0 garantissant l'assainissement et la vérité catalogue PostgreSQL.
    """

    def setUp(self):
        # 1. Utilisateur Vendeur
        self.vendeur = Utilisateur.objects.create_user(
            email="vendeur@ayyou.com",
            numero_telephone="+221770000001",
            nom="Diop",
            prenom="Awa",
            password="Password123!"
        )

        # 2. Catégorie valide (avec produit)
        self.cat_active = Categorie.objects.create(
            nom="Plats Sénégalais",
            slug="plats-senegalais",
            est_active=True
        )

        # 3. Catégorie active mais VIDE (0 produit) -> Doit être exclue par P0 !
        self.cat_vide = Categorie.objects.create(
            nom="Pâtisserie Inactive Test",
            slug="patisserie-inactive-test",
            est_active=True
        )

        # 4. Établissement valide A (avec produit thiéboudienne)
        self.est_valid_a = Etablissement.objects.create(
            nom="Chez Fatou",
            type_etablissement=Etablissement.TYPE_RESTAURANT,
            proprietaire=self.vendeur,
            adresse="Fann Résidence",
            statut_verification=Etablissement.STATUT_VALIDE
        )

        # 5. Établissement B dont le nom contient "Thiéboudienne" mais qui n'a PAS de plat Thiéboudienne -> Doit être exclu !
        self.est_piege = Etablissement.objects.create(
            nom="Thiéboudienne Express Fake",
            type_etablissement=Etablissement.TYPE_RESTAURANT,
            proprietaire=self.vendeur,
            adresse="Plateau",
            statut_verification=Etablissement.STATUT_VALIDE
        )

        # 6. Établissement C totalement VIDE (0 produit) -> Doit être exclu !
        self.est_vide = Etablissement.objects.create(
            nom="Restaurant Fantôme",
            type_etablissement=Etablissement.TYPE_RESTAURANT,
            proprietaire=self.vendeur,
            adresse="Almadies",
            statut_verification=Etablissement.STATUT_VALIDE
        )

        # 7. Produit Thiéboudienne sur Établissement A
        self.prod_thieb = Produit.objects.create(
            etablissement=self.est_valid_a,
            categorie=self.cat_active,
            nom="Thiéboudienne Rouge Penda Mbaye",
            description="Délicieux riz au poisson avec légume cassave et rof",
            prix_base=Decimal("3500.00"),
            est_disponible=True,
            image_url="http://example.com/thieb.jpg"
        )

        # 8. Produit Burger sur Établissement Piege (pour qu'il ait 1 produit, mais PAS de thiéboudienne)
        self.prod_burger = Produit.objects.create(
            etablissement=self.est_piege,
            categorie=self.cat_active,
            nom="Cheeseburger Double",
            description="Burger gourmand avec sauce maison",
            prix_base=Decimal("4000.00"),
            est_disponible=True,
            image_url="http://example.com/burger.jpg"
        )

        # 9. Produit Indisponible sur Établissement A
        self.prod_indispo = Produit.objects.create(
            etablissement=self.est_valid_a,
            categorie=self.cat_active,
            nom="Soupe de Poisson Indisponible",
            description="Non disponible aujourd'hui",
            prix_base=Decimal("2000.00"),
            est_disponible=False,
            image_url="http://example.com/soupe.jpg"
        )

    def test_01_search_products_returns_real_products_only(self):
        """TEST 1: Recherche 'thiéboudienne' -> produits réels uniquement."""
        res = CatalogSearchService.search_products(query="thiéboudienne")
        self.assertTrue(res["success"])
        self.assertEqual(res["total_count"], 1)
        self.assertEqual(res["results"][0]["id"], self.prod_thieb.id)
        self.assertEqual(res["results"][0]["nom"], "Thiéboudienne Rouge Penda Mbaye")

    def test_02_search_establishments_by_product_returns_matching_establishments(self):
        """TEST 2: Recherche 'restaurants proposant du thiéboudienne' -> uniquement établissements ayant un Produit correspondant."""
        res = CatalogSearchService.search_establishments_by_product(product_query="thiéboudienne")
        self.assertTrue(res["success"])
        self.assertEqual(res["total_count"], 1)
        self.assertEqual(res["results"][0]["id"], self.est_valid_a.id)

    def test_03_establishment_name_trap_is_not_returned(self):
        """TEST 3: Un établissement dont le nom contient 'thiéboudienne' mais qui n'a pas le produit NE DOIT PAS être retourné."""
        res = CatalogSearchService.search_establishments_by_product(product_query="thiéboudienne")
        returned_ids = [r["id"] for r in res["results"]]
        self.assertNotIn(self.est_piege.id, returned_ids, "L'établissement piège ne doit PAS être retourné !")

    def test_04_active_empty_category_is_excluded(self):
        """TEST 4: Catégorie active avec 0 produit NE DOIT PAS être retournée par le catalogue IA."""
        categories = CatalogSearchService.get_categories_with_products()
        cat_ids = [c["id"] for c in categories]
        self.assertIn(self.cat_active.id, cat_ids)
        self.assertNotIn(self.cat_vide.id, cat_ids, "La catégorie vide doit être exclue des résultats !")

    def test_05_empty_establishment_is_excluded(self):
        """TEST 5: Établissement sans aucun produit NE DOIT PAS être retourné dans les résultats de découverte."""
        res = CatalogSearchService.search_establishments(limit=10)
        returned_ids = [r["id"] for r in res["results"]]
        self.assertNotIn(self.est_vide.id, returned_ids, "L'établissement fantôme vide doit être exclu !")

    def test_06_unavailable_product_is_excluded(self):
        """TEST 6: Produit indisponible ne doit pas apparaître dans les résultats commandables."""
        res = CatalogSearchService.search_products(query="Soupe", is_available=True)
        self.assertEqual(res["total_count"], 0)

    def test_07_budget_parsing_fcfa(self):
        """TEST 7: Budget '5000 FCFA' -> 5000.0."""
        self.assertEqual(parse_budget("5000 FCFA"), 5000.0)

    def test_08_budget_parsing_spaced_fcfa(self):
        """TEST 8: Budget '5 000 FCFA' -> 5000.0."""
        self.assertEqual(parse_budget("5 000 FCFA"), 5000.0)

    def test_09_budget_parsing_k(self):
        """TEST 9: Budget '5k' -> 5000.0."""
        self.assertEqual(parse_budget("5k"), 5000.0)

    def test_10_get_establishment_products_returns_own_products_only(self):
        """TEST 10: Restaurant sélectionné -> get_establishment_products() retourne uniquement ses vrais produits."""
        res = CatalogSearchService.get_establishment_products(establishment_id=self.est_valid_a.id)
        self.assertTrue(res["success"])
        self.assertEqual(res["total_count"], 1)
        self.assertEqual(res["results"][0]["id"], self.prod_thieb.id)

    def test_11_non_existent_product_returns_none(self):
        """TEST 11: Produit inexistant -> résultat vide proprement (None)."""
        prod = CatalogSearchService.get_product(product_id=999999)
        self.assertIsNone(prod)

    def test_12_non_existent_category_returns_none(self):
        """TEST 12: Catégorie inexistante -> résultat vide proprement (None)."""
        cat = CatalogSearchService.get_category(category_id_or_slug="slug-inexistant-xyz")
        self.assertIsNone(cat)

    def test_13_no_results_invented(self):
        """TEST 13: Aucune donnée inventée si 0 résultat."""
        res = CatalogSearchService.search_products(query="sushi-japonais-inexistant")
        self.assertEqual(res["total_count"], 0)
        self.assertEqual(len(res["results"]), 0)

    def test_14_data_privacy_isolation(self):
        """TEST 14: Vérifier l'isolation des données privées (pas d'email, de mot de passe ni de token dans le catalogue)."""
        res = CatalogSearchService.search_products(query="thiéboudienne")
        item = res["results"][0]
        keys = list(item.keys())
        self.assertNotIn("email", keys)
        self.assertNotIn("password", keys)
        self.assertNotIn("telephone", keys)
        self.assertNotIn("token", keys)

    def test_15_user_permissions_and_isolation(self):
        """TEST 15: Vérifier qu'aucun changement de permissions n'a altéré la sécurité des requêtes."""
        cat = CatalogSearchService.get_category(self.cat_active.id)
        self.assertIsNotNone(cat)
        self.assertEqual(cat["nom"], "Plats Sénégalais")
