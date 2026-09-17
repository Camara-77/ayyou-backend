from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken
from apps.users.models import Utilisateur, ProfilClient, Role, UtilisateurRole


class ProfileAPITestCase(APITestCase):

    def setUp(self):
        # Créer le rôle CLIENT
        self.role_client, _ = Role.objects.get_or_create(
            nom=Role.CLIENT,
            defaults={'description': 'Client principal'}
        )

        # Créer l'utilisateur 1
        self.user1 = Utilisateur.objects.create_user(
            email="moussa.diop@ayyou.sn",
            numero_telephone="+221771234567",
            prenom="Moussa",
            nom="Diop",
            password="Password123!",
            est_verifie=True
        )
        UtilisateurRole.objects.create(utilisateur=self.user1, role=self.role_client)
        self.profil1, _ = ProfilClient.objects.get_or_create(utilisateur=self.user1)

        # Créer l'utilisateur 2
        self.user2 = Utilisateur.objects.create_user(
            email="aissatou.camara@ayyou.sn",
            numero_telephone="+221779876543",
            prenom="Aissatou",
            nom="Camara",
            password="Password123!",
            est_verifie=True
        )
        UtilisateurRole.objects.create(utilisateur=self.user2, role=self.role_client)
        self.profil2, _ = ProfilClient.objects.get_or_create(utilisateur=self.user2)

        # Tokens JWT pour utilisateur 1
        refresh1 = RefreshToken.for_user(self.user1)
        self.token1 = str(refresh1.access_token)

        # Tokens JWT pour utilisateur 2
        refresh2 = RefreshToken.for_user(self.user2)
        self.token2 = str(refresh2.access_token)

        self.profile_url = reverse('users:user-profile')
        self.location_url = reverse('users:user-location')

    def test_get_profile_unauthenticated_fails(self):
        response = self.client.get(self.profile_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_get_profile_authenticated_success(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token1}')
        response = self.client.get(self.profile_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['email'], "moussa.diop@ayyou.sn")
        self.assertEqual(response.data['prenom'], "Moussa")
        self.assertEqual(response.data['nom'], "Diop")
        self.assertEqual(response.data['nom_complet'], "Moussa Diop")
        self.assertEqual(response.data['numero_telephone'], "+221771234567")
        self.assertIn('profil_client', response.data)

    def test_profile_response_excludes_password(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token1}')
        response = self.client.get(self.profile_url)
        self.assertNotIn('password', response.data)
        self.assertNotIn('password_hash', response.data)

    def test_update_profile_prenom_nom_success(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token1}')
        payload = {
            "prenom": "Mamadou",
            "nom": "Sall",
            "profil_client": {
                "adresse_principale": "Point E, Rue 5, Dakar",
                "notifications_activees": False
            }
        }
        response = self.client.patch(self.profile_url, payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['prenom'], "Mamadou")
        self.assertEqual(response.data['nom'], "Sall")
        self.assertEqual(response.data['nom_complet'], "Mamadou Sall")
        self.assertEqual(response.data['profil_client']['adresse_principale'], "Point E, Rue 5, Dakar")
        self.assertFalse(response.data['profil_client']['notifications_activees'])

        # Vérification en base de données
        self.user1.refresh_from_db()
        self.assertEqual(self.user1.prenom, "Mamadou")
        self.assertEqual(self.user1.nom, "Sall")

    def test_update_profile_email_success(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token1}')
        payload = {"email": "moussa.nouveau@ayyou.sn"}
        response = self.client.patch(self.profile_url, payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['email'], "moussa.nouveau@ayyou.sn")

    def test_update_profile_duplicate_email_fails(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token1}')
        # Tenter d'utiliser l'email de user2
        payload = {"email": "aissatou.camara@ayyou.sn"}
        response = self.client.patch(self.profile_url, payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('email', response.data['errors'])

    def test_update_profile_cannot_modify_sensitive_fields(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token1}')
        payload = {
            "is_staff": True,
            "is_superuser": True,
            "est_verifie": False
        }
        response = self.client.patch(self.profile_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Vérifier que les privilèges n'ont pas été élevés
        self.user1.refresh_from_db()
        self.assertFalse(self.user1.is_staff)
        self.assertFalse(self.user1.is_superuser)

    def test_update_location_coordinates_success(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token1}')
        payload = {
            "latitude": 14.7114000,
            "longitude": -17.4672000,
            "adresse_principale": "Almadies, Route des Plages, Dakar"
        }
        response = self.client.post(self.location_url, payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("message", response.data)
        self.assertEqual(response.data['user']['profil_client']['adresse_principale'], "Almadies, Route des Plages, Dakar")

    def test_update_location_invalid_coordinates_fails(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token1}')
        payload = {
            "latitude": 120.0000000,  # Latitude invalide (> 90)
            "longitude": -17.4672000
        }
        response = self.client.post(self.location_url, payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('latitude', response.data['errors'])

    def test_user_cannot_access_or_modify_other_user_profile(self):
        # Utilisateur 2 tente d'accéder à son profil
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token2}')
        response = self.client.get(self.profile_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # La réponse DOIT être le profil de user2 et non user1
        self.assertEqual(response.data['email'], "aissatou.camara@ayyou.sn")
        self.assertNotEqual(response.data['email'], "moussa.diop@ayyou.sn")
