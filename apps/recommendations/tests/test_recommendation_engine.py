from datetime import timedelta
from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone
from django.contrib.auth import get_user_model

from apps.catalog.models import Categorie, Etablissement, Produit, PublicationFeed, LikeProduit
from apps.telemetry.models import VideoEventLog
from apps.recommendations.configuration import EngineConfig
from apps.recommendations.services import (
    InteractionService,
    AffinityService,
    FreshnessService,
    PopularityService,
    ScoringService,
    DiversificationService,
    RecommendationService,
)

User = get_user_model()


class RecommendationEngineTestCase(TestCase):
    def setUp(self):
        # 1. Création des utilisateurs
        self.user = User.objects.create_user(
            numero_telephone="+221770000000",
            email="client_test@ayyou.com",
            password="password123",
            nom="Diop",
            prenom="Awa"
        )

        # 2. Création des catégories
        self.cat_senegal = Categorie.objects.create(nom="Cuisine Sénégalaise", slug="cuisine-senegalaise", ordre=1)
        self.cat_fastfood = Categorie.objects.create(nom="Fast Food Dakar", slug="fast-food-dakar", ordre=2)

        # 3. Création des établissements
        now = timezone.now()
        exp_date = now + timedelta(days=30)

        self.etab_1 = Etablissement.objects.create(
            nom="Chez Loutcha",
            type_etablissement="RESTAURANT",
            adresse="Dakar Plateau",
            statut_abonnement=Etablissement.STATUT_ABONNEMENT_ACTIF,
            date_expiration_abonnement=exp_date
        )
        self.etab_2 = Etablissement.objects.create(
            nom="Burger Dakar",
            type_etablissement="RESTAURANT",
            adresse="Almadies",
            statut_abonnement=Etablissement.STATUT_ABONNEMENT_ACTIF,
            date_expiration_abonnement=exp_date
        )

        # 4. Création des produits
        self.prod_thieb = Produit.objects.create(
            etablissement=self.etab_1,
            categorie=self.cat_senegal,
            nom="Thiéboudienne Penda Mbaye",
            prix_base=3500,
            image_url="http://example.com/thieb.jpg"
        )
        self.prod_burger = Produit.objects.create(
            etablissement=self.etab_2,
            categorie=self.cat_fastfood,
            nom="Double Cheese Burger",
            prix_base=4500,
            image_url="http://example.com/burger.jpg"
        )

        # 5. Création des publications vidéo
        self.pub_1 = PublicationFeed.objects.create(
            etablissement=self.etab_1,
            produit=self.prod_thieb,
            media_url="http://example.com/video_thieb.mp4",
            type_media=PublicationFeed.TYPE_MEDIA_VIDEO,
            nombre_likes=10,
            nombre_partages=2,
            date_publication=now - timedelta(days=1)
        )
        self.pub_2 = PublicationFeed.objects.create(
            etablissement=self.etab_2,
            produit=self.prod_burger,
            media_url="http://example.com/video_burger.mp4",
            type_media=PublicationFeed.TYPE_MEDIA_VIDEO,
            nombre_likes=5,
            nombre_partages=0,
            date_publication=now - timedelta(days=2)
        )

    def test_cold_start_ranking(self):
        """
        Vérifie qu'un nouvel utilisateur sans historique reçoit les vidéos
        triées déterministement par fraîcheur et popularité.
        """
        pubs = RecommendationService.get_recommended_feed(user=None, session_id="anon_123")
        self.assertEqual(len(pubs), 2)
        # pub_1 est plus récente (1 jour vs 2 jours) et plus populaire (10 likes vs 5)
        self.assertEqual(pubs[0].id, self.pub_1.id)

    def test_active_user_affinity(self):
        """
        Vérifie qu'un utilisateur actif ayant complété une vidéo de Burger
        voit le Burger remonter en première position malgré la fraîcheur du Thieb.
        """
        # Log un événement complet sur le Burger
        VideoEventLog.objects.create(
            utilisateur=self.user,
            publication=self.pub_2,
            event_type=VideoEventLog.EVENT_COMPLETED,
            watch_time_seconds=30.0,
            video_duration_seconds=30.0,
            progress_percent=100.0
        )

        pubs = RecommendationService.get_recommended_feed(user=self.user)
        self.assertEqual(pubs[0].id, self.pub_2.id)

    def test_skip_penalty(self):
        """
        Vérifie qu'un zappe rapide (< 3s) applique une pénalité déterministe negative.
        """
        # L'utilisateur zappe la vidéo de Burger
        VideoEventLog.objects.create(
            utilisateur=self.user,
            publication=self.pub_2,
            event_type=VideoEventLog.EVENT_SKIP,
            watch_time_seconds=1.5,
            video_duration_seconds=30.0,
            progress_percent=5.0
        )

        user_data = InteractionService.extract_user_interaction_data(user=self.user)
        self.assertIn(self.pub_2.id, user_data.video_scores)
        self.assertLess(user_data.video_scores[self.pub_2.id], 0.0)

    def test_time_decay(self):
        """
        Vérifie que la décroissance temporelle réduit le poids des évènements anciens (7 jours demi-vie).
        """
        now = timezone.now()
        past_7d = now - timedelta(days=7)

        decay_recent = InteractionService.calculate_time_decay(now, ref_now=now)
        decay_old = InteractionService.calculate_time_decay(past_7d, ref_now=now)

        self.assertAlmostEqual(decay_recent, 1.0, places=4)
        self.assertAlmostEqual(decay_old, 0.5, places=2)

    def test_freshness_bonus(self):
        """
        Vérifie le calcul du bonus de fraîcheur en fonction de l'âge de la publication.
        """
        now = timezone.now()
        fresh_score = FreshnessService.calculate_freshness_score(now, ref_now=now)
        old_score = FreshnessService.calculate_freshness_score(now - timedelta(days=3), ref_now=now)

        self.assertAlmostEqual(fresh_score, EngineConfig.MAX_FRESHNESS_BONUS, places=4)
        self.assertAlmostEqual(old_score, EngineConfig.MAX_FRESHNESS_BONUS * 0.5, places=2)

    def test_popularity_score_cap(self):
        """
        Vérifie que le score de popularité plafonne bien à MAX_POPULARITY_SCORE.
        """
        pop_score = PopularityService.calculate_popularity_score(likes_count=1000, shares_count=500)
        self.assertEqual(pop_score, EngineConfig.MAX_POPULARITY_SCORE)

    def test_fallback_on_exception(self):
        """
        Vérifie qu'en cas d'erreur inattendue, le service bascule de manière sécurisée
        sur le feed chronologique pur sans faire crasher la requête.
        """
        queryset = PublicationFeed.objects.filter(type_media=PublicationFeed.TYPE_MEDIA_VIDEO)

        with patch('apps.recommendations.services.interaction_service.InteractionService.extract_user_interaction_data', side_effect=ValueError("Simulated Error")):
            pubs = RecommendationService.rank_publications(queryset, user=self.user)
            self.assertEqual(len(pubs), 2)
