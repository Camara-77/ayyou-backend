from django.test import TestCase
from decimal import Decimal
from apps.catalog.models import Etablissement, Produit, Categorie
from apps.ai.tools import (
    search_food,
    search_food_paginated,
    search_establishments,
    search_establishments_paginated,
    get_product,
    get_establishment
)


class CatalogDiscoveryTests(TestCase):
    def setUp(self):
        # Create active verified establishment
        self.resto1 = Etablissement.objects.create(
            nom="Chez Loutcha Dakar",
            type_etablissement="RESTAURANT",
            statut_verification=Etablissement.STATUT_VALIDE,
            adresse="Plateau, Dakar",
            statut=Etablissement.STATUT_OUVERT
        )
        self.resto2 = Etablissement.objects.create(
            nom="Le Lagon 1",
            type_etablissement="RESTAURANT",
            statut_verification=Etablissement.STATUT_VALIDE,
            adresse="Corniche, Dakar",
            statut=Etablissement.STATUT_OUVERT
        )
        self.unverified_resto = Etablissement.objects.create(
            nom="Resto Non Verifie",
            type_etablissement="RESTAURANT",
            statut_verification=Etablissement.STATUT_EN_ATTENTE,
            adresse="Dakar"
        )

        # Create Category
        self.cat_senegal = Categorie.objects.create(
            nom="Sénégalais",
            slug="senegalais",
            est_active=True
        )

        # Create Products
        self.p_thieb = Produit.objects.create(
            etablissement=self.resto1,
            categorie=self.cat_senegal,
            nom="Thiéboudienne Penda Mbaye",
            prix_base=Decimal("4500.00"),
            est_disponible=True
        )
        self.p_yassa = Produit.objects.create(
            etablissement=self.resto1,
            categorie=self.cat_senegal,
            nom="Yassa Poulet Grillé",
            prix_base=Decimal("3500.00"),
            est_disponible=True
        )
        self.p_dibi = Produit.objects.create(
            etablissement=self.resto2,
            categorie=self.cat_senegal,
            nom="Dibi Agneau",
            prix_base=Decimal("6000.00"),
            est_disponible=True
        )
        self.p_disabled = Produit.objects.create(
            etablissement=self.resto1,
            categorie=self.cat_senegal,
            nom="Plat Indisponible Test",
            prix_base=Decimal("2000.00"),
            est_disponible=False
        )

    def test_accent_insensitive_search(self):
        """Vérifie que la recherche 'thieboudienne' trouve 'Thiéboudienne Penda Mbaye' avec accent."""
        res = search_food(query="thieboudienne")
        self.assertTrue(len(res) > 0)
        self.assertEqual(res[0]["id"], self.p_thieb.id)

    def test_budget_filtering(self):
        """Vérifie le filtrage par prix maximum (ex: <= 5000 FCFA)."""
        res = search_food(max_price=5000)
        product_ids = [p["id"] for p in res]
        self.assertIn(self.p_thieb.id, product_ids)
        self.assertIn(self.p_yassa.id, product_ids)
        self.assertNotIn(self.p_dibi.id, product_ids)  # 6000 FCFA > 5000 FCFA

    def test_disabled_product_filtering(self):
        """Vérifie qu'un produit marqué est_disponible=False est exclu des résultats."""
        res = search_food(query="Plat Indisponible Test")
        self.assertEqual(len(res), 0)

    def test_realtime_price_update(self):
        """Vérifie la répercussion immédiate d'une mise à jour de prix dans PostgreSQL."""
        # Verification initiale
        p_data = get_product(self.p_thieb.id)
        self.assertEqual(p_data["prix"], 4500.0)

        # Modification du prix en base
        self.p_thieb.prix_base = Decimal("5000.00")
        self.p_thieb.save()

        # Nouvelle consultation en temps réel
        p_data_new = get_product(self.p_thieb.id)
        self.assertEqual(p_data_new["prix"], 5000.0)
        self.assertIn("5 000 FCFA", p_data_new["prix_formate"])

    def test_paginated_establishments(self):
        """Vérifie la pagination des établissements avec offset et limit."""
        res_paginated = search_establishments_paginated(limit=1, offset=0)
        self.assertEqual(len(res_paginated["results"]), 1)
        self.assertEqual(res_paginated["total_count"], 2)
        self.assertTrue(res_paginated["has_more"])

        res_page2 = search_establishments_paginated(limit=1, offset=1)
        self.assertEqual(len(res_page2["results"]), 1)
        self.assertFalse(res_page2["has_more"])

    def test_security_isolation(self):
        """Vérifie qu'aucun champ sensible n'est exposé dans les dictionnaires d'outils."""
        prod_res = get_product(self.p_thieb.id)
        self.assertNotIn("password", prod_res)
        self.assertNotIn("secret_key", prod_res)
        self.assertNotIn("database_url", prod_res)

        resto_res = get_establishment(self.resto1.id)
        self.assertNotIn("password", resto_res)
        self.assertNotIn("secret_key", resto_res)

    def test_search_restaurants_by_food_and_budget(self):
        """Vérifie la recherche d'établissements filtrée par plat (thiéboudienne) ET par budget max (5000 FCFA)."""
        res = search_establishments_paginated(query="thiéboudienne", max_price=5000)
        self.assertGreaterEqual(res["total_count"], 1)
        resto_ids = [e["id"] for e in res["results"]]
        self.assertIn(self.resto1.id, resto_ids)
        self.assertNotIn(self.resto2.id, resto_ids)  # resto2 a dibi à 6000 > 5000

        # Test d'intégration de la vue AIPlanningParseView avec le prompt exact
        from rest_framework.test import APIRequestFactory
        from apps.ai.views_planning_ai import AIPlanningParseView
        factory = APIRequestFactory()
        prompt = "Montre-moi les restaurants qui proposent du thiéboudienne avec un budget de 5 000 FCFA."
        req = factory.post('/api/ai/planning-parse/', {'prompt': prompt}, format='json')
        view = AIPlanningParseView.as_view()
        response = view(req)

        self.assertEqual(response.status_code, 200)
        data = response.data
        self.assertEqual(data["status"], "restaurant_search")
        self.assertEqual(data["intent"], "RESTAURANT_SEARCH")
        self.assertEqual(data["type"], "catalog_results")
        self.assertEqual(data["entity"], "restaurant")
        self.assertIn("thiéboudienne", data["message"].lower())
        self.assertIn("5 000 fcfa", data["message"].lower())
        self.assertGreaterEqual(len(data["matching_establishments"]), 1)
        self.assertIn("conversation_id", data)

