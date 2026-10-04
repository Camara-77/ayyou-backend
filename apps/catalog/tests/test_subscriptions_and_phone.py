from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status

from datetime import timedelta
from django.utils import timezone
from apps.users.models import Utilisateur
from apps.catalog.models import Etablissement, AbonnementEtablissement, Categorie, Produit, PublicationFeed


class SubscriptionsAndPhoneTests(TestCase):
    def setUp(self):
        self.client = APIClient()

        # User 1
        self.user = Utilisateur.objects.create_user(
            email='client.test@ayyou.com',
            numero_telephone='+221770001122',
            prenom='Modou',
            nom='Fall',
            password='Password123!'
        )

        # User 2
        self.other_user = Utilisateur.objects.create_user(
            email='autre.client@ayyou.com',
            numero_telephone='+221770003344',
            prenom='Awa',
            nom='Diop',
            password='Password123!'
        )

        # Establishment 1 (Restaurant)
        self.restaurant = Etablissement.objects.create(
            nom='Chez Lamine Teranga',
            type_etablissement=Etablissement.TYPE_RESTAURANT,
            statut_verification=Etablissement.STATUT_VALIDE,
            statut_abonnement=Etablissement.STATUT_ABONNEMENT_ACTIF,
            date_expiration_abonnement=timezone.now() + timedelta(days=30),
            adresse='Almadies, Dakar',
            proprietaire=self.other_user
        )

        # Establishment 2 (Vendeur)
        self.vendeur = Etablissement.objects.create(
            nom='Les Délices d\'Awa',
            type_etablissement=Etablissement.TYPE_VENDEUR,
            statut_verification=Etablissement.STATUT_VALIDE,
            statut_abonnement=Etablissement.STATUT_ABONNEMENT_ACTIF,
            date_expiration_abonnement=timezone.now() + timedelta(days=30),
            adresse='Sacré-Cœur 3, Dakar',
            proprietaire=self.other_user
        )

    def test_subscribe_to_etablissement(self):
        self.client.force_authenticate(user=self.user)
        url = reverse('catalog:subscription-list-create-delete')
        response = self.client.post(url, {'etablissement_id': self.restaurant.id}, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(AbonnementEtablissement.objects.filter(utilisateur=self.user, etablissement=self.restaurant).exists())

    def test_duplicate_subscription_prevented(self):
        self.client.force_authenticate(user=self.user)
        url = reverse('catalog:subscription-list-create-delete')
        
        res1 = self.client.post(url, {'etablissement_id': self.restaurant.id}, format='json')
        self.assertEqual(res1.status_code, status.HTTP_201_CREATED)

        res2 = self.client.post(url, {'etablissement_id': self.restaurant.id}, format='json')
        self.assertEqual(res2.status_code, status.HTTP_200_OK)
        self.assertEqual(AbonnementEtablissement.objects.filter(utilisateur=self.user, etablissement=self.restaurant).count(), 1)

    def test_unsubscribe_from_etablissement(self):
        self.client.force_authenticate(user=self.user)
        AbonnementEtablissement.objects.create(utilisateur=self.user, etablissement=self.restaurant)

        url = reverse('catalog:subscription-detail', kwargs={'pk': self.restaurant.id})
        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(AbonnementEtablissement.objects.filter(utilisateur=self.user, etablissement=self.restaurant).exists())

    def test_get_my_subscriptions(self):
        self.client.force_authenticate(user=self.user)
        AbonnementEtablissement.objects.create(utilisateur=self.user, etablissement=self.restaurant)
        AbonnementEtablissement.objects.create(utilisateur=self.user, etablissement=self.vendeur)

        url = reverse('catalog:subscription-list-create-delete')
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        names = [item['etablissement_detail']['nom'] for item in response.data]
        self.assertIn('Chez Lamine Teranga', names)
        self.assertIn('Les Délices d\'Awa', names)

    def test_followers_count_and_status(self):
        self.client.force_authenticate(user=self.user)
        AbonnementEtablissement.objects.create(utilisateur=self.user, etablissement=self.restaurant)
        AbonnementEtablissement.objects.create(utilisateur=self.other_user, etablissement=self.restaurant)

        url = reverse('catalog:etablissement-detail', kwargs={'pk': self.restaurant.id})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['followers_count'], 2)
        self.assertTrue(response.data['is_subscribed'])

    def test_unauthenticated_subscription_fails(self):
        url = reverse('catalog:subscription-list-create-delete')
        response = self.client.post(url, {'etablissement_id': self.restaurant.id}, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_update_phone_success(self):
        self.client.force_authenticate(user=self.user)
        url = reverse('users:user-phone-update')
        response = self.client.patch(url, {'numero_telephone': '+221789998877'}, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertEqual(self.user.numero_telephone, '+221789998877')

    def test_update_phone_duplicate_fails(self):
        self.client.force_authenticate(user=self.user)
        url = reverse('users:user-phone-update')
        response = self.client.patch(url, {'numero_telephone': self.other_user.numero_telephone}, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('errors', response.data)

    def test_video_publication_with_valid_reference_dish(self):
        self.client.force_authenticate(user=self.other_user)
        cat = Categorie.objects.create(nom='Plats Nationaux', slug='plats-nationaux')
        etab = Etablissement.objects.filter(proprietaire=self.other_user).first()
        p1 = Produit.objects.create(nom='Thiéboudienne', prix_base=3500, etablissement=etab, categorie=cat)

        url = reverse('catalog:publication-feed-list')
        data = {
            'media_url': 'https://res.cloudinary.com/demo/video/upload/v1234/test.mp4',
            'produit_id': p1.id,
            'title': 'Thiéboudienne Penda Mbaye'
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        pub = PublicationFeed.objects.get(pk=response.data['id'])
        self.assertEqual(pub.produit, p1)

    def test_video_publication_with_invalid_dish_ownership(self):
        self.client.force_authenticate(user=self.other_user)
        cat = Categorie.objects.create(nom='Plats Nationaux', slug='plats-nationaux-2')
        other_etab = Etablissement.objects.create(
            nom='Autre Resto',
            type_etablissement=Etablissement.TYPE_RESTAURANT,
            proprietaire=self.user
        )
        p_other = Produit.objects.create(nom='Burger Foreign', prix_base=5000, etablissement=other_etab, categorie=cat)

        url = reverse('catalog:publication-feed-list')
        data = {
            'media_url': 'https://res.cloudinary.com/demo/video/upload/v1234/test.mp4',
            'produit_id': p_other.id,
            'title': 'Hack attempt'
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Le plat de référence sélectionné n'appartient pas à votre établissement", str(response.data))

    def test_video_publication_general_without_dish(self):
        self.client.force_authenticate(user=self.other_user)
        url = reverse('catalog:publication-feed-list')
        data = {
            'media_url': 'https://res.cloudinary.com/demo/video/upload/v1234/test.mp4',
            'title': 'Vidéo Présentation'
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        pub = PublicationFeed.objects.get(pk=response.data['id'])
        self.assertIsNone(pub.produit)

