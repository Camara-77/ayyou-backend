from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from apps.users.models import Utilisateur, Role, UtilisateurRole, ProfilLivreur

class ProfilLivreurEditTests(TestCase):
    def setUp(self):
        self.role_livreur, _ = Role.objects.get_or_create(nom=Role.LIVREUR)
        self.role_client, _ = Role.objects.get_or_create(nom=Role.CLIENT)
        self.role_vendeur, _ = Role.objects.get_or_create(nom=Role.VENDEUR)

        # Livreur A (Validé)
        self.user_a = Utilisateur.objects.create_user(
            email='livreur.a@ayyou.sn',
            numero_telephone='+221776543210',
            prenom='Abdoulaye',
            nom='Diop',
            password='Passer123!'
        )
        UtilisateurRole.objects.create(utilisateur=self.user_a, role=self.role_livreur)
        self.profil_a = ProfilLivreur.objects.create(
            utilisateur=self.user_a,
            statut_verification=ProfilLivreur.STATUT_VALIDE,
            marque='Honda',
            modele='CG 125',
            immatriculation='DK-4892-AZ',
            secteur_intervention='Plateau, Point E, Fann'
        )

        # Livreur B (Validé)
        self.user_b = Utilisateur.objects.create_user(
            email='livreur.b@ayyou.sn',
            numero_telephone='+221789990000',
            prenom='Moussa',
            nom='Sene',
            password='Passer123!'
        )
        UtilisateurRole.objects.create(utilisateur=self.user_b, role=self.role_livreur)
        self.profil_b = ProfilLivreur.objects.create(
            utilisateur=self.user_b,
            statut_verification=ProfilLivreur.STATUT_VALIDE
        )

        # Client non-Livreur
        self.user_client = Utilisateur.objects.create_user(
            email='client@ayyou.sn',
            numero_telephone='+221701112233',
            prenom='Fatou',
            nom='Ndiaye',
            password='Passer123!'
        )
        UtilisateurRole.objects.create(utilisateur=self.user_client, role=self.role_client)

        self.client_a = APIClient()
        self.client_a.force_authenticate(user=self.user_a)

        self.client_client = APIClient()
        self.client_client.force_authenticate(user=self.user_client)

    def test_get_profile_returns_matricule_and_user_info(self):
        res = self.client_a.get('/api/deliveries/profile/')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        data = res.json()
        self.assertEqual(data['prenom'], 'Abdoulaye')
        self.assertEqual(data['nom'], 'Diop')
        self.assertEqual(data['email'], 'livreur.a@ayyou.sn')
        self.assertIn('matricule', data)
        self.assertTrue(data['matricule'].startswith('#AY-'))

    def test_patch_profile_updates_identity_vehicle_and_zones(self):
        payload = {
            'prenom': 'Abdoulaye Modifié',
            'nom': 'Diop Modifié',
            'marque': 'Yamaha',
            'modele': 'Crypton',
            'immatriculation': 'DK-9999-ZZ',
            'secteur_intervention': 'Plateau, Point E, Médina, Corniche Ouest',
            'comptes_reversement': [
                {'provider': 'WAVE', 'provider_name': 'Wave Sénégal', 'numero': '+221776543210', 'is_principal': True},
                {'provider': 'ORANGE_MONEY', 'provider_name': 'Orange Money', 'numero': '+221789990012', 'is_principal': False}
            ]
        }
        res = self.client_a.patch('/api/deliveries/profile/', payload, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        data = res.json()

        # Vérification données retournées
        self.assertEqual(data['prenom'], 'Abdoulaye Modifié')
        self.assertEqual(data['nom'], 'Diop Modifié')
        self.assertEqual(data['marque'], 'Yamaha')
        self.assertEqual(data['modele'], 'Crypton')
        self.assertEqual(data['immatriculation'], 'DK-9999-ZZ')
        self.assertIn('Corniche Ouest', data['secteur_intervention'])

        # Verification persistance BDD
        self.user_a.refresh_from_db()
        self.profil_a.refresh_from_db()
        self.assertEqual(self.user_a.prenom, 'Abdoulaye Modifié')
        self.assertEqual(self.user_a.nom, 'Diop Modifié')
        self.assertEqual(self.profil_a.marque, 'Yamaha')
        self.assertEqual(len(self.profil_a.comptes_reversement), 2)
        self.assertTrue(self.profil_a.comptes_reversement[0]['is_principal'])

    def test_non_livreur_cannot_access_or_patch_delivery_profile(self):
        res_get = self.client_client.get('/api/deliveries/profile/')
        self.assertIn(res_get.status_code, [status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND])

        res_patch = self.client_client.patch('/api/deliveries/profile/', {'prenom': 'Hack'}, format='json')
        self.assertIn(res_patch.status_code, [status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND])

    def test_patch_duplicate_email_fails(self):
        payload = {'email': 'livreur.b@ayyou.sn'} # Email déjà utilisé par Livreur B
        res = self.client_a.patch('/api/deliveries/profile/', payload, format='json')
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_photo_upload_endpoint(self):
        payload = {'photo_url': 'https://res.cloudinary.com/ayyou/image/upload/v12345/driver_a.jpg'}
        res = self.client_a.post('/api/deliveries/profile/photo/', payload, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.profil_a.refresh_from_db()
        self.assertEqual(self.profil_a.photo_avatar, 'https://res.cloudinary.com/ayyou/image/upload/v12345/driver_a.jpg')
