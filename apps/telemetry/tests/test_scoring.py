import os
import tempfile
import pandas as pd
import numpy as np
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status

from apps.users.models import Utilisateur
from apps.catalog.models import PublicationFeed, Produit, Etablissement, Categorie
from apps.telemetry.models import VideoEventLog
from apps.telemetry.ml.dataset import FEATURE_COLUMNS
from apps.telemetry.ml.scoring import RecommendationScoringService


class RecommendationScoringTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        # 1. Catégorie et Établissement
        cls.cat = Categorie.objects.create(nom="Fast Food Test", slug="fast-food-test")
        cls.etablissement = Etablissement.objects.create(
            nom="Resto Test Scoring",
            adresse="Dakar Test",
            telephone="+221770000000",
            note_moyenne=4.5,
            nombre_avis=25
        )

        # 2. Produits et Publications Candidates
        cls.produit1 = Produit.objects.create(
            nom="Burger Scoring A",
            prix_base=2500.00,
            etablissement=cls.etablissement,
            categorie=cls.cat
        )
        cls.produit2 = Produit.objects.create(
            nom="Pizza Scoring B",
            prix_base=4500.00,
            etablissement=cls.etablissement,
            categorie=cls.cat
        )
        cls.pub1 = PublicationFeed.objects.create(
            etablissement=cls.etablissement,
            produit=cls.produit1,
            media_url="https://example.com/video1.mp4",
            nombre_likes=10,
            nombre_partages=2
        )
        cls.pub2 = PublicationFeed.objects.create(
            etablissement=cls.etablissement,
            produit=cls.produit2,
            media_url="https://example.com/video2.mp4",
            nombre_likes=50,
            nombre_partages=12
        )

        # 3. Utilisateur Authentifié avec Historique
        cls.user_auth = Utilisateur.objects.create(
            email="scoring.user@ayyou.sn",
            nom="ScoringUser",
            prenom="Test",
            numero_telephone="+221771111111"
        )
        # Télémétrie d'historique
        VideoEventLog.objects.create(
            utilisateur=cls.user_auth,
            publication=cls.pub1,
            session_id="hist_session_001",
            event_type="WATCH",
            watch_time_seconds=10.0,
            video_duration_seconds=15.0
        )

        # Client API
        cls.client = APIClient()

    def setUp(self):
        RecommendationScoringService.reset_cache()

    def test_01_model_loading(self):
        """Vérifie le chargement correct du modèle V2 et de ses métadonnées."""
        model, metadata = RecommendationScoringService.load_model()
        self.assertIsNotNone(model)
        self.assertIsInstance(metadata, dict)
        self.assertEqual(metadata.get('model_type'), 'LGBMRanker (LambdaMART)')

    def test_02_missing_model_file(self):
        """Vérifie qu'une exception FileNotFoundError est levée si le fichier modèle est absent."""
        with self.assertRaises(FileNotFoundError):
            RecommendationScoringService.load_model(model_path="models/recommender/non_existent_model.joblib")

    def test_03_score_single_candidate(self):
        """Vérifie le scoring d'une vidéo candidate unique."""
        results = RecommendationScoringService.score_candidates([self.pub1.id])
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['publication_id'], str(self.pub1.id))
        self.assertIn('predicted_score', results[0])
        self.assertEqual(results[0]['rank'], 1)

    def test_04_score_batch_candidates_and_rank_sorting(self):
        """Vérifie le scoring en lot (batch) et le tri par rang décroissant."""
        pub_ids = [self.pub1.id, self.pub2.id]
        results = RecommendationScoringService.score_candidates(pub_ids)
        self.assertEqual(len(results), 2)
        
        # Vérification du tri décroissant par score
        self.assertGreaterEqual(results[0]['predicted_score'], results[1]['predicted_score'])
        self.assertEqual(results[0]['rank'], 1)
        self.assertEqual(results[1]['rank'], 2)

    def test_05_authenticated_user_scoring(self):
        """Vérifie le scoring pour un utilisateur authentifié avec historique."""
        results = RecommendationScoringService.score_candidates(
            publication_ids=[self.pub1.id, self.pub2.id],
            user_id=self.user_auth.id
        )
        self.assertEqual(len(results), 2)

    def test_06_anonymous_visitor_scoring(self):
        """Vérifie le scoring pour un visiteur anonyme via session_id."""
        results = RecommendationScoringService.score_candidates(
            publication_ids=[self.pub1.id, self.pub2.id],
            session_id="anon_session_test_999"
        )
        self.assertEqual(len(results), 2)

    def test_07_cold_start_new_user(self):
        """Vérifie la robustesse en Cold Start pour un utilisateur nouvellement créé sans historique."""
        new_user = Utilisateur.objects.create(
            email="newbie@ayyou.sn",
            nom="Newbie",
            prenom="Test",
            numero_telephone="+221772222222"
        )
        results = RecommendationScoringService.score_candidates(
            publication_ids=[self.pub1.id],
            user_id=new_user.id
        )
        self.assertEqual(len(results), 1)
        self.assertIn('predicted_score', results[0])

    def test_08_cold_start_new_video(self):
        """Vérifie la robustesse en Cold Start pour une vidéo candidate nouvellement créée sans télémétrie."""
        new_pub = PublicationFeed.objects.create(
            etablissement=self.etablissement,
            produit=self.produit1,
            media_url="https://example.com/new_video.mp4"
        )
        results = RecommendationScoringService.score_candidates(
            publication_ids=[new_pub.id]
        )
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['publication_id'], str(new_pub.id))

    def test_09_feature_consistency_with_training(self):
        """Vérifie que la liste et l'ordre des features de FEATURE_COLUMNS sont 100% cohérents."""
        expected_features = [
            'is_authenticated',
            'user_account_age_days',
            'user_total_orders',
            'user_avg_order_amount',
            'user_total_likes',
            'user_total_events',
            'user_avg_watch_time',
            'user_avg_completion_rate',
            'user_top_category_id',
            'video_recency_hours',
            'video_duration_seconds',
            'video_total_likes',
            'video_total_shares',
            'dish_price',
            'dish_category_id',
            'resto_rating',
            'resto_reviews_count',
            'feed_position',
            'hour_of_day',
            'day_of_week'
        ]
        self.assertEqual(FEATURE_COLUMNS, expected_features)

        # Absence de toute fuite post-interaction dans FEATURE_COLUMNS
        leaked_columns = ['event_type', 'watch_time_seconds', 'completion_rate', 'is_skip', 'is_completed']
        for col in leaked_columns:
            self.assertNotIn(col, FEATURE_COLUMNS)

    def test_10_simulation_api_endpoint(self):
        """Vérifie l'endpoint de simulation d'API POST /api/telemetry/scoring/simulate/."""
        url = "/api/telemetry/scoring/simulate/"
        payload = {
            "publication_ids": [int(self.pub1.id), int(self.pub2.id)],
            "session_id": "api_sim_session_101"
        }
        response = self.client.post(url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK, f"Response error: {response.data}")
        data = response.json()
        self.assertEqual(data['status'], 'success')
        self.assertEqual(data['model_version'], 'recommender_lgbm_v2')
        self.assertEqual(data['candidates_count'], 2)
        self.assertEqual(len(data['ranked_candidates']), 2)
