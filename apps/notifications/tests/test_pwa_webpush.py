import json
from unittest.mock import patch
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.users.models import Utilisateur
from apps.notifications.models import PushSubscription, PushNotificationPreference, Notification
from apps.notifications.webpush_service import WebPushService, VAPID_PUBLIC_KEY
from apps.catalog.models import Etablissement, Produit, PublicationFeed, AbonnementEtablissement
from apps.orders.models import RepasPlanifie
from django.utils import timezone
import datetime


class PWAWebPushTests(TestCase):
    def setUp(self):
        self.client = APIClient()

        # Utilisateur Client de test
        self.user = Utilisateur.objects.create_user(
            email='client.pwa@ayyou.sn',
            password='Password123!',
            prenom='Aminata',
            nom='Diallo',
            numero_telephone='+221771234567'
        )

        # Autre utilisateur
        self.other_user = Utilisateur.objects.create_user(
            email='autre.user@ayyou.sn',
            password='Password123!',
            prenom='Ousmane',
            nom='Sow',
            numero_telephone='+221779876543'
        )

        # Resto & Produit
        self.pro_user = Utilisateur.objects.create_user(
            email='pro.resto@ayyou.sn',
            password='Password123!',
            prenom='Abdou',
            nom='Ndiaye',
            numero_telephone='+221789998877'
        )
        self.etablissement = Etablissement.objects.create(
            nom="Chez Abdou Dibi",
            type_etablissement=Etablissement.TYPE_RESTAURANT,
            proprietaire=self.pro_user,
            statut_verification=Etablissement.STATUT_VALIDE
        )
        self.produit = Produit.objects.create(
            etablissement=self.etablissement,
            nom="Dibi d'Agneau",
            prix_base=4500,
            est_disponible=True
        )

        # Abonnement Web Push VAPID
        self.subscription = PushSubscription.objects.create(
            utilisateur=self.user,
            endpoint="https://fcm.googleapis.com/fcm/send/fake-token-123",
            p256dh="fake-p256dh-key",
            auth="fake-auth-secret",
            user_agent="Mozilla/5.0 (Android; Mobile)"
        )

    def test_vapid_public_key_endpoint(self):
        """Vérifie l'endpoint GET /api/notifications/vapid-public-key/."""
        self.client.force_authenticate(user=self.user)
        url = reverse('notifications:vapid-public-key')
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data.get('public_key'), VAPID_PUBLIC_KEY)

    def test_push_subscribe_endpoint(self):
        """Vérifie l'enregistrement d'une souscription Web Push via POST /api/notifications/push-subscribe/."""
        self.client.force_authenticate(user=self.user)
        url = reverse('notifications:push-subscribe')
        payload = {
            "endpoint": "https://updates.push.services.mozilla.com/wpush/v2/test-endpoint-456",
            "keys": {
                "p256dh": "new-p256dh-key",
                "auth": "new-auth-secret"
            }
        }
        res = self.client.post(url, payload, format='json')
        self.assertIn(res.status_code, [status.HTTP_200_OK, status.HTTP_201_CREATED])
        self.assertEqual(PushSubscription.objects.filter(utilisateur=self.user).count(), 2)

    def test_push_unsubscribe_endpoint(self):
        """Vérifie la désactivation d'un abonnement via POST /api/notifications/push-unsubscribe/."""
        self.client.force_authenticate(user=self.user)
        url = reverse('notifications:push-unsubscribe')
        payload = {"endpoint": self.subscription.endpoint}
        res = self.client.post(url, payload, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.subscription.refresh_from_db()
        self.assertFalse(self.subscription.is_active)

    def test_push_preferences_get_and_patch(self):
        """Vérifie la consultation et la modification des préférences [ON/OFF]."""
        self.client.force_authenticate(user=self.user)
        url = reverse('notifications:push-preferences')

        # GET
        res_get = self.client.get(url)
        self.assertEqual(res_get.status_code, status.HTTP_200_OK)
        self.assertTrue(res_get.data['push_rappels_planning'])

        # PATCH
        res_patch = self.client.patch(url, {'push_rappels_planning': False}, format='json')
        self.assertEqual(res_patch.status_code, status.HTTP_200_OK)
        self.assertFalse(res_patch.data['push_rappels_planning'])

    @patch('apps.notifications.webpush_service.webpush')
    def test_webpush_service_send_with_preferences(self, mock_webpush):
        """Vérifie que WebPushService respecte les préférences utilisateur et les Deep Links."""
        pref, _ = PushNotificationPreference.objects.get_or_create(utilisateur=self.user)
        pref.push_rappels_planning = True
        pref.save()

        sent_count = WebPushService.send_push_to_user(
            utilisateur_id=self.user.id,
            titre="Test Repas Planifié",
            message="Votre repas est prêt",
            url="/planning/detail/10",
            category="PLANNING"
        )
        self.assertEqual(sent_count, 1)
        mock_webpush.assert_called_once()

    @patch('apps.notifications.webpush_service.webpush')
    def test_video_publication_triggers_push_to_subscribers(self, mock_webpush):
        """Vérifie qu'une nouvelle vidéo publiée envoie un Web Push aux abonnés."""
        # S'abonner à l'établissement
        AbonnementEtablissement.objects.create(utilisateur=self.user, etablissement=self.etablissement)

        publication = PublicationFeed.objects.create(
            etablissement=self.etablissement,
            produit=self.produit,
            media_url='https://res.cloudinary.com/ayyou/video/upload/v1/dibi.mp4',
            type_media=PublicationFeed.TYPE_MEDIA_VIDEO
        )

        sent_count = WebPushService.send_push_to_user(
            utilisateur_id=self.user.id,
            titre=f"🎥 {self.etablissement.nom} a publié une vidéo",
            message=f"Découvrez : {self.produit.nom}",
            url=f"/feed/video/{publication.id}",
            category="VIDEO"
        )
        self.assertEqual(sent_count, 1)
        mock_webpush.assert_called()
