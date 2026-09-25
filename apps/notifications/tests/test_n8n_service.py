import json
from unittest.mock import patch, MagicMock
from django.test import TestCase, override_settings, TransactionTestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from django.db import transaction

from apps.users.models import Utilisateur, ProfilLivreur
from apps.catalog.models import Etablissement
from apps.notifications.n8n_service import N8nNotificationService


class N8nNotificationServiceTestCase(TestCase):
    """
    Suite de tests unitaires et d'intégration pour le service n8n (Phase 13.6.D).
    Validation PRO Restaurant, Vendeur, Livreur, gestion des headers, résilience et anti-doublons.
    """

    def setUp(self):
        # Super Admin
        self.superadmin = Utilisateur.objects.create_user(
            email='admin_n8n@ayyou.com',
            numero_telephone='+221 77 000 99 88',
            password='AdminPassword123!',
            prenom='Super',
            nom='Admin',
            is_staff=True,
            is_superuser=True
        )

        self.client_admin = APIClient()
        self.client_admin.force_authenticate(user=self.superadmin)

        # Propriétaire Restaurant
        self.owner_restau = Utilisateur.objects.create_user(
            email='restau_owner@ayyou.com',
            numero_telephone='+221 77 111 22 33',
            password='Password123!',
            prenom='Amadou',
            nom='Diallo'
        )

        # Restaurant en attente
        self.restaurant = Etablissement.objects.create(
            nom="Chez Loutcha Dakar",
            type_etablissement=Etablissement.TYPE_RESTAURANT,
            proprietaire=self.owner_restau,
            adresse="Avenue Ponty",
            telephone="+221 33 821 00 00",
            statut_verification=Etablissement.STATUT_EN_ATTENTE
        )

        # Propriétaire Vendeur
        self.owner_vendeur = Utilisateur.objects.create_user(
            email='vendeur_owner@ayyou.com',
            numero_telephone='+221 77 444 55 66',
            password='Password123!',
            prenom='Fatou',
            nom='Sow'
        )

        # Vendeur en attente
        self.vendeur = Etablissement.objects.create(
            nom="Delices de Fatou",
            type_etablissement=Etablissement.TYPE_VENDEUR,
            proprietaire=self.owner_vendeur,
            adresse="Fann Résidence",
            telephone="+221 77 444 55 66",
            statut_verification=Etablissement.STATUT_EN_ATTENTE
        )

        # Livreur
        self.user_driver = Utilisateur.objects.create_user(
            email='driver_n8n@ayyou.com',
            numero_telephone='+221 77 777 88 99',
            password='Password123!',
            prenom='Moussa',
            nom='Ndiaye'
        )

        self.profil_driver = ProfilLivreur.objects.create(
            utilisateur=self.user_driver,
            type_vehicule=ProfilLivreur.VEHICULE_MOTO,
            immatriculation="DK-1234-AB",
            statut_verification=ProfilLivreur.STATUT_EN_ATTENTE
        )

    @patch('urllib.request.urlopen')
    @patch.dict('os.environ', {'N8N_PRO_APPROVAL_WEBHOOK_URL': 'http://localhost:5678/webhook/test', 'N8N_WEBHOOK_SECRET': 'test_secret_123'})
    def test_1_validation_restaurant(self, mock_urlopen):
        """1. Validation Restaurant (EN_ATTENTE -> VALIDE) : payload type RESTAURANT et webhook n8n déclenché."""
        mock_response = MagicMock()
        mock_response.getcode.return_value = 200
        mock_urlopen.return_value.__enter__.return_value = mock_response

        url = reverse('admin_panel:business-approve', kwargs={'pk': self.restaurant.id})
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client_admin.patch(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.restaurant.refresh_from_db()
        self.assertEqual(self.restaurant.statut_verification, Etablissement.STATUT_VALIDE)
        self.assertTrue(self.restaurant.est_verifie)

        # Vérification de l'appel HTTP n8n
        self.assertEqual(mock_urlopen.call_count, 1)
        req_arg = mock_urlopen.call_args[0][0]
        self.assertEqual(req_arg.full_url, 'http://localhost:5678/webhook/test')
        self.assertEqual(req_arg.headers.get('X-webhook-secret'), 'test_secret_123')

        payload = json.loads(req_arg.data.decode('utf-8'))
        self.assertEqual(payload['event'], 'PRO_ACCOUNT_APPROVED')
        self.assertEqual(payload['type'], 'RESTAURANT')
        self.assertEqual(payload['user_id'], self.owner_restau.id)
        self.assertEqual(payload['name'], 'Chez Loutcha Dakar')
        self.assertEqual(payload['email'], 'restau_owner@ayyou.com')
        self.assertEqual(payload['phone'], '+221 77 111 22 33')

    @patch('urllib.request.urlopen')
    @patch.dict('os.environ', {'N8N_PRO_APPROVAL_WEBHOOK_URL': 'http://localhost:5678/webhook/test', 'N8N_WEBHOOK_SECRET': 'test_secret_123'})
    def test_2_validation_vendeur(self, mock_urlopen):
        """2. Validation Vendeur (EN_ATTENTE -> VALIDE) : payload type VENDEUR."""
        mock_response = MagicMock()
        mock_response.getcode.return_value = 200
        mock_urlopen.return_value.__enter__.return_value = mock_response

        url = reverse('admin_panel:business-approve', kwargs={'pk': self.vendeur.id})
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client_admin.patch(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.vendeur.refresh_from_db()
        self.assertEqual(self.vendeur.statut_verification, Etablissement.STATUT_VALIDE)

        req_arg = mock_urlopen.call_args[0][0]
        payload = json.loads(req_arg.data.decode('utf-8'))
        self.assertEqual(payload['event'], 'PRO_ACCOUNT_APPROVED')
        self.assertEqual(payload['type'], 'VENDEUR')
        self.assertEqual(payload['user_id'], self.owner_vendeur.id)
        self.assertEqual(payload['name'], 'Delices de Fatou')
        self.assertEqual(payload['email'], 'vendeur_owner@ayyou.com')

    @patch('urllib.request.urlopen')
    @patch.dict('os.environ', {'N8N_PRO_APPROVAL_WEBHOOK_URL': 'http://localhost:5678/webhook/test', 'N8N_WEBHOOK_SECRET': 'test_secret_123'})
    def test_3_validation_livreur(self, mock_urlopen):
        """3. Validation Livreur (EN_ATTENTE -> VALIDE) : payload type LIVREUR."""
        mock_response = MagicMock()
        mock_response.getcode.return_value = 200
        mock_urlopen.return_value.__enter__.return_value = mock_response

        url = reverse('admin_panel:driver-approve', kwargs={'pk': self.profil_driver.id})
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client_admin.patch(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.profil_driver.refresh_from_db()
        self.assertEqual(self.profil_driver.statut_verification, ProfilLivreur.STATUT_VALIDE)

        req_arg = mock_urlopen.call_args[0][0]
        payload = json.loads(req_arg.data.decode('utf-8'))
        self.assertEqual(payload['event'], 'PRO_ACCOUNT_APPROVED')
        self.assertEqual(payload['type'], 'LIVREUR')
        self.assertEqual(payload['user_id'], self.user_driver.id)
        self.assertEqual(payload['name'], 'Moussa Ndiaye')
        self.assertEqual(payload['email'], 'driver_n8n@ayyou.com')
        self.assertEqual(payload['phone'], '+221 77 777 88 99')

    @patch('urllib.request.urlopen')
    @patch.dict('os.environ', {'N8N_PRO_APPROVAL_WEBHOOK_URL': 'http://localhost:5678/webhook/test'})
    def test_4_anti_doublon_valide_vers_valide(self, mock_urlopen):
        """4. Anti-doublons : Aucun nouvel événement si le compte est déjà VALIDE (VALIDE -> VALIDE)."""
        self.restaurant.statut_verification = Etablissement.STATUT_VALIDE
        self.restaurant.est_verifie = True
        self.restaurant.save()

        url = reverse('admin_panel:business-approve', kwargs={'pk': self.restaurant.id})
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client_admin.patch(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Aucun appel n8n ne doit être déclenché
        self.assertEqual(mock_urlopen.call_count, 0)

    @patch('urllib.request.urlopen', side_effect=Exception("Timeout / n8n inatteignable"))
    @patch.dict('os.environ', {'N8N_PRO_APPROVAL_WEBHOOK_URL': 'http://localhost:5678/webhook/test'})
    def test_5_erreur_http_n8n_ne_casse_pas_django(self, mock_urlopen):
        """5. Résilience : Une erreur n8n n'annule pas la validation Django DB (Django reste la source de vérité)."""
        url = reverse('admin_panel:business-approve', kwargs={'pk': self.restaurant.id})
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client_admin.patch(url)

        # L'API Django retourne HTTP 200 et la validation DB est préservée
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.restaurant.refresh_from_db()
        self.assertEqual(self.restaurant.statut_verification, Etablissement.STATUT_VALIDE)
        self.assertTrue(self.restaurant.est_verifie)

    @patch('urllib.request.urlopen')
    @patch.dict('os.environ', {'N8N_PRO_APPROVAL_WEBHOOK_URL': ''})
    def test_6_webhook_non_configure(self, mock_urlopen):
        """6. Webhook non configuré (URL vide) : Pas de crash, validation effectuée proprement."""
        url = reverse('admin_panel:business-approve', kwargs={'pk': self.restaurant.id})
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client_admin.patch(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.restaurant.refresh_from_db()
        self.assertEqual(self.restaurant.statut_verification, Etablissement.STATUT_VALIDE)
        self.assertEqual(mock_urlopen.call_count, 0)

    @patch('urllib.request.urlopen')
    @patch.dict('os.environ', {'N8N_PRO_APPROVAL_WEBHOOK_URL': 'http://localhost:5678/webhook/test', 'N8N_WEBHOOK_SECRET': 'mon_super_secret'})
    def test_7_presence_header_secret(self, mock_urlopen):
        """7. Présence du header X-Webhook-Secret."""
        mock_response = MagicMock()
        mock_response.getcode.return_value = 200
        mock_urlopen.return_value.__enter__.return_value = mock_response

        success = N8nNotificationService.send_pro_approval_for_etablissement(self.restaurant)
        self.assertTrue(success)

        req = mock_urlopen.call_args[0][0]
        self.assertEqual(req.headers.get('X-webhook-secret'), 'mon_super_secret')


class N8nTransactionOnCommitTestCase(TransactionTestCase):
    """
    Test spécifique pour vérifier l'exécution post-commit DB.
    """

    def setUp(self):
        self.user = Utilisateur.objects.create_user(
            email='driver_commit@ayyou.com',
            numero_telephone='+221 77 888 99 00',
            password='Password123!',
            prenom='Ousmane',
            nom='Baye'
        )

        self.driver = ProfilLivreur.objects.create(
            utilisateur=self.user,
            statut_verification=ProfilLivreur.STATUT_EN_ATTENTE
        )

    @patch('urllib.request.urlopen')
    @patch.dict('os.environ', {'N8N_PRO_APPROVAL_WEBHOOK_URL': 'http://localhost:5678/webhook/test'})
    def test_8_transaction_on_commit_explicite(self, mock_urlopen):
        """8. transaction.on_commit : L'appel HTTP n8n s'exécute uniquement après le commit DB."""
        mock_response = MagicMock()
        mock_response.getcode.return_value = 200
        mock_urlopen.return_value.__enter__.return_value = mock_response

        with transaction.atomic():
            self.driver.statut_verification = ProfilLivreur.STATUT_VALIDE
            self.driver.save()
            transaction.on_commit(
                lambda: N8nNotificationService.send_pro_approval_for_driver(self.driver)
            )
            # Avant le commit de la transaction, le webhook n'a pas été appelé
            self.assertEqual(mock_urlopen.call_count, 0)

        # Après le commit du bloc atomic(), l'appel HTTP a été effectué
        self.assertEqual(mock_urlopen.call_count, 1)
        payload = json.loads(mock_urlopen.call_args[0][0].data.decode('utf-8'))
        self.assertEqual(payload['user_id'], self.user.id)
        self.assertEqual(payload['type'], 'LIVREUR')
