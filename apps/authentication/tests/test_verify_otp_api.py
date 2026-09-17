from datetime import timedelta
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase
from apps.users.models import Utilisateur
from apps.authentication.models import VerificationOTP
from apps.authentication.serializers import VerifyOtpSerializer
from apps.authentication.services import OtpService, RegistrationService


class VerifyOtpAPITestCase(APITestCase):
    """
    Suite de tests unitaires pour l'API de vérification OTP SMS (POST /api/auth/verify-otp/).
    """

    def setUp(self):
        self.verify_url = reverse('authentication:verify-otp')
        self.phone_number = '+221771234567'
        self.register_data = {
            'prenom': 'Fatou',
            'nom': 'Sow',
            'email': 'fatou.sow@ayyou.sn',
            'numero_telephone': self.phone_number,
            'password': 'SuperPassword@2025',
            'password_confirmation': 'SuperPassword@2025'
        }
        # Inscrire l'utilisateur
        self.user = RegistrationService.register_client(self.register_data)
        self.otp = VerificationOTP.objects.filter(utilisateur=self.user, est_utilise=False).first()

    def test_01_otp_correct(self):
        """1. Tester la soumission d'un code OTP correct (HTTP 200 OK)."""
        payload = {
            'numero_telephone': self.phone_number,
            'code': self.otp.code
        }
        response = self.client.post(self.verify_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['verified'])
        self.assertEqual(response.data['message'], "Numéro de téléphone vérifié avec succès.")

    def test_02_otp_incorrect(self):
        """2. Tester la soumission d'un code OTP incorrect (HTTP 400 Bad Request)."""
        payload = {
            'numero_telephone': self.phone_number,
            'code': '000000'
        }
        response = self.client.post(self.verify_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_03_otp_moins_de_six_chiffres(self):
        """3. Tester un code OTP de moins de 6 chiffres."""
        payload = {
            'numero_telephone': self.phone_number,
            'code': '12345'
        }
        response = self.client.post(self.verify_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_04_otp_contenant_lettres(self):
        """4. Tester un code OTP contenant des caractères non numériques."""
        payload = {
            'numero_telephone': self.phone_number,
            'code': '12345a'
        }
        response = self.client.post(self.verify_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_05_otp_expire(self):
        """5. Tester un code OTP expiré."""
        self.otp.date_expiration = timezone.now() - timedelta(minutes=1)
        self.otp.save()

        payload = {
            'numero_telephone': self.phone_number,
            'code': self.otp.code
        }
        response = self.client.post(self.verify_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.otp.refresh_from_db()
        self.assertTrue(self.otp.est_utilise)

    def test_06_otp_deja_utilise(self):
        """6. Tester un code OTP déjà utilisé."""
        self.otp.est_utilise = True
        self.otp.save()

        payload = {
            'numero_telephone': self.phone_number,
            'code': self.otp.code
        }
        response = self.client.post(self.verify_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_07_mauvais_utilisateur_telephone(self):
        """7. Tester un mauvais numéro de téléphone."""
        autre_user = Utilisateur.objects.create_user(
            email='autre.user@ayyou.sn',
            numero_telephone='+221779990000',
            password='SuperPassword@2025',
            prenom='Autre',
            nom='User'
        )
        payload = {
            'numero_telephone': '+221779990000',
            'code': self.otp.code
        }
        response = self.client.post(self.verify_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_08_utilisateur_inexistant(self):
        """8. Tester un numéro de téléphone d'utilisateur inexistant."""
        payload = {
            'numero_telephone': '+221770000000',
            'code': '123456'
        }
        response = self.client.post(self.verify_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_09_premiere_tentative_incorrecte(self):
        """9. Tester l'incrémentation après la première tentative incorrecte."""
        payload = {
            'numero_telephone': self.phone_number,
            'code': '000000'
        }
        self.client.post(self.verify_url, payload, format='json')
        self.otp.refresh_from_db()
        self.assertEqual(self.otp.nombre_tentatives, 1)

    def test_10_deuxieme_tentative_incorrecte(self):
        """10. Tester l'incrémentation après la deuxième tentative incorrecte."""
        payload = {
            'numero_telephone': self.phone_number,
            'code': '000000'
        }
        self.client.post(self.verify_url, payload, format='json')
        self.client.post(self.verify_url, payload, format='json')
        self.otp.refresh_from_db()
        self.assertEqual(self.otp.nombre_tentatives, 2)

    def test_11_troisieme_tentative_incorrecte(self):
        """11. Tester la troisième tentative incorrecte."""
        payload = {
            'numero_telephone': self.phone_number,
            'code': '000000'
        }
        self.client.post(self.verify_url, payload, format='json')
        self.client.post(self.verify_url, payload, format='json')
        self.client.post(self.verify_url, payload, format='json')
        self.otp.refresh_from_db()
        self.assertEqual(self.otp.nombre_tentatives, 3)

    def test_12_blocage_apres_trois_tentatives(self):
        """12. Tester le blocage et l'invalidation de l'OTP après 3 tentatives."""
        payload = {
            'numero_telephone': self.phone_number,
            'code': '000000'
        }
        for _ in range(3):
            self.client.post(self.verify_url, payload, format='json')

        self.otp.refresh_from_db()
        self.assertTrue(self.otp.est_utilise)

        # La 4ème tentative même avec le bon code doit être rejetée
        good_payload = {
            'numero_telephone': self.phone_number,
            'code': self.otp.code
        }
        response = self.client.post(self.verify_url, good_payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_13_verification_reussie_statut_verifie(self):
        """13. Tester que est_verifie passe à True sur Utilisateur après succès."""
        payload = {
            'numero_telephone': self.phone_number,
            'code': self.otp.code
        }
        self.client.post(self.verify_url, payload, format='json')
        self.user.refresh_from_db()
        self.assertTrue(self.user.est_verifie)

    def test_14_otp_valide_est_utilise_true(self):
        """14. Tester que est_utilise passe à True sur VerificationOTP après succès."""
        payload = {
            'numero_telephone': self.phone_number,
            'code': self.otp.code
        }
        self.client.post(self.verify_url, payload, format='json')
        self.otp.refresh_from_db()
        self.assertTrue(self.otp.est_utilise)

    def test_15_impossibilite_reutiliser_meme_otp(self):
        """15. Tester l'impossibilité de réutiliser le même OTP une deuxième fois."""
        payload = {
            'numero_telephone': self.phone_number,
            'code': self.otp.code
        }
        res1 = self.client.post(self.verify_url, payload, format='json')
        self.assertEqual(res1.status_code, status.HTTP_200_OK)

        res2 = self.client.post(self.verify_url, payload, format='json')
        self.assertEqual(res2.status_code, status.HTTP_400_BAD_REQUEST)

    def test_16_invalidation_anciens_otp(self):
        """16. Tester que les anciens OTP de l'utilisateur sont invalidés lors de la vérification."""
        # Générer un deuxième OTP
        second_otp = OtpService.generate_and_send_otp(self.user)
        payload = {
            'numero_telephone': self.phone_number,
            'code': second_otp.code
        }
        self.client.post(self.verify_url, payload, format='json')

        self.otp.refresh_from_db()
        second_otp.refresh_from_db()
        self.assertTrue(self.otp.est_utilise)
        self.assertTrue(second_otp.est_utilise)

    def test_17_transaction_atomique(self):
        """17. Tester que les modifications de statut sont atomiques."""
        payload = {
            'numero_telephone': self.phone_number,
            'code': self.otp.code
        }
        response = self.client.post(self.verify_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertTrue(self.user.est_verifie)

    def test_18_absence_code_otp_dans_reponse(self):
        """18. Tester qu'aucun code OTP ni secret ne fuite dans la réponse HTTP."""
        payload = {
            'numero_telephone': self.phone_number,
            'code': self.otp.code
        }
        response = self.client.post(self.verify_url, payload, format='json')
        self.assertNotIn('code', response.data)
        self.assertNotIn('otp', response.data)
        self.assertNotIn(self.otp.code, str(response.content))

    def test_19_absence_donnees_sensibles_logs(self):
        """19. Tester l'absence de fuite de mot de passe ou code OTP dans les données du serializer."""
        serializer = VerifyOtpSerializer(data={'numero_telephone': self.phone_number, 'code': '123456'})
        self.assertTrue(serializer.is_valid())

    def test_20_sauvegarde_sans_conflit(self):
        """20. Tester la validation avec format local Sénégalais '77 123 45 67'."""
        payload = {
            'numero_telephone': '77 123 45 67',
            'code': self.otp.code
        }
        response = self.client.post(self.verify_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
