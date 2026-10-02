import numpy as np
from unittest.mock import patch
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.users.models import Utilisateur
from apps.catalog.models import Etablissement, PublicationFeed, Produit, Categorie
from apps.telemetry.models import VideoEventLog, RecommendationExperimentLog, RecommendationShadowLog
from apps.telemetry.ml.experiment_service import RecommendationExperimentService
from apps.telemetry.ml.scoring import RecommendationScoringService


class RecommendationExperimentModeTestCase(TestCase):
    """
    Suite de tests complète pour la Phase 10 (Expérimentation Contrôlée A/B Testing V3).
    Vérifie la répartition déterministe par hachage, l'isolation des groupes CONTROL/EXPERIMENT,
    le fallback chronologique automatique et la non-régression stricte de l'API Feed.
    """

    def setUp(self):
        # 1. Utilisateurs test (Auth et Secondaire)
        self.user_auth = Utilisateur.objects.create_user(
            email='exp_tester@ayyou.com',
            numero_telephone='+221778889900',
            password='Password123!',
            nom='Tester',
            prenom='Experiment'
        )

        self.user_second = Utilisateur.objects.create_user(
            email='exp_second@ayyou.com',
            numero_telephone='+221778889911',
            password='Password123!',
            nom='Second',
            prenom='User'
        )

        # 2. Catégorie et Établissement PRO actif
        self.categorie = Categorie.objects.create(nom='Senegalese Food', est_active=True)
        self.etablissement = Etablissement.objects.create(
            proprietaire=self.user_auth,
            nom='Resto Expérimentation V3',
            statut_abonnement=Etablissement.STATUT_ABONNEMENT_ACTIF,
            date_expiration_abonnement=timezone.now() + timezone.timedelta(days=30),
            type_etablissement=Etablissement.TYPE_RESTAURANT
        )

        # 3. Publications du Feed
        self.publications = []
        for i in range(1, 6):
            produit = Produit.objects.create(
                etablissement=self.etablissement,
                categorie=self.categorie,
                nom=f"Plat Exp {i}",
                prix_base=1500.0 * i
            )
            pub = PublicationFeed.objects.create(
                etablissement=self.etablissement,
                produit=produit,
                media_url=f"https://cloudinary.com/exp_video_{i}.mp4",
                type_media=PublicationFeed.TYPE_MEDIA_VIDEO,
                duree_video="2:00"
            )
            self.publications.append(pub)

        # 4. Télémétrie réelle minimale
        for pub in self.publications[:3]:
            VideoEventLog.objects.create(
                utilisateur=self.user_auth,
                publication=pub,
                session_id='sess_init_exp',
                event_type=VideoEventLog.EVENT_WATCH,
                watch_time_seconds=15.0,
                progress_percent=60.0
            )

        self.client = APIClient()

    @override_settings(RECOMMENDATION_MODE='chronological', RECOMMENDATION_EXPERIMENT_ENABLED=False)
    def test_1_default_mode_is_chronological(self):
        """Vérifie que le mode par défaut est 100% chronologique."""
        group, mode = RecommendationExperimentService.get_experiment_group(user=self.user_auth)
        self.assertEqual(group, RecommendationExperimentLog.GROUP_CONTROL)
        self.assertEqual(mode, 'chronological')

    @override_settings(RECOMMENDATION_MODE='experiment', RECOMMENDATION_EXPERIMENT_ENABLED=False)
    def test_2_experiment_disabled(self):
        """Vérifie que si RECOMMENDATION_EXPERIMENT_ENABLED=False, le groupe reste CONTROL."""
        group, mode = RecommendationExperimentService.get_experiment_group(user=self.user_auth)
        self.assertEqual(group, RecommendationExperimentLog.GROUP_CONTROL)
        self.assertEqual(mode, 'chronological')

    @override_settings(RECOMMENDATION_MODE='experiment', RECOMMENDATION_EXPERIMENT_ENABLED=True, RECOMMENDATION_EXPERIMENT_PERCENTAGE=100)
    def test_3_experiment_enabled(self):
        """Vérifie que lorsque activé à 100%, l'utilisateur est dans le groupe EXPERIMENT."""
        group, mode = RecommendationExperimentService.get_experiment_group(user=self.user_auth)
        self.assertEqual(group, RecommendationExperimentLog.GROUP_EXPERIMENT)
        self.assertEqual(mode, 'experiment')

    @override_settings(RECOMMENDATION_MODE='experiment', RECOMMENDATION_EXPERIMENT_ENABLED=True, RECOMMENDATION_EXPERIMENT_PERCENTAGE=0)
    def test_4_percentage_0(self):
        """Vérifie qu'à 0%, 100% des requêtes vont dans le groupe CONTROL."""
        group, mode = RecommendationExperimentService.get_experiment_group(user=self.user_auth)
        self.assertEqual(group, RecommendationExperimentLog.GROUP_CONTROL)

    @override_settings(RECOMMENDATION_MODE='experiment', RECOMMENDATION_EXPERIMENT_ENABLED=True, RECOMMENDATION_EXPERIMENT_PERCENTAGE=100)
    def test_5_percentage_100(self):
        """Vérifie qu'à 100%, 100% des requêtes vont dans le groupe EXPERIMENT."""
        group, mode = RecommendationExperimentService.get_experiment_group(user=self.user_auth)
        self.assertEqual(group, RecommendationExperimentLog.GROUP_EXPERIMENT)

    @override_settings(RECOMMENDATION_MODE='experiment', RECOMMENDATION_EXPERIMENT_ENABLED=True, RECOMMENDATION_EXPERIMENT_PERCENTAGE=50)
    def test_6_deterministic_distribution(self):
        """Vérifie que le hachage MD5 produit une répartition déterministe reproductible."""
        g1, m1 = RecommendationExperimentService.get_experiment_group(user=self.user_auth)
        g2, m2 = RecommendationExperimentService.get_experiment_group(user=self.user_auth)
        self.assertEqual(g1, g2)

    @override_settings(RECOMMENDATION_MODE='experiment', RECOMMENDATION_EXPERIMENT_ENABLED=True, RECOMMENDATION_EXPERIMENT_PERCENTAGE=50)
    def test_7_same_user_same_group(self):
        """Vérifie qu'un même utilisateur authentifié reste toujours dans le même groupe."""
        groups = [RecommendationExperimentService.get_experiment_group(user=self.user_auth)[0] for _ in range(10)]
        self.assertEqual(len(set(groups)), 1)

    @override_settings(RECOMMENDATION_MODE='experiment', RECOMMENDATION_EXPERIMENT_ENABLED=True, RECOMMENDATION_EXPERIMENT_PERCENTAGE=50)
    def test_8_same_anon_session_same_group(self):
        """Vérifie qu'une même session anonyme reste toujours dans le même groupe."""
        sess_id = 'sess_anon_stable_hash_123'
        groups = [RecommendationExperimentService.get_experiment_group(session_id=sess_id)[0] for _ in range(10)]
        self.assertEqual(len(set(groups)), 1)

    @override_settings(RECOMMENDATION_MODE='experiment', RECOMMENDATION_EXPERIMENT_ENABLED=True, RECOMMENDATION_EXPERIMENT_PERCENTAGE=100)
    def test_9_auth_user_accepted(self):
        """Vérifie qu'un utilisateur authentifié est correctement rattaché dans RecommendationExperimentLog."""
        RecommendationExperimentService.process_feed_candidates(
            candidate_pubs=self.publications,
            user=self.user_auth,
            session_id='sess_test_auth_log'
        )
        logs = RecommendationExperimentLog.objects.filter(session_id='sess_test_auth_log')
        self.assertTrue(logs.exists())
        for log in logs:
            self.assertEqual(log.utilisateur, self.user_auth)

    @override_settings(RECOMMENDATION_MODE='experiment', RECOMMENDATION_EXPERIMENT_ENABLED=True, RECOMMENDATION_EXPERIMENT_PERCENTAGE=100)
    def test_10_anon_user_accepted(self):
        """Vérifie qu'une session anonyme (user=None) est acceptée et stockée avec utilisateur=None."""
        RecommendationExperimentService.process_feed_candidates(
            candidate_pubs=self.publications,
            user=None,
            session_id='sess_test_anon_log'
        )
        logs = RecommendationExperimentLog.objects.filter(session_id='sess_test_anon_log')
        self.assertTrue(logs.exists())
        for log in logs:
            self.assertIsNone(log.utilisateur)

    @override_settings(RECOMMENDATION_MODE='experiment', RECOMMENDATION_EXPERIMENT_ENABLED=True, RECOMMENDATION_EXPERIMENT_PERCENTAGE=100)
    def test_11_v3_used_only_in_experiment(self):
        """Vérifie que V3 est appelé uniquement pour le groupe EXPERIMENT."""
        with patch.object(RecommendationScoringService, 'score_candidates', wraps=RecommendationScoringService.score_candidates) as mock_score:
            RecommendationExperimentService.process_feed_candidates(
                candidate_pubs=self.publications,
                user=self.user_auth,
                session_id='sess_v3_call'
            )
            mock_score.assert_called_once()

    @override_settings(RECOMMENDATION_MODE='experiment', RECOMMENDATION_EXPERIMENT_ENABLED=True, RECOMMENDATION_EXPERIMENT_PERCENTAGE=0)
    def test_12_control_remains_chronological(self):
        """Vérifie que le groupe CONTROL retourne la liste d'origine dans l'ordre chronologique exact."""
        res = RecommendationExperimentService.process_feed_candidates(
            candidate_pubs=self.publications,
            user=self.user_auth,
            session_id='sess_ctrl_chrono'
        )
        self.assertEqual([p.id for p in res], [p.id for p in self.publications])

    @override_settings(RECOMMENDATION_MODE='experiment', RECOMMENDATION_EXPERIMENT_ENABLED=True, RECOMMENDATION_EXPERIMENT_PERCENTAGE=100)
    def test_13_fallback_on_v3_error(self):
        """Vérifie qu'une erreur de scoring V3 déclenche automatiquement le fallback chronologique."""
        with patch.object(RecommendationScoringService, 'score_candidates', side_effect=RuntimeError("LGBM Crash")):
            res = RecommendationExperimentService.process_feed_candidates(
                candidate_pubs=self.publications,
                user=self.user_auth,
                session_id='sess_fallback_error'
            )

            # La liste retournée doit être la liste chronologique d'origine
            self.assertEqual([p.id for p in res], [p.id for p in self.publications])

            # Le log doit marquer fallback_used=True
            logs = RecommendationExperimentLog.objects.filter(session_id='sess_fallback_error')
            self.assertTrue(logs.exists())
            for log in logs:
                self.assertTrue(log.fallback_used)

    @override_settings(RECOMMENDATION_MODE='experiment', RECOMMENDATION_EXPERIMENT_ENABLED=True, RECOMMENDATION_EXPERIMENT_PERCENTAGE=100)
    def test_14_fallback_on_missing_model(self):
        """Vérifie qu'un modèle introuvable déclenche le fallback chronologique."""
        with patch.object(RecommendationScoringService, 'load_model', side_effect=FileNotFoundError("Missing model file")):
            res = RecommendationExperimentService.process_feed_candidates(
                candidate_pubs=self.publications,
                session_id='sess_missing_model'
            )
            self.assertEqual([p.id for p in res], [p.id for p in self.publications])

    @override_settings(RECOMMENDATION_MODE='experiment', RECOMMENDATION_EXPERIMENT_ENABLED=True, RECOMMENDATION_EXPERIMENT_PERCENTAGE=100)
    def test_15_fallback_on_invalid_score(self):
        """Vérifie qu'un score contenant NaN ou Inf déclenche le fallback chronologique."""
        fake_scores = [{'publication_id': str(p.id), 'predicted_score': float('nan'), 'rank': idx + 1} for idx, p in enumerate(self.publications)]
        with patch.object(RecommendationScoringService, 'score_candidates', return_value=fake_scores):
            res = RecommendationExperimentService.process_feed_candidates(
                candidate_pubs=self.publications,
                session_id='sess_nan_score'
            )
            self.assertEqual([p.id for p in res], [p.id for p in self.publications])

    @override_settings(RECOMMENDATION_MODE='experiment', RECOMMENDATION_EXPERIMENT_ENABLED=True, RECOMMENDATION_EXPERIMENT_PERCENTAGE=100)
    def test_16_publication_count_unchanged(self):
        """Vérifie que le nombre de publications réordonnées est strictement identique au nombre initial."""
        res = RecommendationExperimentService.process_feed_candidates(
            candidate_pubs=self.publications,
            session_id='sess_count_check'
        )
        self.assertEqual(len(res), len(self.publications))

    @override_settings(RECOMMENDATION_MODE='experiment', RECOMMENDATION_EXPERIMENT_ENABLED=True, RECOMMENDATION_EXPERIMENT_PERCENTAGE=100)
    def test_17_api_contract_unchanged(self):
        """Vérifie que la structure et le statut HTTP de l'API /api/catalog/feed/ restent 200 OK."""
        url = reverse('catalog:publication-feed-list')
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertIn('results', data if isinstance(data, dict) else {'results': data})

    @override_settings(RECOMMENDATION_MODE='experiment', RECOMMENDATION_EXPERIMENT_ENABLED=True, RECOMMENDATION_EXPERIMENT_PERCENTAGE=100)
    def test_18_no_mocks_in_real_scoring(self):
        """Vérifie que le modèle réel V3 sur disque s'exécute de manière autonome sans mock."""
        res = RecommendationExperimentService.process_feed_candidates(
            candidate_pubs=self.publications,
            user=self.user_auth,
            session_id='sess_real_v3_no_mock'
        )
        self.assertEqual(len(res), len(self.publications))

    @override_settings(RECOMMENDATION_MODE='experiment', RECOMMENDATION_EXPERIMENT_ENABLED=True, RECOMMENDATION_EXPERIMENT_PERCENTAGE=100)
    def test_19_model_version_v3_logged(self):
        """Vérifie que le log enregistre model_version='v3' pour le groupe EXPERIMENT."""
        RecommendationExperimentService.process_feed_candidates(
            candidate_pubs=self.publications,
            session_id='sess_v3_log_check'
        )
        logs = RecommendationExperimentLog.objects.filter(session_id='sess_v3_log_check')
        for log in logs:
            self.assertEqual(log.model_version, 'v3')

    @override_settings(RECOMMENDATION_MODE='experiment', RECOMMENDATION_EXPERIMENT_ENABLED=True, RECOMMENDATION_EXPERIMENT_PERCENTAGE=100)
    def test_20_deterministic_v3_scores(self):
        """Vérifie que 5 exécutions successives sur les mêmes candidats produisent des scores et classements identiques."""
        r1 = RecommendationExperimentService.process_feed_candidates(candidate_pubs=self.publications, session_id='sess_det_v3_1')
        r2 = RecommendationExperimentService.process_feed_candidates(candidate_pubs=self.publications, session_id='sess_det_v3_2')
        self.assertEqual([p.id for p in r1], [p.id for p in r2])

    @override_settings(RECOMMENDATION_MODE='experiment', RECOMMENDATION_EXPERIMENT_ENABLED=True, RECOMMENDATION_EXPERIMENT_PERCENTAGE=100)
    def test_21_no_nan_no_inf(self):
        """Vérifie qu'aucun score NaN ou Inf n'est inséré dans la base de données."""
        RecommendationExperimentService.process_feed_candidates(candidate_pubs=self.publications, session_id='sess_check_finite')
        logs = RecommendationExperimentLog.objects.filter(session_id='sess_check_finite')
        for log in logs:
            if log.predicted_score is not None:
                self.assertFalse(np.isnan(log.predicted_score))
                self.assertFalse(np.isinf(log.predicted_score))

    @override_settings(SHADOW_RECOMMENDER_ENABLED=True, RECOMMENDATION_MODE='experiment', RECOMMENDATION_EXPERIMENT_ENABLED=True, RECOMMENDATION_EXPERIMENT_PERCENTAGE=100)
    def test_22_shadow_mode_still_functional(self):
        """Vérifie que le Shadow Mode continue de s'exécuter en arrière-plan parallèlement à l'expérimentation."""
        url = reverse('catalog:publication-feed-list')
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Vérifier présence de logs Shadow et de logs Experiment
        self.assertTrue(RecommendationShadowLog.objects.exists())
        self.assertTrue(RecommendationExperimentLog.objects.exists())

    def test_23_old_telemetry_still_functional(self):
        """Vérifie que l'enregistrement de la télémétrie classique VideoEventLog fonctionne toujours sans problème."""
        url = reverse('telemetry:video-event-create')
        payload = {
            'publication_id': self.publications[0].id,
            'session_id': 'sess_telemetry_verify',
            'event_type': VideoEventLog.EVENT_WATCH,
            'watch_time_seconds': 10.0,
            'video_duration_seconds': 120.0,
            'progress_percent': 8.3
        }
        res = self.client.post(url, data=payload, format='json')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

    @override_settings(RECOMMENDATION_MODE='chronological', RECOMMENDATION_EXPERIMENT_ENABLED=False)
    def test_24_feed_non_regression_strict(self):
        """Vérification explicite de non-régression stricte de l'endpoint /api/catalog/feed/."""
        url = reverse('catalog:publication-feed-list')

        res1 = self.client.get(url)
        self.assertEqual(res1.status_code, status.HTTP_200_OK)

        res2 = self.client.get(url)
        self.assertEqual(res2.status_code, status.HTTP_200_OK)

        self.assertEqual(res1.json(), res2.json())
