from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from apps.users.models import Utilisateur, Role


class GoogleAuthAPITest(APITestCase):
    def setUp(self):
        self.url = reverse('authentication:google')

    def test_google_auth_missing_token(self):
        response = self.client.post(self.url, {})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('token', response.data['errors'])

    def test_google_auth_new_user_creation(self):
        payload = {'token': 'test.google.user@example.com'}
        response = self.client.post(self.url, payload)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)
        self.assertEqual(response.data['utilisateur']['email'], 'test.google.user@example.com')
        self.assertTrue(response.data['utilisateur']['est_verifie'])

        user = Utilisateur.objects.filter(email='test.google.user@example.com').first()
        self.assertIsNotNone(user)
        self.assertTrue(user.est_verifie)

    def test_google_auth_existing_user(self):
        user = Utilisateur.objects.create_user(
            email='existing.google@example.com',
            prenom='Jean',
            nom='Dupont',
            numero_telephone='+221770001122',
            password='Password123!',
            est_verifie=False
        )
        payload = {'token': 'existing.google@example.com'}
        response = self.client.post(self.url, payload)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)

        user.refresh_from_db()
        self.assertTrue(user.est_verifie)
