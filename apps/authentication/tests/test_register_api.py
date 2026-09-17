from unittest.mock import patch
from datetime import timedelta
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase
from apps.users.models import Utilisateur, ProfilClient, Role, UtilisateurRole
from apps.authentication.models import VerificationOTP


class RegisterAPITestCase(APITestCase):
    """
    Suite de tests unitaires pour l'API d'inscription Client AYYOU (POST /api/auth/register/).
    """

    def setUp(self):
        self.register_url = reverse('authentication:register')
        self.valid_payload = {
            'prenom': 'Moussa',
            'nom': 'Diop',
            'email': 'moussa.diop@ayyou.sn',
            'numero_telephone': '+221771234567',
            'password': 'SuperPassword@2025',
            'password_confirmation': 'SuperPassword@2025'
        }

    def test_01_inscription_valide(self):
        """1. Tester une inscription valide (HTTP 201 Created)."""
        response = self.client.post(self.register_url, self.valid_payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data['verification_required'])
        self.assertEqual(response.data['verification_type'], 'VERIFICATION_TELEPHONE')

    def test_02_email_invalide(self):
        """2. Tester un format d'email invalide (HTTP 400 Bad Request)."""
        payload = self.valid_payload.copy()
        payload['email'] = 'email_invalide_sans_arobase'
        response = self.client.post(self.register_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('email', response.data['errors'])

    def test_03_email_deja_utilise(self):
        """3. Tester la tentative d'inscription avec un email déjà existant (HTTP 409 Conflict)."""
        self.client.post(self.register_url, self.valid_payload, format='json')
        payload = self.valid_payload.copy()
        payload['numero_telephone'] = '+221779998877'  # Téléphone différent
        response = self.client.post(self.register_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertIn('email', response.data['errors'])

    def test_04_telephone_invalide(self):
        """4. Tester un format de numéro de téléphone invalide (HTTP 400 Bad Request)."""
        payload = self.valid_payload.copy()
        payload['numero_telephone'] = '123'
        response = self.client.post(self.register_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('numero_telephone', response.data['errors'])

    def test_05_telephone_deja_utilise(self):
        """5. Tester un numéro de téléphone déjà utilisé (HTTP 409 Conflict)."""
        self.client.post(self.register_url, self.valid_payload, format='json')
        payload = self.valid_payload.copy()
        payload['email'] = 'autre.email@ayyou.sn'  # Email différent
        response = self.client.post(self.register_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertIn('numero_telephone', response.data['errors'])

    def test_06_telephone_normalise_e164(self):
        """6. Tester la normalisation du téléphone au format international E.164."""
        payload = self.valid_payload.copy()
        payload['numero_telephone'] = '77 123 45 67'  # Format local sans indicatif (utilisera SN par défaut)
        response = self.client.post(self.register_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        user = Utilisateur.objects.get(email='moussa.diop@ayyou.sn')
        self.assertEqual(user.numero_telephone, '+221771234567')

    def test_07_mot_de_passe_trop_court(self):
        """7. Tester un mot de passe trop court (< 8 car.)."""
        payload = self.valid_payload.copy()
        payload['password'] = 'Pass@1'
        payload['password_confirmation'] = 'Pass@1'
        response = self.client.post(self.register_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('password', response.data['errors'])

    def test_08_mot_de_passe_sans_chiffre(self):
        """8. Tester un mot de passe sans chiffre."""
        payload = self.valid_payload.copy()
        payload['password'] = 'SuperPassword@'
        payload['password_confirmation'] = 'SuperPassword@'
        response = self.client.post(self.register_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('password', response.data['errors'])

    def test_09_mot_de_passe_sans_symbole(self):
        """9. Tester un mot de passe sans symbole/caractère spécial."""
        payload = self.valid_payload.copy()
        payload['password'] = 'SuperPassword2025'
        payload['password_confirmation'] = 'SuperPassword2025'
        response = self.client.post(self.register_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('password', response.data['errors'])

    def test_10_confirmation_differente(self):
        """10. Tester des mots de passe qui ne correspondent pas."""
        payload = self.valid_payload.copy()
        payload['password_confirmation'] = 'AutrePassword@2025'
        response = self.client.post(self.register_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('password_confirmation', response.data['errors'])

    def test_11_creation_profil_client(self):
        """11. Tester la création automatique du ProfilClient lors de l'inscription."""
        self.client.post(self.register_url, self.valid_payload, format='json')
        user = Utilisateur.objects.get(email='moussa.diop@ayyou.sn')
        self.assertTrue(ProfilClient.objects.filter(utilisateur=user).exists())

    def test_12_attribution_role_client(self):
        """12. Tester l'attribution automatique du rôle CLIENT."""
        self.client.post(self.register_url, self.valid_payload, format='json')
        user = Utilisateur.objects.get(email='moussa.diop@ayyou.sn')
        roles = [ur.role.nom for ur in user.roles_attribues.all()]
        self.assertIn(Role.CLIENT, roles)

    def test_13_generation_otp(self):
        """13. Tester la génération de l'OTP SMS de vérification."""
        self.client.post(self.register_url, self.valid_payload, format='json')
        user = Utilisateur.objects.get(email='moussa.diop@ayyou.sn')
        otp = VerificationOTP.objects.filter(utilisateur=user).first()
        self.assertIsNotNone(otp)
        self.assertEqual(otp.type_verification, VerificationOTP.VERIFICATION_TELEPHONE)

    def test_14_otp_six_chiffres(self):
        """14. Tester que le code OTP est une chaîne exacte de 6 chiffres."""
        self.client.post(self.register_url, self.valid_payload, format='json')
        user = Utilisateur.objects.get(email='moussa.diop@ayyou.sn')
        otp = VerificationOTP.objects.filter(utilisateur=user).first()
        self.assertEqual(len(otp.code), 6)
        self.assertTrue(otp.code.isdigit())

    def test_15_expiration_otp(self):
        """15. Tester la date d'expiration de l'OTP."""
        self.client.post(self.register_url, self.valid_payload, format='json')
        user = Utilisateur.objects.get(email='moussa.diop@ayyou.sn')
        otp = VerificationOTP.objects.filter(utilisateur=user).first()
        self.assertGreater(otp.date_expiration, timezone.now())

    def test_16_ancien_otp_invalide(self):
        """16. Tester l'invalidation du précédent OTP lors d'une nouvelle demande."""
        self.client.post(self.register_url, self.valid_payload, format='json')
        user = Utilisateur.objects.get(email='moussa.diop@ayyou.sn')
        first_otp = VerificationOTP.objects.filter(utilisateur=user).first()

        # Déclencher un deuxième OTP
        from apps.authentication.services import OtpService
        second_otp = OtpService.generate_and_send_otp(user)

        first_otp.refresh_from_db()
        self.assertTrue(first_otp.est_utilise)
        self.assertFalse(second_otp.est_utilise)

    @patch('apps.authentication.services.otp_service.OtpService.generate_and_send_otp')
    def test_17_transaction_atomique_rollback(self, mock_otp):
        """17. Tester le rollback de la transaction atomique si une étape échoue."""
        mock_otp.side_effect = Exception("Erreur simulée du service OTP")
        with self.assertRaises(Exception):
            self.client.post(self.register_url, self.valid_payload, format='json')

        self.assertFalse(Utilisateur.objects.filter(email='moussa.diop@ayyou.sn').exists())
        self.assertFalse(ProfilClient.objects.exists())

    def test_18_aucun_mot_de_passe_en_clair(self):
        """18. Tester qu'aucun mot de passe n'est stocké en clair."""
        self.client.post(self.register_url, self.valid_payload, format='json')
        user = Utilisateur.objects.get(email='moussa.diop@ayyou.sn')
        self.assertNotEqual(user.password, 'SuperPassword@2025')
        self.assertTrue(user.check_password('SuperPassword@2025'))

    def test_19_aucun_otp_dans_reponse_api(self):
        """19. Tester qu'aucun code OTP ni mot de passe ne fuite dans la réponse HTTP API."""
        response = self.client.post(self.register_url, self.valid_payload, format='json')
        response_str = str(response.content)
        self.assertNotIn('code', response.data)
        self.assertNotIn('password', response_str)
        self.assertNotIn('SuperPassword@2025', response_str)

    def test_20_utilisateur_non_verifie_apres_inscription(self):
        """20. Tester que l'utilisateur a le statut non vérifié (est_verifie=False) après l'inscription."""
        self.client.post(self.register_url, self.valid_payload, format='json')
        user = Utilisateur.objects.get(email='moussa.diop@ayyou.sn')
        self.assertFalse(user.est_verifie)
        self.assertTrue(user.est_actif)
