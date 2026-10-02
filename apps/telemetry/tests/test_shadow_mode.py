import uuid
from unittest.mock import patch
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.users.models import Utilisateur
from apps.catalog.models import Etablissement, PublicationFeed, Produit, Categorie
from apps.telemetry.models import VideoEventLog, RecommendationShadowLog
from apps.telemetry.ml.shadow_service import RecommendationShadowService
from apps.telemetry.ml.scoring import RecommendationScoringService


class RecommendationShadowModeTestCase(TestCase):
    """
    Suite de tests complète pour la Phase 9 (Shadow Mode du Recommender V3).
    Vérifie le fonctionnement isolé, le déterminisme, le respect des feature flags,
    l'absence de régression du Feed et l'exécution non-bloquante.
    """

    def setUp(self):
        # 1. Utilisateur test
        self.user = Utilisateur.objects.create_user(
            email='shadow_tester@ayyou.com',
            numero_telephone='+221779998877',
            password='Password123!',
            nom='Tester',
            prenom='Shadow'
        )

        # 2. Catégorie et Etablissement PRO actif
        self.categorie = Categorie.objects.create(nom='Gourmet', est_active=True)
        self.etablissement = Etablissement.objects.create(
            proprietaire=self.user,
            nom='Restaurant Test Shadow',
            statut_abonnement=Etablissement.STATUT_ABONNEMENT_ACTIF,
            date_expiration_abonnement=timezone.now() + timezone.timedelta(days=30),
            type_etablissement=Etablissement.TYPE_RESTAURANT
        )

        # 3. Produits et Publications du Feed
        self.publications = []
        for i in range(1, 6):
            produit = Produit.objects.create(
                etablissement=self.etablissement,
                categorie=self.categorie,
                nom=f"Plat Shadow {i}",
                prix_base=1000.0 * i
            )
            pub = PublicationFeed.objects.create(
                etablissement=self.etablissement,
                produit=produit,
                media_url=f"https://cloudinary.com/video_{i}.mp4",
                type_media=PublicationFeed.TYPE_MEDIA_VIDEO,
                duree_video="1:30"
            )
            self.publications.append(pub)

        # 4. Télémétrie réelle minimale
        for pub in self.publications[:3]:
            VideoEventLog.objects.create(
                utilisateur=self.user,
                publication=pub,
                session_id='sess_test_shadow_init',
                event_type=VideoEventLog.EVENT_WATCH,
                watch_time_seconds=12.5,
                progress_percent=50.0
            )

        self.client = APIClient()

    def test_1_shadow_scoring_runs_and_logs(self):
        """Vérifie que le Shadow scoring s'exécute et génère des entrées dans RecommendationShadowLog."""
        pub_ids = [p.id for p in self.publications]
        logs_before = RecommendationShadowLog.objects.count()

        results = RecommendationShadowService.run_shadow_scoring(
            publication_ids=pub_ids,
            user=self.user,
            session_id='sess_shadow_test_1'
        )

        logs_after = RecommendationShadowLog.objects.count()
        self.assertEqual(len(results), len(pub_ids))
        self.assertEqual(logs_after - logs_before, len(pub_ids))

    def test_2_shadow_scoring_does_not_modify_feed(self):
        """Vérifie que le Feed réel reste 100% chronologique et inchangé lors d'un appel GET."""
        url = reverse('catalog:publication-feed-list')
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Extraire les IDs retournés
        data = response.json()
        items = data.get('results', data)
        returned_ids = [item['id'] for item in items]

        # L'ordre doit être strictement chronologique décroissant (-date_publication)
        expected_ids = list(PublicationFeed.objects.filter(
            etablissement__statut_abonnement=Etablissement.STATUT_ABONNEMENT_ACTIF
        ).order_by('-date_publication').values_list('id', flat=True))

        self.assertEqual(returned_ids, expected_ids)

    def test_3_shadow_scoring_non_blocking_on_error(self):
        """Vérifie qu'une erreur interne lors du scoring V3 n'altère pas la réponse 200 OK du Feed."""
        url = reverse('catalog:publication-feed-list')

        with patch.object(RecommendationScoringService, 'score_candidates', side_effect=RuntimeError("Simulated LGBM Failure")):
            response = self.client.get(url)
            self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_4_v3_error_feed_continues(self):
        """Vérifie que run_shadow_scoring capture les exceptions et retourne une liste vide sans planter."""
        pub_ids = [p.id for p in self.publications]

        with patch.object(RecommendationScoringService, 'score_candidates', side_effect=ValueError("Model Corrupted")):
            res = RecommendationShadowService.run_shadow_scoring(
                publication_ids=pub_ids,
                session_id='sess_err_test'
            )
            self.assertEqual(res, [])

    def test_5_model_version_is_v3(self):
        """Vérifie que la version du modèle enregistrée est obligatoirement 'v3'."""
        pub_ids = [p.id for p in self.publications]
        RecommendationShadowService.run_shadow_scoring(publication_ids=pub_ids, session_id='sess_v3_check')

        logs = RecommendationShadowLog.objects.filter(session_id='sess_v3_check')
        self.assertTrue(logs.exists())
        for log in logs:
            self.assertEqual(log.model_version, 'v3')

    def test_6_valid_scores_logged(self):
        """Vérifie que les scores prédits sont des nombres valides non nuls."""
        pub_ids = [p.id for p in self.publications]
        RecommendationShadowService.run_shadow_scoring(publication_ids=pub_ids, session_id='sess_score_check')

        logs = RecommendationShadowLog.objects.filter(session_id='sess_score_check')
        for log in logs:
            self.assertIsInstance(log.predicted_score, float)

    def test_7_valid_rankings_logged(self):
        """Vérifie que les rangs prédits couvrent de 1 à N sans doublons."""
        pub_ids = [p.id for p in self.publications]
        RecommendationShadowService.run_shadow_scoring(publication_ids=pub_ids, session_id='sess_rank_check')

        logs = RecommendationShadowLog.objects.filter(session_id='sess_rank_check')
        ranks = set(log.predicted_rank for log in logs)
        expected_ranks = set(range(1, len(pub_ids) + 1))
        self.assertEqual(ranks, expected_ranks)

    def test_8_session_id_preserved(self):
        """Vérifie que le session_id transmis est fidèlement conservé."""
        target_sess = 'sess_custom_identifier_999'
        pub_ids = [p.id for p in self.publications]
        RecommendationShadowService.run_shadow_scoring(publication_ids=pub_ids, session_id=target_sess)

        logs = RecommendationShadowLog.objects.filter(session_id=target_sess)
        self.assertEqual(logs.count(), len(pub_ids))

    def test_9_anonymous_user_accepted(self):
        """Vérifie qu'un utilisateur anonyme (user=None) est traité sans erreur."""
        pub_ids = [p.id for p in self.publications]
        RecommendationShadowService.run_shadow_scoring(publication_ids=pub_ids, user=None, session_id='sess_anon')

        logs = RecommendationShadowLog.objects.filter(session_id='sess_anon')
        self.assertEqual(logs.count(), len(pub_ids))
        for log in logs:
            self.assertIsNone(log.utilisateur)

    def test_10_authenticated_user_accepted(self):
        """Vérifie qu'un utilisateur authentifié est correctement rattaché aux logs."""
        pub_ids = [p.id for p in self.publications]
        RecommendationShadowService.run_shadow_scoring(publication_ids=pub_ids, user=self.user, session_id='sess_auth')

        logs = RecommendationShadowLog.objects.filter(session_id='sess_auth')
        self.assertEqual(logs.count(), len(pub_ids))
        for log in logs:
            self.assertEqual(log.utilisateur, self.user)

    @override_settings(SHADOW_RECOMMENDER_ENABLED=False)
    def test_11_feature_flag_disabled_no_shadow_logs(self):
        """Vérifie que lorsque SHADOW_RECOMMENDER_ENABLED=False, aucun log shadow n'est écrit."""
        pub_ids = [p.id for p in self.publications]
        logs_before = RecommendationShadowLog.objects.count()

        res = RecommendationShadowService.run_shadow_scoring(publication_ids=pub_ids, session_id='sess_flag_off')
        logs_after = RecommendationShadowLog.objects.count()

        self.assertEqual(res, [])
        self.assertEqual(logs_before, logs_after)

    @override_settings(SHADOW_RECOMMENDER_ENABLED=True)
    def test_12_feature_flag_enabled_shadow_logs_written(self):
        """Vérifie que lorsque SHADOW_RECOMMENDER_ENABLED=True, les logs shadow sont correctement écrits."""
        pub_ids = [p.id for p in self.publications]
        logs_before = RecommendationShadowLog.objects.count()

        res = RecommendationShadowService.run_shadow_scoring(publication_ids=pub_ids, session_id='sess_flag_on')
        logs_after = RecommendationShadowLog.objects.count()

        self.assertEqual(len(res), len(pub_ids))
        self.assertEqual(logs_after - logs_before, len(pub_ids))

    def test_13_no_synthetic_data_used(self):
        """Vérifie que les publications scorées proviennent uniquement de la base de données réelle."""
        pub_ids = [p.id for p in self.publications]
        RecommendationShadowService.run_shadow_scoring(publication_ids=pub_ids, session_id='sess_no_synth')

        logs = RecommendationShadowLog.objects.filter(session_id='sess_no_synth')
        logged_pub_ids = set(log.publication_id for log in logs)
        self.assertEqual(logged_pub_ids, set(pub_ids))

    def test_14_determinism_preserved(self):
        """Vérifie que 5 exécutions successives du Shadow mode produisent un classement identique."""
        pub_ids = [p.id for p in self.publications]

        rankings = []
        for run_idx in range(5):
            res = RecommendationShadowService.run_shadow_scoring(
                publication_ids=pub_ids,
                session_id=f"sess_det_{run_idx}"
            )
            rank_tuple = tuple((item['publication_id'], item['rank'], item['predicted_score']) for item in res)
            rankings.append(rank_tuple)

        # Tous les classements doivent être 100% identiques
        for i in range(1, 5):
            self.assertEqual(rankings[0], rankings[i])

    def test_15_feed_non_regression_strict(self):
        """Vérification explicite de non-régression de l'endpoint /api/catalog/feed/."""
        url = reverse('catalog:publication-feed-list')

        # 1. Premier appel
        res1 = self.client.get(url)
        self.assertEqual(res1.status_code, status.HTTP_200_OK)

        # 2. Deuxième appel
        res2 = self.client.get(url)
        self.assertEqual(res2.status_code, status.HTTP_200_OK)

        # 3. Comparaison stricte des réponses JSON
        self.assertEqual(res1.json(), res2.json())
