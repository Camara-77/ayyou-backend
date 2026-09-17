from django.test import TestCase
from django.db.utils import IntegrityError
from django.utils import timezone
from datetime import timedelta
from apps.users.models import Utilisateur, ProfilClient, Role, UtilisateurRole


class UtilisateurModelTestCase(TestCase):
    """
    Tests unitaires pour le modèle Utilisateur, ProfilClient, Role et UtilisateurRole.
    """

    def setUp(self):
        self.user_data = {
            'email': 'client.test@ayyou.com',
            'numero_telephone': '+221771234567',
            'password': 'SuperMotDePasse@2025',
            'prenom': 'Amine',
            'nom': 'Benali'
        }

    def test_01_creation_utilisateur(self):
        """1. Tester la création réussie d'un Utilisateur."""
        user = Utilisateur.objects.create_user(**self.user_data)
        self.assertIsNotNone(user.id)
        self.assertEqual(user.email, 'client.test@ayyou.com')
        self.assertEqual(user.numero_telephone, '+221771234567')
        self.assertEqual(user.prenom, 'Amine')
        self.assertEqual(user.nom, 'Benali')
        self.assertTrue(user.est_actif)
        self.assertFalse(user.est_verifie)

    def test_02_hashage_mot_de_passe(self):
        """2. Tester le hachage sécurisé du mot de passe."""
        user = Utilisateur.objects.create_user(**self.user_data)
        self.assertTrue(user.check_password('SuperMotDePasse@2025'))
        self.assertFalse(user.check_password('MauvaisMotDePasse'))

    def test_03_impossibilite_recuperer_mot_de_passe_en_clair(self):
        """3. Tester que le mot de passe n'est jamais stocké en clair."""
        user = Utilisateur.objects.create_user(**self.user_data)
        self.assertNotEqual(user.password, 'SuperMotDePasse@2025')
        self.assertTrue(user.password.startswith('pbkdf2_sha256$') or '$' in user.password)

    def test_04_unicite_email(self):
        """4. Tester l'unicité stricte de l'email."""
        Utilisateur.objects.create_user(**self.user_data)
        duplicate_data = self.user_data.copy()
        duplicate_data['numero_telephone'] = '+221779998877'
        duplicate_data['email'] = 'CLIENT.TEST@AYYOU.COM'  # Case insensitive test

        with self.assertRaises((IntegrityError, Exception)):
            Utilisateur.objects.create_user(**duplicate_data)

    def test_05_unicite_numero_telephone(self):
        """5. Tester l'unicité stricte du numéro de téléphone."""
        Utilisateur.objects.create_user(**self.user_data)
        duplicate_data = self.user_data.copy()
        duplicate_data['email'] = 'autre.user@ayyou.com'

        with self.assertRaises(IntegrityError):
            Utilisateur.objects.create_user(**duplicate_data)

    def test_06_creation_profil_client(self):
        """6. Tester la création d'un ProfilClient."""
        user = Utilisateur.objects.create_user(**self.user_data)
        profil = ProfilClient.objects.create(utilisateur=user)
        self.assertIsNotNone(profil.id)
        self.assertEqual(profil.utilisateur, user)

    def test_07_creation_role(self):
        """7. Tester la création d'un Role."""
        role = Role.objects.create(nom=Role.CLIENT, description="Rôle client acheteur")
        self.assertIsNotNone(role.id)
        self.assertEqual(role.nom, Role.CLIENT)

    def test_08_attribution_role(self):
        """8. Tester l'attribution d'un rôle à un utilisateur."""
        user = Utilisateur.objects.create_user(**self.user_data)
        role = Role.objects.create(nom=Role.CLIENT)
        user_role = UtilisateurRole.objects.create(utilisateur=user, role=role)
        self.assertIsNotNone(user_role.id)
        self.assertEqual(user_role.utilisateur, user)
        self.assertEqual(user_role.role, role)

    def test_09_impossibilite_dupliquer_role(self):
        """9. Tester l'impossibilité de dupliquer un rôle pour un même utilisateur."""
        user = Utilisateur.objects.create_user(**self.user_data)
        role = Role.objects.create(nom=Role.CLIENT)
        UtilisateurRole.objects.create(utilisateur=user, role=role)

        with self.assertRaises(IntegrityError):
            UtilisateurRole.objects.create(utilisateur=user, role=role)

    def test_12_relation_utilisateur_profil_client(self):
        """12. Tester la relation 1 ─── 1 entre Utilisateur et ProfilClient."""
        user = Utilisateur.objects.create_user(**self.user_data)
        ProfilClient.objects.create(utilisateur=user)
        self.assertEqual(user.profil_client.utilisateur, user)

    def test_13_relation_utilisateur_role(self):
        """13. Tester la relation Utilisateur → Role."""
        user = Utilisateur.objects.create_user(**self.user_data)
        role_client = Role.objects.create(nom=Role.CLIENT)
        role_vendeur = Role.objects.create(nom=Role.VENDEUR)

        UtilisateurRole.objects.create(utilisateur=user, role=role_client)
        UtilisateurRole.objects.create(utilisateur=user, role=role_vendeur)

        roles = [ur.role.nom for ur in user.roles_attribues.all()]
        self.assertIn(Role.CLIENT, roles)
        self.assertIn(Role.VENDEUR, roles)
        self.assertEqual(len(roles), 2)
