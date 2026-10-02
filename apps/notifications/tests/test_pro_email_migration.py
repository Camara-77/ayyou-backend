import os
from unittest.mock import patch
from django.test import TestCase, override_settings
from django.core import mail
from django.db import transaction
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status

from apps.users.models import Utilisateur, Role, UtilisateurRole, ProfilLivreur
from apps.catalog.models import Etablissement
from apps.notifications.models import Notification
from apps.notifications.email_service import EmailNotificationService


class ProEmailMigrationTestCase(TestCase):
    """
    Suite de tests automatisés pour valider la migration de l'envoi d'emails n8n vers Django direct via SMTP.
    Couvre les 6 scénarios :
    - Restaurant Approuvé / Refusé
    - Vendeur Approuvé / Refusé
    - Livreur Approuvé / Refusé
    """

    def setUp(self):
        self.client = APIClient()

        # SuperAdmin
        self.superadmin = Utilisateur.objects.create_superuser(
            email='admin_email_test@ayyou.com',
            numero_telephone='+221770000000',
            password='Password123!',
            prenom='Admin',
            nom='AYYOU'
        )
        self.client.force_authenticate(user=self.superadmin)

        # Utilisateur candidat pro
        self.pro_user = Utilisateur.objects.create_user(
            email='pro_candidat_test@ayyou.com',
            numero_telephone='+221771112233',
            password='Password123!',
            prenom='Mamadou',
            nom='Diallo'
        )

        # Restaurant test
        self.restaurant = Etablissement.objects.create(
            nom="Dakar Grill Restaurant",
            type_etablissement=Etablissement.TYPE_RESTAURANT,
            proprietaire=self.pro_user,
            adresse="Plateau, Dakar",
            statut_verification=Etablissement.STATUT_EN_ATTENTE
        )

        # Vendeur à domicile test
        self.vendeur = Etablissement.objects.create(
            nom="Chez Tata Amina Vendeur",
            type_etablissement=Etablissement.TYPE_VENDEUR,
            proprietaire=self.pro_user,
            adresse="Yoff, Dakar",
            statut_verification=Etablissement.STATUT_EN_ATTENTE
        )

        # Livreur test
        self.driver = ProfilLivreur.objects.create(
            utilisateur=self.pro_user,
            type_vehicule=ProfilLivreur.VEHICULE_MOTO,
            statut_verification=ProfilLivreur.STATUT_EN_ATTENTE
        )

    @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    @patch('urllib.request.urlopen')
    def test_restaurant_approval_email(self, mock_n8n):
        """1. Approval Restaurant : Django envoie direct l'email sans appeler n8n."""
        url = reverse('admin_panel:business-approve', args=[self.restaurant.id])
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.patch(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.restaurant.refresh_from_db()
        self.assertEqual(self.restaurant.statut_verification, Etablissement.STATUT_VALIDE)

        # Vérifier l'email dans la boite d'envoi locmem
        self.assertEqual(len(mail.outbox), 1)
        sent_email = mail.outbox[0]

        self.assertIn('pro_candidat_test@ayyou.com', sent_email.to)
        self.assertIn('Dakar Grill Restaurant', sent_email.body)
        self.assertIn('validé', sent_email.subject.lower())
        self.assertIn('/pro/login', sent_email.body)

        # Aucun appel au Webhook n8n
        mock_n8n.assert_not_called()

        # Pas de secret/password/token dans le body
        self.assertNotIn('Password123!', sent_email.body)
        self.assertNotIn('secret', sent_email.body.lower())

    @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    @patch('urllib.request.urlopen')
    def test_restaurant_rejection_email(self, mock_n8n):
        """2. Rejection Restaurant : Django envoie l'email de refus avec motif."""
        url = reverse('admin_panel:business-reject', args=[self.restaurant.id])
        motif = "Registre de commerce NINEA illisible"
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.patch(url, {'motif': motif}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.restaurant.refresh_from_db()
        self.assertEqual(self.restaurant.statut_verification, Etablissement.STATUT_REFUSE)

        self.assertEqual(len(mail.outbox), 1)
        sent_email = mail.outbox[0]

        self.assertIn('pro_candidat_test@ayyou.com', sent_email.to)
        self.assertIn('Registre de commerce NINEA illisible', sent_email.body)

        mock_n8n.assert_not_called()

    @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    @patch('urllib.request.urlopen')
    def test_vendeur_approval_email(self, mock_n8n):
        """3. Approval Vendeur à domicile : Email envoyé avec lien /vendeur/login."""
        url = reverse('admin_panel:business-approve', args=[self.vendeur.id])
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.patch(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.vendeur.refresh_from_db()
        self.assertEqual(self.vendeur.statut_verification, Etablissement.STATUT_VALIDE)

        self.assertEqual(len(mail.outbox), 1)
        sent_email = mail.outbox[0]

        self.assertIn('pro_candidat_test@ayyou.com', sent_email.to)
        self.assertIn('/vendeur/login', sent_email.body)

        mock_n8n.assert_not_called()

    @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    @patch('urllib.request.urlopen')
    def test_vendeur_rejection_email(self, mock_n8n):
        """4. Rejection Vendeur à domicile : Email de refus envoyé avec le motif."""
        url = reverse('admin_panel:business-reject', args=[self.vendeur.id])
        motif = "Certificat d'hygiène manquant"
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.patch(url, {'motif': motif}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.vendeur.refresh_from_db()
        self.assertEqual(self.vendeur.statut_verification, Etablissement.STATUT_REFUSE)

        self.assertEqual(len(mail.outbox), 1)
        sent_email = mail.outbox[0]

        self.assertIn("hygiène manquant", sent_email.body)

        mock_n8n.assert_not_called()

    @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    @patch('urllib.request.urlopen')
    def test_driver_approval_email(self, mock_n8n):
        """5. Approval Livreur : Email envoyé avec lien /delivery/login."""
        url = reverse('admin_panel:driver-approve', args=[self.driver.id])
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.patch(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.driver.refresh_from_db()
        self.assertEqual(self.driver.statut_verification, ProfilLivreur.STATUT_VALIDE)

        self.assertEqual(len(mail.outbox), 1)
        sent_email = mail.outbox[0]

        self.assertIn('pro_candidat_test@ayyou.com', sent_email.to)
        self.assertIn('/delivery/login', sent_email.body)

        mock_n8n.assert_not_called()

    @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    @patch('urllib.request.urlopen')
    def test_driver_rejection_email(self, mock_n8n):
        """6. Rejection Livreur : Email de refus envoyé avec motif."""
        url = reverse('admin_panel:driver-reject', args=[self.driver.id])
        motif = "Permis de conduire périmé"
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.patch(url, {'motif': motif}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.driver.refresh_from_db()
        self.assertEqual(self.driver.statut_verification, ProfilLivreur.STATUT_REFUSE)

        self.assertEqual(len(mail.outbox), 1)
        sent_email = mail.outbox[0]

        self.assertIn('Permis de conduire périmé', sent_email.body)

        mock_n8n.assert_not_called()
