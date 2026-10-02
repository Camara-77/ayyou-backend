from decimal import Decimal
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from apps.users.models import Utilisateur, ProfilClient, ProfilLivreur, Role, UtilisateurRole
from apps.deliveries.models import Livraison
from apps.orders.models import Commande, SousCommande
from apps.authentication.services import RegistrationService



class UserModeSwitchingTestCase(APITestCase):
    """
    Suite de tests unitaires pour la gestion et le basculement du Mode Actif (CLIENT ↔ LIVREUR) - Étape 10.5.
    """

    def setUp(self):
        self.modes_url = reverse('users:user-modes')
        self.switch_mode_url = reverse('users:user-mode-switch')

        # 1. Créer un rôle CLIENT et LIVREUR
        self.role_client, _ = Role.objects.get_or_create(nom=Role.CLIENT)
        self.role_livreur, _ = Role.objects.get_or_create(nom=Role.LIVREUR)

        # 2. Créer un Client simple
        self.client_user = Utilisateur.objects.create_user(
            email='client.simple@ayyou.sn',
            numero_telephone='+221770001122',
            password='Password123!',
            prenom='Modou',
            nom='Fall',
            est_actif=True,
            est_verifie=True
        )
        ProfilClient.objects.create(utilisateur=self.client_user)
        UtilisateurRole.objects.create(utilisateur=self.client_user, role=self.role_client)

        # 3. Inscription idempotente d'un Livreur (Client + Livreur)
        self.driver_user, self.profil_livreur = RegistrationService.register_livreur({
            'prenom': 'Samba',
            'nom': 'Ndiaye',
            'email': 'samba.livreur@ayyou.sn',
            'numero_telephone': '+221770003344',
            'password': 'Password123!',
            'type_vehicule': ProfilLivreur.VEHICULE_MOTO,
            'immatriculation': 'DK-9988-BB'
        })
        self.profil_livreur.statut_verification = ProfilLivreur.STATUT_VALIDE
        self.profil_livreur.est_disponible = True
        self.profil_livreur.save()

    def test_01_inscription_livreur_profils_et_unicite(self):
        """
        TEST 1 : Inscription Livreur
        - Un seul Utilisateur créé
        - ProfilClient et ProfilLivreur tous deux présents
        - Aucun doublon Utilisateur
        """
        user_count = Utilisateur.objects.filter(email='samba.livreur@ayyou.sn').count()
        self.assertEqual(user_count, 1)
        self.assertTrue(ProfilClient.objects.filter(utilisateur=self.driver_user).exists())
        self.assertTrue(ProfilLivreur.objects.filter(utilisateur=self.driver_user).exists())

        roles = [ur.role.nom for ur in self.driver_user.roles_attribues.all()]
        self.assertIn(Role.CLIENT, roles)
        self.assertIn(Role.LIVREUR, roles)

    def test_02_modes_disponibles_utilisateur_double_role(self):
        """
        TEST 2 : Utilisateur Livreur + Client
        - modes disponibles = ['CLIENT', 'LIVREUR']
        """
        self.client.force_authenticate(user=self.driver_user)
        response = self.client.get(self.modes_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['active_mode'], 'CLIENT')
        self.assertEqual(response.data['available_modes'], ['CLIENT', 'LIVREUR'])
        self.assertTrue(response.data['can_switch_to_driver'])

    def test_03_passage_livreur_vers_client(self):
        """
        TEST 3 : Passage LIVREUR -> CLIENT
        - Changement réussi
        - ProfilLivreur conservé
        - Statut de vérification conservé
        """
        self.driver_user.mode_actif = Utilisateur.MODE_LIVREUR
        self.driver_user.save()
        self.client.force_authenticate(user=self.driver_user)

        response = self.client.patch(self.switch_mode_url, {'mode': 'CLIENT'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['active_mode'], 'CLIENT')

        self.driver_user.refresh_from_db()
        self.assertEqual(self.driver_user.mode_actif, 'CLIENT')
        self.assertEqual(self.driver_user.profil_livreur.statut_verification, ProfilLivreur.STATUT_VALIDE)

    def test_04_passage_client_vers_livreur(self):
        """
        TEST 4 : Passage CLIENT -> LIVREUR
        - Changement réussi
        - ProfilLivreur récupéré
        - Statut conservé
        """
        self.client.force_authenticate(user=self.driver_user)

        response = self.client.patch(self.switch_mode_url, {'mode': 'LIVREUR'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['active_mode'], 'LIVREUR')

        self.driver_user.refresh_from_db()
        self.assertEqual(self.driver_user.mode_actif, 'LIVREUR')
        self.assertEqual(self.driver_user.profil_livreur.statut_verification, ProfilLivreur.STATUT_VALIDE)

    def test_05_client_simple_ne_peut_pas_passer_en_livreur(self):
        """
        TEST 5 : Client normal ne possédant pas le rôle ou profil Livreur
        - Tentative de passage en mode LIVREUR -> HTTP 403 Forbidden
        """
        self.client.force_authenticate(user=self.client_user)

        response = self.client.patch(self.switch_mode_url, {'mode': 'LIVREUR'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn("Vous ne possédez pas le rôle ou profil livreur", response.data['detail'])

    def test_06_livreur_en_attente_operationnel_regles(self):
        """
        TEST 6 : Livreur au statut EN_ATTENTE
        - Est_disponible ne peut pas être True
        """
        self.profil_livreur.statut_verification = ProfilLivreur.STATUT_EN_ATTENTE
        self.profil_livreur.est_disponible = False
        self.profil_livreur.save()

        self.client.force_authenticate(user=self.driver_user)
        response = self.client.get(self.modes_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['driver_status'], ProfilLivreur.STATUT_EN_ATTENTE)

    def test_07_livreur_refuse_operationnel_regles(self):
        """
        TEST 7 : Livreur au statut REFUSE
        - Le statut reste REFUSE
        """
        self.profil_livreur.statut_verification = ProfilLivreur.STATUT_REFUSE
        self.profil_livreur.est_disponible = False
        self.profil_livreur.save()

        self.client.force_authenticate(user=self.driver_user)
        response = self.client.get(self.modes_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['driver_status'], ProfilLivreur.STATUT_REFUSE)

    def test_08_passage_en_mode_client_desactive_disponibilite(self):
        """
        TEST 8 : Passage en mode CLIENT
        - Aucune nouvelle mission ne doit lui être attribuée (est_disponible repasse à False)
        - Statut de vérification VALIDE conservé
        """
        self.driver_user.mode_actif = Utilisateur.MODE_LIVREUR
        self.driver_user.save()
        self.profil_livreur.est_disponible = True
        self.profil_livreur.save()

        self.client.force_authenticate(user=self.driver_user)
        response = self.client.patch(self.switch_mode_url, {'mode': 'CLIENT'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.profil_livreur.refresh_from_db()
        self.assertFalse(self.profil_livreur.est_disponible)
        self.assertEqual(self.profil_livreur.statut_verification, ProfilLivreur.STATUT_VALIDE)

    def test_09_livraison_existante_non_supprimee(self):
        """
        TEST 9 : Livraison existante
        - Le changement de mode ne supprime pas la livraison affectée au livreur.
        """
        commande = Commande.objects.create(
            utilisateur=self.client_user,
            total=Decimal('5000.00'),
            adresse_livraison='Dakar',
            nom_destinataire='Client Test',
            telephone_destinataire='+221770001122'
        )

        livraison = Livraison.objects.create(
            commande=commande,
            livreur=self.profil_livreur,
            statut=Livraison.STATUT_ACCEPTEE,
            token_qr='test_token_123456',
            code_validation='1234'
        )


        self.client.force_authenticate(user=self.driver_user)
        self.client.patch(self.switch_mode_url, {'mode': 'CLIENT'}, format='json')

        livraison.refresh_from_db()
        self.assertEqual(livraison.livreur, self.profil_livreur)
        self.assertEqual(livraison.statut, Livraison.STATUT_ACCEPTEE)

    def test_10_repetition_des_changements_de_mode(self):
        """
        TEST 10 : Répétition des changements de mode
        CLIENT -> LIVREUR -> CLIENT -> LIVREUR
        - Aucun doublon
        - Aucune perte de données
        - Statut inchangé
        """
        self.client.force_authenticate(user=self.driver_user)

        for _ in range(3):
            res1 = self.client.patch(self.switch_mode_url, {'mode': 'LIVREUR'}, format='json')
            self.assertEqual(res1.status_code, status.HTTP_200_OK)
            self.assertEqual(res1.data['active_mode'], 'LIVREUR')

            res2 = self.client.patch(self.switch_mode_url, {'mode': 'CLIENT'}, format='json')
            self.assertEqual(res2.status_code, status.HTTP_200_OK)
            self.assertEqual(res2.data['active_mode'], 'CLIENT')

        self.assertEqual(Utilisateur.objects.filter(email='samba.livreur@ayyou.sn').count(), 1)
        self.assertEqual(ProfilClient.objects.filter(utilisateur=self.driver_user).count(), 1)
        self.assertEqual(ProfilLivreur.objects.filter(utilisateur=self.driver_user).count(), 1)
        self.assertEqual(self.profil_livreur.statut_verification, ProfilLivreur.STATUT_VALIDE)
