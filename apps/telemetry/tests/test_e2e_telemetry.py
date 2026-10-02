from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.users.models import Utilisateur
from apps.catalog.models import Categorie, Etablissement, Produit, PublicationFeed
from apps.telemetry.models import VideoEventLog
from apps.telemetry.data_preparation import DatasetBuilder, TelemetryDataCleaner, FeatureExtractor


class EndToEndTelemetryTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()

        # User
        self.user = Utilisateur.objects.create_user(
            email='e2e_user@ayyou.com',
            numero_telephone='+221778889900',
            password='Password123!',
            prenom='E2E',
            nom='Tester'
        )

        # Categorie
        self.categorie = Categorie.objects.create(
            nom='Thiéboudienne & Rice',
            slug='thieb'
        )

        # Etablissement
        self.etablissement = Etablissement.objects.create(
            nom='Le Lagon Dakar',
            statut_abonnement='ACTIF',
            note_moyenne=4.8,
            nombre_avis=250,
            type_etablissement='RESTAURANT'
        )

        # Produits
        self.produit_1 = Produit.objects.create(
            etablissement=self.etablissement,
            categorie=self.categorie,
            nom='Thiéboudienne Penda Mbaye',
            prix_base=2500.00
        )
        self.produit_2 = Produit.objects.create(
            etablissement=self.etablissement,
            categorie=self.categorie,
            nom='Yassa Poulet',
            prix_base=2000.00
        )
        self.produit_3 = Produit.objects.create(
            etablissement=self.etablissement,
            categorie=self.categorie,
            nom='Mafé Viande',
            prix_base=3000.00
        )

        # Publications Feed
        self.pub_1 = PublicationFeed.objects.create(
            etablissement=self.etablissement,
            produit=self.produit_1,
            media_url='https://res.cloudinary.com/ayyou/video/upload/v1/thieb.mp4',
            type_media='video',
            nombre_likes=42,
            nombre_partages=8
        )
        self.pub_2 = PublicationFeed.objects.create(
            etablissement=self.etablissement,
            produit=self.produit_2,
            media_url='https://res.cloudinary.com/ayyou/video/upload/v1/yassa.mp4',
            type_media='video',
            nombre_likes=10,
            nombre_partages=1
        )
        self.pub_3 = PublicationFeed.objects.create(
            etablissement=self.etablissement,
            produit=self.produit_3,
            media_url='https://res.cloudinary.com/ayyou/video/upload/v1/mafe.mp4',
            type_media='video',
            nombre_likes=88,
            nombre_partages=15
        )

        self.url_batch = reverse('telemetry:video-event-batch-create')
        self.url_single = reverse('telemetry:video-event-create')

    def test_scenario_session_a_anonymous(self):
        """
        Scénario Session A (Visiteur anonyme):
        - Vidéo 1 : impression, play, watch, pause
        - Vidéo 2 : impression, play, skip
        - Vidéo 3 : impression, play, completed, dish_click, cart_add
        """
        session_id_a = 'session_A_e2e_123'

        batch_payload = {
            'events': [
                # Vidéo 1
                {
                    'publication_id': str(self.pub_1.id),
                    'session_id': session_id_a,
                    'event_type': VideoEventLog.EVENT_IMPRESSION,
                    'feed_position': 0
                },
                {
                    'publication_id': str(self.pub_1.id),
                    'session_id': session_id_a,
                    'event_type': VideoEventLog.EVENT_PLAY,
                    'feed_position': 0
                },
                {
                    'publication_id': str(self.pub_1.id),
                    'session_id': session_id_a,
                    'event_type': VideoEventLog.EVENT_PAUSE,
                    'watch_time_seconds': 10.0,
                    'video_duration_seconds': 30.0,
                    'progress_percent': 33.3,
                    'feed_position': 0
                },
                # Vidéo 2 (Skip)
                {
                    'publication_id': str(self.pub_2.id),
                    'session_id': session_id_a,
                    'event_type': VideoEventLog.EVENT_IMPRESSION,
                    'feed_position': 1
                },
                {
                    'publication_id': str(self.pub_2.id),
                    'session_id': session_id_a,
                    'event_type': VideoEventLog.EVENT_PLAY,
                    'feed_position': 1
                },
                {
                    'publication_id': str(self.pub_2.id),
                    'session_id': session_id_a,
                    'event_type': VideoEventLog.EVENT_SKIP,
                    'watch_time_seconds': 1.5,
                    'video_duration_seconds': 20.0,
                    'progress_percent': 7.5,
                    'feed_position': 1
                },
                # Vidéo 3 (Completion & Conversion)
                {
                    'publication_id': str(self.pub_3.id),
                    'session_id': session_id_a,
                    'event_type': VideoEventLog.EVENT_IMPRESSION,
                    'feed_position': 2
                },
                {
                    'publication_id': str(self.pub_3.id),
                    'session_id': session_id_a,
                    'event_type': VideoEventLog.EVENT_PLAY,
                    'feed_position': 2
                },
                {
                    'publication_id': str(self.pub_3.id),
                    'session_id': session_id_a,
                    'event_type': VideoEventLog.EVENT_COMPLETED,
                    'watch_time_seconds': 20.0,
                    'video_duration_seconds': 20.0,
                    'progress_percent': 100.0,
                    'feed_position': 2
                },
                {
                    'publication_id': str(self.pub_3.id),
                    'session_id': session_id_a,
                    'event_type': VideoEventLog.EVENT_DISH_CLICK,
                    'feed_position': 2
                },
                {
                    'publication_id': str(self.pub_3.id),
                    'session_id': session_id_a,
                    'event_type': VideoEventLog.EVENT_CART_ADD,
                    'feed_position': 2
                }
            ]
        }

        response = self.client.post(self.url_batch, batch_payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # 1. Vérification en base VideoEventLog
        logs = VideoEventLog.objects.filter(session_id=session_id_a).order_by('id')
        self.assertEqual(logs.count(), 11)

        # Vérification des événements anonymes (utilisateur is None)
        for log in logs:
            self.assertIsNone(log.utilisateur)
            self.assertEqual(log.session_id, session_id_a)

        # 2. Vérification de la transmission au DatasetBuilder
        dataset = DatasetBuilder.build_training_dataset(queryset=logs)
        self.assertEqual(len(dataset), 11)

        # Target Relevance Scores
        targets = [row['target_relevance'] for row in dataset]
        # Vidéo 1 PAUSE -> 1
        # Vidéo 2 SKIP -> 0
        # Vidéo 3 COMPLETED -> 2
        # Vidéo 3 DISH_CLICK / CART_ADD -> 4
        self.assertIn(0, targets)
        self.assertIn(1, targets)
        self.assertIn(2, targets)
        self.assertIn(4, targets)

    def test_scenario_session_b_authenticated(self):
        """
        Scénario Session B (Utilisateur connecté):
        - Vidéo 1 : impression, play, like
        - Vérification que l'utilisateur_id est correctement associé.
        """
        self.client.force_authenticate(user=self.user)
        session_id_b = 'session_B_auth_456'

        payload = {
            'publication_id': str(self.pub_1.id),
            'session_id': session_id_b,
            'event_type': VideoEventLog.EVENT_LIKE,
            'watch_time_seconds': 12.0,
            'video_duration_seconds': 30.0,
            'progress_percent': 40.0,
            'feed_position': 0
        }

        response = self.client.post(self.url_single, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        log = VideoEventLog.objects.get(session_id=session_id_b)
        self.assertEqual(log.utilisateur, self.user)

        row = DatasetBuilder.build_dataset_row(log)
        self.assertIsNotNone(row)
        self.assertEqual(row['user_id'], self.user.id)
        self.assertEqual(row['target_relevance'], 3) # Like -> 3

    def test_validation_and_robustness(self):
        """
        Test de robustesse : rejet d'événements invalides.
        """
        # Invalid publication ID
        payload_invalid_pub = {
            'publication_id': '99999',
            'session_id': 'sess_err_1',
            'event_type': VideoEventLog.EVENT_PLAY
        }
        resp = self.client.post(self.url_single, payload_invalid_pub, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

        # Invalid event type
        payload_invalid_type = {
            'publication_id': str(self.pub_1.id),
            'session_id': 'sess_err_2',
            'event_type': 'NON_EXISTENT_TYPE'
        }
        resp = self.client.post(self.url_single, payload_invalid_type, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
