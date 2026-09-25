import jwt
from django.urls import reverse
from django.utils import timezone
from rest_framework import status, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import AccessToken
from apps.users.models import Utilisateur
from apps.authentication.models import VerificationOTP
from apps.authentication.services import RegistrationService, OtpService


class ProtectedTestView(APIView):
    """Vue de test protégée exigeant une authentification JWT."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return Response({"message": "Accès autorisé", "user_id": request.user.id})


class LoginAPITestCase(APITestCase):
    """
    Suite de tests unitaires et d'intégration pour l'API de connexion Client (POST /api/auth/login/).
    Vérifie l'authentification par email/téléphone, les tokens JWT, la sécurité et la mise à jour de la dernière connexion.
    """

    def setUp(self):
        self.login_url = reverse('authentication:login')
        self.phone_number = '+221771234567'
        self.email = 'fatou.sow@ayyou.sn'
        self.password = 'SuperPassword@2025'

        self.register_data = {
            'prenom': 'Fatou',
            'nom': 'Sow',
            'email': self.email,
            'numero_telephone': self.phone_number,
            'password': self.password,
            'password_confirmation': self.password
        }

        # 1. Inscrire l'utilisateur
        self.user = RegistrationService.register_client(self.register_data)

        # 2. Récupérer et valider l'OTP pour passer l'utilisateur en est_verifie=True
        otp = VerificationOTP.objects.filter(utilisateur=self.user, est_utilise=False).first()
        OtpService.verify_otp_code(self.phone_number, otp.code)
        self.user.refresh_from_db()

    def test_01_login_email_valide(self):
        """1. Connexion réussie avec adresse email valide (HTTP 200 OK)."""
        payload = {
            'identifier': self.email,
            'password': self.password
        }
        response = self.client.post(self.login_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)

    def test_02_login_telephone_valide(self):
        """2. Connexion réussie avec numéro de téléphone au format E.164 (HTTP 200 OK)."""
        payload = {
            'identifier': self.phone_number,
            'password': self.password
        }
        response = self.client.post(self.login_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)

    def test_03_login_email_majuscules(self):
        """3. Connexion réussie avec email contenant des majuscules."""
        payload = {
            'identifier': 'FATOU.SOW@AYYOU.SN',
            'password': self.password
        }
        response = self.client.post(self.login_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_04_login_telephone_format_local(self):
        """4. Connexion réussie avec téléphone au format local sénégalais ('77 123 45 67')."""
        payload = {
            'identifier': '77 123 45 67',
            'password': self.password
        }
        response = self.client.post(self.login_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_05_login_telephone_format_e164(self):
        """5. Connexion réussie avec téléphone au format international E.164."""
        payload = {
            'identifier': '+221771234567',
            'password': self.password
        }
        response = self.client.post(self.login_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_06_mot_de_passe_correct(self):
        """6. Validation d'un mot de passe correct."""
        payload = {
            'identifier': self.email,
            'password': self.password
        }
        response = self.client.post(self.login_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_07_mot_de_passe_incorrect(self):
        """7. Mot de passe incorrect (HTTP 400 Bad Request / Identifiants invalides)."""
        payload = {
            'identifier': self.email,
            'password': 'MauvaisPassword123!'
        }
        response = self.client.post(self.login_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('errors', response.data)

    def test_08_identifiant_inexistant(self):
        """8. Identifiant inexistant (email ou téléphone non enregistré)."""
        payload = {
            'identifier': 'inconnu@ayyou.sn',
            'password': self.password
        }
        response = self.client.post(self.login_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_09_utilisateur_non_verifie(self):
        """9. Utilisateur non vérifié (est_verifie=False) refusé avec HTTP 403 et détails."""
        self.user.est_verifie = False
        self.user.save(update_fields=['est_verifie'])

        payload = {
            'identifier': self.email,
            'password': self.password
        }
        response = self.client.post(self.login_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertTrue(response.data['errors']['verification_required'])

    def test_10_utilisateur_inactif(self):
        """10. Utilisateur inactif (est_actif=False) refusé."""
        self.user.est_actif = False
        self.user.save(update_fields=['est_actif'])

        payload = {
            'identifier': self.email,
            'password': self.password
        }
        response = self.client.post(self.login_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_11_absence_identifier(self):
        """11. Rejet si le champ identifier est absent."""
        payload = {
            'password': self.password
        }
        response = self.client.post(self.login_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_12_absence_password(self):
        """12. Rejet si le champ password est absent."""
        payload = {
            'identifier': self.email
        }
        response = self.client.post(self.login_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_13_presence_access_token(self):
        """13. Vérification de la présence de l'Access Token JWT."""
        payload = {'identifier': self.email, 'password': self.password}
        response = self.client.post(self.login_url, payload, format='json')
        self.assertIn('access', response.data)
        self.assertTrue(len(response.data['access']) > 20)

    def test_14_presence_refresh_token(self):
        """14. Vérification de la présence du Refresh Token JWT."""
        payload = {'identifier': self.email, 'password': self.password}
        response = self.client.post(self.login_url, payload, format='json')
        self.assertIn('refresh', response.data)
        self.assertTrue(len(response.data['refresh']) > 20)

    def test_15_presence_informations_utilisateur(self):
        """15. Présence des informations profil utilisateur dans la réponse."""
        payload = {'identifier': self.email, 'password': self.password}
        response = self.client.post(self.login_url, payload, format='json')
        user_data = response.data['utilisateur']
        self.assertEqual(user_data['id'], self.user.id)
        self.assertEqual(user_data['email'], self.email)
        self.assertEqual(user_data['prenom'], 'Fatou')
        self.assertEqual(user_data['nom'], 'Sow')
        self.assertTrue(user_data['est_verifie'])

    def test_16_absence_password_dans_reponse(self):
        """16. Absence totale du mot de passe dans la réponse API."""
        payload = {'identifier': self.email, 'password': self.password}
        response = self.client.post(self.login_url, payload, format='json')
        self.assertNotIn('password', response.data['utilisateur'])
        self.assertNotIn('password', response.data)

    def test_17_absence_hash_password_dans_reponse(self):
        """17. Absence totale du hash de mot de passe dans la réponse API."""
        payload = {'identifier': self.email, 'password': self.password}
        response = self.client.post(self.login_url, payload, format='json')
        content_str = str(response.content)
        self.assertNotIn('pbkdf2', content_str)
        self.assertNotIn('argon2', content_str)

    def test_18_absence_otp_dans_reponse(self):
        """18. Absence totale de code OTP ou de secret dans la réponse de connexion."""
        payload = {'identifier': self.email, 'password': self.password}
        response = self.client.post(self.login_url, payload, format='json')
        self.assertNotIn('otp', response.data)
        self.assertNotIn('code', response.data)

    def test_19_mise_a_jour_derniere_connexion(self):
        """19. Vérifier que Utilisateur.derniere_connexion est mis à jour lors du login."""
        anc_connexion = self.user.derniere_connexion
        payload = {'identifier': self.email, 'password': self.password}
        self.client.post(self.login_url, payload, format='json')
        self.user.refresh_from_db()
        self.assertIsNotNone(self.user.derniere_connexion)
        if anc_connexion:
            self.assertGreater(self.user.derniere_connexion, anc_connexion)

    def test_20_ancien_otp_non_expose(self):
        """20. Vérifier que les anciens OTP ne sont ni exposés ni altérés inutilement."""
        payload = {'identifier': self.email, 'password': self.password}
        self.client.post(self.login_url, payload, format='json')
        otps = VerificationOTP.objects.filter(utilisateur=self.user)
        for otp in otps:
            self.assertTrue(otp.est_utilise)

    def test_21_jwt_valide(self):
        """21. Decodage et validation du token JWT Access généré."""
        payload = {'identifier': self.email, 'password': self.password}
        response = self.client.post(self.login_url, payload, format='json')
        access_token_str = response.data['access']
        token = AccessToken(access_token_str)
        self.assertEqual(str(token['user_id']), str(self.user.id))

    def test_22_endpoint_protege_avec_bearer_token(self):
        """22. Validation réelle du token Bearer JWT via JWTAuthentication de DRF."""
        from rest_framework_simplejwt.authentication import JWTAuthentication
        from rest_framework.test import APIRequestFactory

        payload = {'identifier': self.email, 'password': self.password}
        login_res = self.client.post(self.login_url, payload, format='json')
        access_token = login_res.data['access']

        # Créer une requête simulant le Header Authorization: Bearer <token>
        factory = APIRequestFactory()
        request = factory.get('/api/users/me/', HTTP_AUTHORIZATION=f'Bearer {access_token}')

        # Authentifier la requête via le middleware SimpleJWT
        auth_res = JWTAuthentication().authenticate(request)
        self.assertIsNotNone(auth_res)
        user_auth, token_auth = auth_res
        self.assertEqual(user_auth.id, self.user.id)
        self.assertEqual(user_auth.email, self.email)

    def test_23_login_pro_status_response(self):
        """23. Vérifier que le login retourne pro_status, roles et merchant_status/driver_status."""
        from apps.users.models import Role, UtilisateurRole
        from apps.catalog.models import Etablissement

        # 1. Tester utilisateur Client pur
        res1 = self.client.post(self.login_url, {'identifier': self.email, 'password': self.password})
        self.assertEqual(res1.status_code, status.HTTP_200_OK)
        self.assertEqual(res1.data['utilisateur']['pro_status'], 'NONE')
        self.assertIn('CLIENT', res1.data['utilisateur']['roles'])

        # 2. Inscrire un gérant de restaurant (EN_ATTENTE)
        resto_payload = {
            "email": "resto.login.test@ayyou.com",
            "numero_telephone": "+221778889900",
            "password": "Password123!",
            "password_confirm": "Password123!",
            "prenom": "Resto",
            "nom": "Owner",
            "nom_etablissement": "Resto Login Test",
            "adresse": "Dakar"
        }
        self.client.post(reverse('pro_api:register_restaurant'), resto_payload, format='json')

        # Login restaurant candidate (EN_ATTENTE)
        res2 = self.client.post(self.login_url, {'identifier': "resto.login.test@ayyou.com", 'password': "Password123!"})
        self.assertEqual(res2.status_code, status.HTTP_200_OK)
        self.assertEqual(res2.data['utilisateur']['pro_status'], 'PENDING')
        self.assertEqual(res2.data['utilisateur']['merchant_status'], 'EN_ATTENTE')
        self.assertIn('RESTAURANT', res2.data['utilisateur']['roles'])

        # 3. Approuver l'établissement par Super Admin
        etab = Etablissement.objects.get(id=res2.data['utilisateur']['etablissement']['id'])
        etab.statut_verification = Etablissement.STATUT_VALIDE
        etab.save()

        # Login restaurant candidate (VALIDE)
        res3 = self.client.post(self.login_url, {'identifier': "resto.login.test@ayyou.com", 'password': "Password123!"})
        self.assertEqual(res3.status_code, status.HTTP_200_OK)
        self.assertEqual(res3.data['utilisateur']['pro_status'], 'APPROVED')
        self.assertEqual(res3.data['utilisateur']['merchant_status'], 'VALIDE')
        self.assertTrue(res3.data['utilisateur']['etablissement']['est_verifie'])

        # 4. Rejeter l'établissement par Super Admin
        etab.statut_verification = Etablissement.STATUT_REFUSE
        etab.save()

        # Login restaurant candidate (REFUSE)
        res4 = self.client.post(self.login_url, {'identifier': "resto.login.test@ayyou.com", 'password': "Password123!"})
        self.assertEqual(res4.status_code, status.HTTP_200_OK)
        self.assertEqual(res4.data['utilisateur']['pro_status'], 'REJECTED')
        self.assertEqual(res4.data['utilisateur']['merchant_status'], 'REFUSE')
        self.assertFalse(res4.data['utilisateur']['etablissement']['est_verifie'])



