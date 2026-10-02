import os
import json
from pathlib import Path
from django.test import TestCase
from django.conf import settings
from rest_framework.test import APIClient
from rest_framework import status

from apps.catalog.models import PublicationFeed, Produit, Etablissement, Categorie
from apps.users.models import Utilisateur
from apps.telemetry.models import VideoEventLog
from apps.telemetry.ml.scoring import RecommendationScoringService


class RecommenderV3IntegrationTestCase(TestCase):
    """
    Tests unitaires d'intégration technique pour le modèle V3 expérimental (Phase 7).
    """

    @classmethod
    def setUpTestData(cls):
        cls.cat = Categorie.objects.create(nom="Burgers", slug="burgers")
        cls.etablissement = Etablissement.objects.create(
            nom="Dakar Burger Club",
            adresse="Plateau Dakar",
            telephone="+221773334455"
        )
        cls.produit_1 = Produit.objects.create(
            nom="Burger Classic",
            prix_base=3000.00,
            etablissement=cls.etablissement,
            categorie=cls.cat
        )
        cls.produit_2 = Produit.objects.create(
            nom="Burger Bacon",
            prix_base=4000.00,
            etablissement=cls.etablissement,
            categorie=cls.cat
        )
        cls.pub_1 = PublicationFeed.objects.create(
            etablissement=cls.etablissement,
            produit=cls.produit_1,
            media_url="https://example.com/b1.mp4"
        )
        cls.pub_2 = PublicationFeed.objects.create(
            etablissement=cls.etablissement,
            produit=cls.produit_2,
            media_url="https://example.com/b2.mp4"
        )
        cls.user = Utilisateur.objects.create(
            email="v3_test_user@ayyou.sn",
            nom="V3",
            prenom="User",
            numero_telephone="+221774445566"
        )
        cls.client = APIClient()

    def test_01_v3_model_artifacts_exist(self):
        """Vérifie l'existence physique du modèle V3 et de ses métadonnées JSON."""
        v3_joblib = Path('models/recommender/recommender_lgbm_v3.joblib')
        v3_json = Path('models/recommender/recommender_lgbm_v3.json')
        self.assertTrue(v3_joblib.exists(), "Le fichier recommender_lgbm_v3.joblib doit exister.")
        self.assertTrue(v3_json.exists(), "Le fichier recommender_lgbm_v3.json doit exister.")

    def test_02_v3_metadata_status(self):
        """Vérifie que les métadonnées de V3 portent la mention EXPERIMENTAL / OFFLINE ONLY."""
        v3_json = Path('models/recommender/recommender_lgbm_v3.json')
        with open(v3_json, 'r', encoding='utf-8') as f:
            meta = json.load(f)
        
        self.assertEqual(meta.get('model_version'), 'v3')
        self.assertEqual(meta.get('status'), 'EXPERIMENTAL / OFFLINE ONLY')
        self.assertFalse(meta.get('is_production_ready', True))

    def test_03_scoring_service_v3_loading(self):
        """Vérifie le chargement de V3 via RecommendationScoringService."""
        RecommendationScoringService.reset_cache()
        model, metadata = RecommendationScoringService.load_model(model_version='v3')
        self.assertIsNotNone(model)
        self.assertEqual(metadata.get('model_version'), 'v3')

    def test_04_scoring_service_v2_and_v3_coexistence(self):
        """Vérifie que V2 et V3 coexistent sans s'écraser."""
        RecommendationScoringService.reset_cache()
        model_v2, meta_v2 = RecommendationScoringService.load_model(model_version='v2')
        model_v3, meta_v3 = RecommendationScoringService.load_model(model_version='v3')

        self.assertEqual(meta_v2.get('model_version', 'v2'), 'v2')
        self.assertEqual(meta_v3.get('model_version'), 'v3')

    def test_05_scoring_candidates_with_v3(self):
        """Vérifie le scoring de candidats avec le modèle V3."""
        pub_ids = [self.pub_1.id, self.pub_2.id]
        results = RecommendationScoringService.score_candidates(
            publication_ids=pub_ids,
            user_id=self.user.id,
            session_id="sess_test_v3_01",
            model_version='v3'
        )

        self.assertEqual(len(results), 2)
        for res in results:
            self.assertIn('publication_id', res)
            self.assertIn('predicted_score', res)
            self.assertIn('rank', res)
            self.assertIsInstance(res['predicted_score'], float)

    def test_06_simulation_endpoint_v3(self):
        """Vérifie l'API de simulation avec model_version='v3'."""
        payload = {
            'publication_ids': [self.pub_1.id, self.pub_2.id],
            'model_version': 'v3',
            'session_id': 'sess_api_sim_001'
        }
        response = self.client.post('/api/telemetry/scoring/simulate/', data=payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data['status'], 'success')
        self.assertEqual(data['model_version'], 'recommender_lgbm_v3')
        self.assertEqual(data['candidates_count'], 2)

    def test_07_simulation_endpoint_chronological(self):
        """Vérifie l'API de simulation avec model_version='chronological'."""
        payload = {
            'publication_ids': [self.pub_1.id, self.pub_2.id],
            'model_version': 'chronological',
            'session_id': 'sess_api_chrono_001'
        }
        response = self.client.post('/api/telemetry/scoring/simulate/', data=payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data['status'], 'success')
        self.assertEqual(data['model_version'], 'chronological')
        self.assertEqual(data['candidates_count'], 2)

    def test_08_default_recommendation_mode_is_chronological(self):
        """Vérifie que le mode par défaut reste la recommandation chronologique."""
        mode = getattr(settings, 'RECOMMENDATION_MODE', 'chronological')
        self.assertEqual(mode, 'chronological', "Le mode de recommandation par défaut en production doit être 'chronological'.")
