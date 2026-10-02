from django.test import TestCase
from django.utils import timezone
from apps.users.models import Utilisateur
from apps.catalog.models import Categorie, Etablissement, Produit, PublicationFeed
from apps.telemetry.models import VideoEventLog
from apps.telemetry.data_preparation import TelemetryDataCleaner, FeatureExtractor, DatasetBuilder


class DataPreparationTestCase(TestCase):
    def setUp(self):
        # User
        self.user = Utilisateur.objects.create_user(
            email='prep_user@ayyou.com',
            numero_telephone='+221771112233',
            password='Password123!',
            prenom='Prep',
            nom='Tester'
        )

        # Category
        self.categorie = Categorie.objects.create(
            nom='Burgers & Fast Food',
            slug='burgers'
        )

        # Etablissement
        self.etablissement = Etablissement.objects.create(
            nom='Burger King Dakar',
            statut_abonnement='ACTIF',
            note_moyenne=4.5,
            nombre_avis=120,
            type_etablissement='RESTAURANT'
        )

        # Produit
        self.produit = Produit.objects.create(
            etablissement=self.etablissement,
            categorie=self.categorie,
            nom='Double Cheese Burger',
            prix_base=3500.00
        )

        # Publication Feed
        self.publication = PublicationFeed.objects.create(
            etablissement=self.etablissement,
            produit=self.produit,
            media_url='https://res.cloudinary.com/ayyou/video/upload/v1/burger.mp4',
            type_media='video',
            nombre_likes=15,
            nombre_partages=3
        )

    def test_completion_rate_calculation_normal(self):
        rate = TelemetryDataCleaner.calculate_completion_rate(15.0, 20.0)
        self.assertEqual(rate, 0.75)

    def test_completion_rate_zero_and_null_protection(self):
        self.assertEqual(TelemetryDataCleaner.calculate_completion_rate(10.0, 0.0), 0.0)
        self.assertEqual(TelemetryDataCleaner.calculate_completion_rate(None, 20.0), 0.0)
        self.assertEqual(TelemetryDataCleaner.calculate_completion_rate(10.0, None), 0.0)
        self.assertEqual(TelemetryDataCleaner.calculate_completion_rate(-5.0, 20.0), 0.0)
        self.assertEqual(TelemetryDataCleaner.calculate_completion_rate(10.0, -20.0), 0.0)

    def test_completion_rate_clamping(self):
        rate = TelemetryDataCleaner.calculate_completion_rate(25.0, 20.0)
        self.assertEqual(rate, 1.0)

    def test_clean_event_invalid_exclusion(self):
        valid_event = {
            'publication_id': str(self.publication.id),
            'event_type': VideoEventLog.EVENT_PLAY,
            'watch_time_seconds': 5.0,
            'video_duration_seconds': 20.0
        }
        self.assertTrue(TelemetryDataCleaner.is_valid_event(valid_event))

        invalid_no_pub = {
            'event_type': VideoEventLog.EVENT_PLAY,
            'watch_time_seconds': 5.0
        }
        self.assertFalse(TelemetryDataCleaner.is_valid_event(invalid_no_pub))

        invalid_negative_wt = {
            'publication_id': str(self.publication.id),
            'event_type': VideoEventLog.EVENT_PLAY,
            'watch_time_seconds': -10.0
        }
        self.assertFalse(TelemetryDataCleaner.is_valid_event(invalid_negative_wt))

        invalid_unknown_type = {
            'publication_id': str(self.publication.id),
            'event_type': 'INVALID_TYPE_XYZ',
            'watch_time_seconds': 5.0
        }
        self.assertFalse(TelemetryDataCleaner.is_valid_event(invalid_unknown_type))

    def test_extract_user_features_authenticated_and_anonymous(self):
        # Auth User
        feats_auth = FeatureExtractor.extract_user_features(user_id=self.user.id)
        self.assertTrue(feats_auth['is_authenticated'])
        self.assertEqual(feats_auth['user_total_orders'], 0)

        # Anon Session
        feats_anon = FeatureExtractor.extract_user_features(session_id='anon_sess_999')
        self.assertFalse(feats_anon['is_authenticated'])
        self.assertEqual(feats_anon['user_total_events'], 0)

    def test_extract_video_features(self):
        feats = FeatureExtractor.extract_video_features(self.publication.id)
        self.assertEqual(feats['dish_price'], 3500.00)
        self.assertEqual(feats['dish_category_id'], self.categorie.id)
        self.assertEqual(feats['resto_rating'], 4.5)
        self.assertEqual(feats['video_total_likes'], 15)

    def test_relevance_label_scoring(self):
        self.assertEqual(DatasetBuilder.compute_relevance_label(VideoEventLog.EVENT_CART_ADD, 0.5), 4)
        self.assertEqual(DatasetBuilder.compute_relevance_label(VideoEventLog.EVENT_DISH_CLICK, 0.2), 4)
        self.assertEqual(DatasetBuilder.compute_relevance_label(VideoEventLog.EVENT_LIKE, 0.8), 3)
        self.assertEqual(DatasetBuilder.compute_relevance_label(VideoEventLog.EVENT_SHARE, 0.4), 3)
        self.assertEqual(DatasetBuilder.compute_relevance_label(VideoEventLog.EVENT_COMPLETED, 1.0), 2)
        self.assertEqual(DatasetBuilder.compute_relevance_label(VideoEventLog.EVENT_WATCH, 0.95), 2)
        self.assertEqual(DatasetBuilder.compute_relevance_label(VideoEventLog.EVENT_SKIP, 0.05), 0)
        self.assertEqual(DatasetBuilder.compute_relevance_label(VideoEventLog.EVENT_WATCH, 0.30), 1)

    def test_build_dataset_row(self):
        event = VideoEventLog.objects.create(
            utilisateur=self.user,
            publication=self.publication,
            session_id='test_sess_001',
            event_type=VideoEventLog.EVENT_COMPLETED,
            watch_time_seconds=20.0,
            video_duration_seconds=20.0,
            progress_percent=100.0,
            feed_position=0
        )
        row = DatasetBuilder.build_dataset_row(event)
        self.assertIsNotNone(row)
        self.assertEqual(row['query_session_id'], 'test_sess_001')
        self.assertEqual(row['user_id'], self.user.id)
        self.assertEqual(row['publication_id'], str(self.publication.id))
        self.assertEqual(row['target_relevance'], 2)
        self.assertEqual(row['completion_rate'], 1.0)
        self.assertEqual(row['dish_price'], 3500.00)

    def test_cold_start_handling(self):
        # New User with 0 interactions/events & New Video
        new_pub = PublicationFeed.objects.create(
            etablissement=self.etablissement,
            media_url='https://res.cloudinary.com/ayyou/video/upload/v1/new_video.mp4',
            type_media='video'
        )
        event = VideoEventLog.objects.create(
            publication=new_pub,
            session_id='cold_session_777',
            event_type=VideoEventLog.EVENT_IMPRESSION,
            watch_time_seconds=0.0,
            video_duration_seconds=15.0,
            feed_position=3
        )
        row = DatasetBuilder.build_dataset_row(event)
        self.assertIsNotNone(row)
        self.assertEqual(row['user_total_orders'], 0)
        self.assertEqual(row['user_total_events'], 0, "L'événement lui-même ne doit pas figurer dans ses propres features historiques (0 event avant event)")
        self.assertIsNone(row['user_id'])
        self.assertEqual(row['dish_price'], 0.0)
