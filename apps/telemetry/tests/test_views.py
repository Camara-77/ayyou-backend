from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from apps.users.models import Utilisateur
from apps.catalog.models import Etablissement, PublicationFeed
from apps.telemetry.models import VideoEventLog


class TelemetryViewsTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        
        # User setup
        self.user = Utilisateur.objects.create_user(
            email='telemetry_user@ayyou.com',
            numero_telephone='+221770000000',
            password='Password123!',
            prenom='Telemetry',
            nom='Tester'
        )

        # Etablissement setup
        self.etablissement = Etablissement.objects.create(
            nom='Test Resto Telemetry',
            statut_abonnement='ACTIF'
        )

        # Publication setup
        self.publication = PublicationFeed.objects.create(
            etablissement=self.etablissement,
            media_url='https://res.cloudinary.com/ayyou/video/upload/v1/test.mp4',
            type_media='video'
        )

        self.url_single = reverse('telemetry:video-event-create')
        self.url_batch = reverse('telemetry:video-event-batch-create')

    def test_create_single_event_anonymous(self):
        payload = {
            'publication_id': str(self.publication.id),
            'session_id': 'session_anon_123',
            'event_type': VideoEventLog.EVENT_IMPRESSION,
            'watch_time_seconds': 5.2,
            'video_duration_seconds': 30.0,
            'progress_percent': 17.3,
            'feed_position': 0,
            'metadata': {'device': 'PWA'}
        }
        response = self.client.post(self.url_single, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        log = VideoEventLog.objects.get(session_id='session_anon_123')
        self.assertIsNone(log.utilisateur)
        self.assertEqual(log.event_type, VideoEventLog.EVENT_IMPRESSION)
        self.assertEqual(log.watch_time_seconds, 5.2)

    def test_create_single_event_authenticated(self):
        self.client.force_authenticate(user=self.user)
        payload = {
            'publication_id': str(self.publication.id),
            'session_id': 'session_user_456',
            'event_type': VideoEventLog.EVENT_COMPLETED,
            'watch_time_seconds': 30.0,
            'video_duration_seconds': 30.0,
            'progress_percent': 100.0,
            'feed_position': 1
        }
        response = self.client.post(self.url_single, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        log = VideoEventLog.objects.get(session_id='session_user_456')
        self.assertEqual(log.utilisateur, self.user)
        self.assertEqual(log.event_type, VideoEventLog.EVENT_COMPLETED)

    def test_create_batch_events(self):
        payload = {
            'events': [
                {
                    'publication_id': str(self.publication.id),
                    'session_id': 'session_batch_789',
                    'event_type': VideoEventLog.EVENT_PLAY,
                    'watch_time_seconds': 0.0,
                    'video_duration_seconds': 15.0,
                    'progress_percent': 0.0,
                    'feed_position': 2
                },
                {
                    'publication_id': str(self.publication.id),
                    'session_id': 'session_batch_789',
                    'event_type': VideoEventLog.EVENT_LIKE,
                    'watch_time_seconds': 10.0,
                    'video_duration_seconds': 15.0,
                    'progress_percent': 66.6,
                    'feed_position': 2
                }
            ]
        }
        response = self.client.post(self.url_batch, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(VideoEventLog.objects.filter(session_id='session_batch_789').count(), 2)
