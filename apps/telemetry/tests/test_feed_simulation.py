import os
import numpy as np
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status

from apps.users.models import Utilisateur
from apps.catalog.models import PublicationFeed, Produit, Etablissement, Categorie
from apps.telemetry.models import VideoEventLog
from apps.telemetry.ml.dataset import FEATURE_COLUMNS
from apps.telemetry.ml.scoring import RecommendationScoringService
from apps.telemetry.ml.simulate_feed import run_feed_simulation_for_profile, run_all_phase_6_scenarios


class FeedSimulationTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        # 1. Données du catalogue
        cls.cat = Categorie.objects.create(nom="Cuisine Sénégalaise", slug="cuisine-senegalaise")
        cls.etablissement = Etablissement.objects.create(
            nom="Chez Coumba",
            adresse="Plateau Dakar",
            telephone="+221773333333",
            note_moyenne=4.8,
            nombre_avis=50
        )
        cls.produit1 = Produit.objects.create(
            nom="Thieboudienne Penda Mbaye",
            prix_base=3000.00,
            etablissement=cls.etablissement,
            categorie=cls.cat
        )
        cls.produit2 = Produit.objects.create(
            nom="Yassa Poulet Yoff",
            prix_base=2500.00,
            etablissement=cls.etablissement,
            categorie=cls.cat
        )
        cls.pub1 = PublicationFeed.objects.create(
            etablissement=cls.etablissement,
            produit=cls.produit1,
            media_url="https://example.com/thieb.mp4",
            nombre_likes=15,
            nombre_partages=3
        )
        cls.pub2 = PublicationFeed.objects.create(
            etablissement=cls.etablissement,
            produit=cls.produit2,
            media_url="https://example.com/yassa.mp4",
            nombre_likes=30,
            nombre_partages=8
        )

        # 2. Utilisateurs pour simulation
        cls.user_auth = Utilisateur.objects.create(
            email="sim.user@ayyou.sn",
            nom="SimUser",
            prenom="Test",
            numero_telephone="+221774444444"
        )
        VideoEventLog.objects.create(
            utilisateur=cls.user_auth,
            publication=cls.pub1,
            session_id="sim_session_auth_001",
            event_type="LIKE",
            watch_time_seconds=15.0,
            video_duration_seconds=15.0
        )

        cls.client = APIClient()

    def test_01_retrieve_and_score_candidates(self):
        """Vérifie la récupération des candidats et leur scoring par LightGBM V2."""
        res = run_feed_simulation_for_profile(
            user_id=self.user_auth.id,
            scenario_name="Test Simulation Candidate Retrieval"
        )
        self.assertIn('candidates_count', res)
        self.assertGreaterEqual(res['candidates_count'], 2)
        self.assertIn('comparison_table', res)
        self.assertEqual(len(res['comparison_table']), res['candidates_count'])

    def test_02_descending_rank_order_and_no_nans(self):
        """Vérifie que les candidats simulés sont triés par score décroissant sans NaNs."""
        res = run_feed_simulation_for_profile(
            session_id="sim_session_anon_002",
            scenario_name="Test No NaNs & Rank Order"
        )
        table = res['comparison_table']
        scores = [item['predicted_score'] for item in table]

        # Vérification zéro NaN
        for score in scores:
            self.assertFalse(np.isnan(score))
            self.assertIsInstance(score, float)

        # Vérification tri décroissant
        sorted_scores = sorted(scores, reverse=True)
        self.assertEqual(scores, sorted_scores)

    def test_03_cold_start_profile_simulation(self):
        """Vérifie la simulation sans crash pour un visiteur anonyme ou un nouvel utilisateur."""
        new_user = Utilisateur.objects.create(
            email="brand_new@ayyou.sn",
            nom="BrandNew",
            prenom="User",
            numero_telephone="+221775555555"
        )
        res_new_user = run_feed_simulation_for_profile(user_id=new_user.id, scenario_name="Cold Start New User")
        self.assertNotIn('error', res_new_user)
        self.assertEqual(res_new_user['candidates_count'], PublicationFeed.objects.count())

        res_anon = run_feed_simulation_for_profile(session_id="anon_cold_start_999", scenario_name="Cold Start Anon")
        self.assertNotIn('error', res_anon)

    def test_04_run_all_scenarios(self):
        """Vérifie l'exécution groupée de l'ensemble des scénarios de simulation de Phase 6."""
        all_res = run_all_phase_6_scenarios()
        self.assertIsInstance(all_res, dict)
        self.assertGreaterEqual(len(all_res), 4)

    def test_05_pre_exposure_feature_isolation(self):
        """Vérifie que la liste FEATURE_COLUMNS exclut 100% des features post-exposition."""
        post_exposure_features = ['event_type', 'watch_time_seconds', 'completion_rate', 'is_skip', 'is_completed']
        for feat in post_exposure_features:
            self.assertNotIn(feat, FEATURE_COLUMNS)

    def test_06_real_feed_endpoint_unmodified(self):
        """Vérifie impérativement que l'endpoint GET /api/catalog/feed/ reste 100% chronologique et inchangé."""
        response = self.client.get("/api/catalog/feed/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # S'assurer que le feed réel est trié chronologiquement par date_publication décroissante
        data = response.json()
        results = data.get('results', data) if isinstance(data, dict) else data
        if len(results) >= 2:
            self.assertGreaterEqual(results[0]['id'], results[1]['id'])
