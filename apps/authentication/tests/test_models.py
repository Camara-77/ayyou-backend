from django.test import TestCase
from django.utils import timezone
from datetime import timedelta
from apps.users.models import Utilisateur
from apps.authentication.models import VerificationOTP


class VerificationOTPModelTestCase(TestCase):
    """
    Tests unitaires pour le modèle VerificationOTP.
    """

    def setUp(self):
        self.user = Utilisateur.objects.create_user(
            email='otp.user@ayyou.com',
            numero_telephone='+221778889900',
            password='SuperPassword@2025',
            prenom='Moussa',
            nom='Diop'
        )

    def test_10_creation_verification_otp(self):
        """10. Tester la création d'une VerificationOTP."""
        expiration = timezone.now() + timedelta(minutes=10)
        otp = VerificationOTP.objects.create(
            utilisateur=self.user,
            code='849201',
            type_verification=VerificationOTP.VERIFICATION_TELEPHONE,
            date_expiration=expiration
        )
        self.assertIsNotNone(otp.id)
        self.assertEqual(otp.code, '849201')
        self.assertEqual(otp.utilisateur, self.user)
        self.assertFalse(otp.est_utilise)
        self.assertEqual(otp.nombre_tentatives, 0)

    def test_11_expiration_otp(self):
        """11. Tester l'expiration d'un code OTP."""
        # OTP déjà expiré (date d'expiration dans le passé)
        expiration_passee = timezone.now() - timedelta(minutes=1)
        otp_expire = VerificationOTP.objects.create(
            utilisateur=self.user,
            code='123456',
            type_verification=VerificationOTP.VERIFICATION_TELEPHONE,
            date_expiration=expiration_passee
        )
        self.assertTrue(otp_expire.est_expire())

        # OTP valide (date d'expiration dans le futur)
        expiration_future = timezone.now() + timedelta(minutes=10)
        otp_valide = VerificationOTP.objects.create(
            utilisateur=self.user,
            code='654321',
            type_verification=VerificationOTP.VERIFICATION_TELEPHONE,
            date_expiration=expiration_future
        )
        self.assertFalse(otp_valide.est_expire())

    def test_14_relation_utilisateur_verification_otp(self):
        """14. Tester la relation Utilisateur → VerificationOTP (1 ─── N)."""
        expiration = timezone.now() + timedelta(minutes=10)
        otp1 = VerificationOTP.objects.create(
            utilisateur=self.user,
            code='111111',
            type_verification=VerificationOTP.VERIFICATION_TELEPHONE,
            date_expiration=expiration
        )
        otp2 = VerificationOTP.objects.create(
            utilisateur=self.user,
            code='222222',
            type_verification=VerificationOTP.REINITIALISATION_MOT_DE_PASSE,
            date_expiration=expiration
        )

        user_otps = self.user.verifications_otp.all()
        self.assertEqual(user_otps.count(), 2)
        self.assertIn(otp1, user_otps)
        self.assertIn(otp2, user_otps)
