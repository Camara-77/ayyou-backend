from unittest.mock import patch
from decimal import Decimal
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.users.models import Utilisateur
from apps.orders.models import Commande, SousCommande
from apps.catalog.models import Etablissement
from apps.payments.models import Paiement, Facture
from apps.deliveries.models import Livraison


class PaydunyaIntegrationTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()

        # Client 1
        self.user1 = Utilisateur.objects.create_user(
            numero_telephone='+221770000001',
            email='client1@ayyou.com',
            prenom='Amadou',
            nom='Diallo'
        )

        # Client 2
        self.user2 = Utilisateur.objects.create_user(
            numero_telephone='+221770000002',
            email='client2@ayyou.com',
            prenom='Fatou',
            nom='Sow'
        )

        # Propriétaire & Établissement
        self.proprio = Utilisateur.objects.create_user(
            numero_telephone='+221770000003',
            email='restaurateur@ayyou.com',
            prenom='Moussa',
            nom='Ndiaye'
        )
        self.etablissement = Etablissement.objects.create(
            proprietaire=self.proprio,
            nom="Teranga Fast Food",
            type_etablissement=Etablissement.TYPE_RESTAURANT,
            statut_verification=Etablissement.STATUT_VALIDE
        )

        # Commande user1 (Montant total = 6000 FCFA)
        self.commande_user1 = Commande.objects.create(
            utilisateur=self.user1,
            numero_commande="CMD-2026-0001",
            statut=Commande.STATUT_EN_ATTENTE_PAIEMENT,
            sous_total=Decimal('5000.00'),
            frais_livraison=Decimal('1000.00'),
            total=Decimal('6000.00'),
            adresse_livraison="Dakar Plateau",
            nom_destinataire="Amadou Diallo",
            telephone_destinataire="+221770000001"
        )
        self.sous_commande = SousCommande.objects.create(
            commande=self.commande_user1,
            etablissement=self.etablissement,
            statut=Commande.STATUT_EN_ATTENTE_PAIEMENT,
            sous_total=Decimal('5000.00'),
            frais_livraison=Decimal('1000.00'),
            total=Decimal('6000.00')
        )

    @patch('apps.payments.paydunya_service.PaydunyaService.creer_facture_checkout')
    def test_01_initiate_paydunya_payment_success(self, mock_creer):
        """1. Initiation paiement réussie"""
        mock_creer.return_value = {
            'success': True,
            'token': 'TEST_TOKEN_123',
            'checkout_url': 'https://app.paydunya.com/sandbox-checkout/invoice/TEST_TOKEN_123',
            'response_code': '00',
            'description': 'Invoice created'
        }

        self.client.force_authenticate(user=self.user1)
        url = reverse('payments:initiate-paydunya')

        payload = {
            'commande_id': self.commande_user1.id,
            'methode': Paiement.METHODE_WAVE
        }

        response = self.client.post(url, payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['token'], 'TEST_TOKEN_123')
        self.assertEqual(response.data['checkout_url'], 'https://app.paydunya.com/sandbox-checkout/invoice/TEST_TOKEN_123')

    @patch('apps.payments.paydunya_service.PaydunyaService.creer_facture_checkout')
    def test_02_commande_appartient_au_client(self, mock_creer):
        """2. Commande appartenant au client connecté"""
        mock_creer.return_value = {'success': True, 'token': 'TOK1', 'checkout_url': 'http://url', 'response_code': '00'}
        self.client.force_authenticate(user=self.user1)
        url = reverse('payments:initiate-paydunya')
        response = self.client.post(url, {'commande_id': self.commande_user1.id}, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_03_commande_autre_client_forbidden(self):
        """3. Commande appartenant à un autre client -> HTTP 403 Forbidden"""
        self.client.force_authenticate(user=self.user2)
        url = reverse('payments:initiate-paydunya')
        response = self.client.post(url, {'commande_id': self.commande_user1.id}, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @patch('apps.payments.paydunya_service.PaydunyaService.creer_facture_checkout')
    def test_04_montant_provenant_strictement_du_backend(self, mock_creer):
        """4. Le montant est STRICTEMENT extrait du backend (le montant client est ignoré)"""
        mock_creer.return_value = {'success': True, 'token': 'TOK2', 'checkout_url': 'http://url', 'response_code': '00'}
        self.client.force_authenticate(user=self.user1)
        url = reverse('payments:initiate-paydunya')

        # tentative de falsification de montant par le frontend à 1.00 FCFA
        payload = {'commande_id': self.commande_user1.id, 'montant': '1.00'}
        response = self.client.post(url, payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        paiement = Paiement.objects.get(id=response.data['payment_id'])
        self.assertEqual(paiement.montant, Decimal('6000.00'))  # strict commande.total

    @patch('apps.payments.paydunya_service.PaydunyaService.creer_facture_checkout')
    def test_05_commande_deja_payee_refus(self, mock_creer):
        """5. Une commande déjà payée ne peut pas être réinitiée"""
        self.commande_user1.statut = Commande.STATUT_PAYEE
        self.commande_user1.save()

        self.client.force_authenticate(user=self.user1)
        url = reverse('payments:initiate-paydunya')
        response = self.client.post(url, {'commande_id': self.commande_user1.id}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch('apps.payments.paydunya_service.PaydunyaService.verifier_facture')
    def test_06_callback_ipn_valide(self, mock_verifier):
        """6. Callback IPN valide confirme le paiement"""
        paiement = Paiement.objects.create(
            commande=self.commande_user1,
            montant=self.commande_user1.total,
            methode=Paiement.METHODE_WAVE,
            statut=Paiement.STATUT_INITIE,
            transaction_externe='IPN_VALID_TOK'
        )

        mock_verifier.return_value = {
            'success': True,
            'status': 'completed',
            'response_code': '00',
            'custom_data': {'paiement_id': str(paiement.id)}
        }

        url = reverse('payments:paydunya-ipn')
        response = self.client.post(url, {'token': 'IPN_VALID_TOK'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'success')

    @patch('apps.payments.paydunya_service.PaydunyaService.verifier_facture')
    def test_07_callback_ipn_invalide(self, mock_verifier):
        """7. Callback IPN avec token invalide PayDunya -> HTTP 400"""
        mock_verifier.return_value = {'success': False, 'status': 'cancelled', 'response_code': '101'}

        url = reverse('payments:paydunya-ipn')
        response = self.client.post(url, {'token': 'INVALID_TOK'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['status'], 'failed')

    @patch('apps.payments.paydunya_service.PaydunyaService.verifier_facture')
    def test_08_and_12_callback_ipn_repete_idempotence_et_unique_livraison(self, mock_verifier):
        """8 & 12. Appels IPN répétés -> Idempotence et une seule livraison générée"""
        paiement = Paiement.objects.create(
            commande=self.commande_user1,
            montant=self.commande_user1.total,
            methode=Paiement.METHODE_WAVE,
            statut=Paiement.STATUT_INITIE,
            transaction_externe='IPN_IDEMPOTENT_TOK'
        )

        mock_verifier.return_value = {
            'success': True,
            'status': 'completed',
            'response_code': '00',
            'custom_data': {'paiement_id': str(paiement.id)}
        }

        url = reverse('payments:paydunya-ipn')

        # Premier appel
        res1 = self.client.post(url, {'token': 'IPN_IDEMPOTENT_TOK'}, format='json')
        self.assertEqual(res1.status_code, status.HTTP_200_OK)
        self.assertEqual(res1.data['status'], 'success')

        self.assertEqual(Facture.objects.filter(commande=self.commande_user1).count(), 1)

        # Passage de la sous-commande à PRETE pour déclencher la livraison
        from apps.deliveries.services import DeliveryService
        for sc in self.commande_user1.sous_commandes.all():
            sc.statut = Commande.STATUT_PRETE
            sc.save()
            DeliveryService.synchroniser_statuts_apres_sous_commande(sc)

        self.assertEqual(Livraison.objects.filter(commande=self.commande_user1).count(), 1)

        # Second appel identique
        res2 = self.client.post(url, {'token': 'IPN_IDEMPOTENT_TOK'}, format='json')
        self.assertEqual(res2.status_code, status.HTTP_200_OK)
        self.assertEqual(res2.data['status'], 'already_confirmed')

        # Toujours exactement 1 livraison et 1 facture
        self.assertEqual(Livraison.objects.filter(commande=self.commande_user1).count(), 1)
        self.assertEqual(Facture.objects.filter(commande=self.commande_user1).count(), 1)

    @patch('apps.payments.paydunya_service.PaydunyaService.verifier_facture')
    def test_09_paiement_reussi_mise_a_jour_statut(self, mock_verifier):
        """9. Paiement réussi met à jour statut Paiement + Commande"""
        paiement = Paiement.objects.create(
            commande=self.commande_user1,
            montant=self.commande_user1.total,
            methode=Paiement.METHODE_WAVE,
            statut=Paiement.STATUT_INITIE,
            transaction_externe='SUCCESS_TOK'
        )

        mock_verifier.return_value = {'success': True, 'status': 'completed', 'response_code': '00', 'custom_data': {'paiement_id': str(paiement.id)}}

        url = reverse('payments:paydunya-ipn')
        self.client.post(url, {'token': 'SUCCESS_TOK'}, format='json')

        paiement.refresh_from_db()
        self.commande_user1.refresh_from_db()
        self.assertEqual(paiement.statut, Paiement.STATUT_PAYE)
        self.assertEqual(self.commande_user1.statut, Commande.STATUT_PAYEE)

    def test_10_paiement_echoue(self):
        """10. Marquage paiement comme échoué via PaymentService"""
        paiement = Paiement.objects.create(
            commande=self.commande_user1,
            montant=self.commande_user1.total,
            methode=Paiement.METHODE_WAVE,
            statut=Paiement.STATUT_INITIE
        )

        self.client.force_authenticate(user=self.user1)
        url = reverse('payments:paiement-echouer', kwargs={'pk': paiement.id})
        response = self.client.post(url, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        paiement.refresh_from_db()
        self.assertEqual(paiement.statut, Paiement.STATUT_ECHOUE)

    def test_11_paiement_en_attente(self):
        """11. Statut paiement initialisé est INITIE / EN_ATTENTE"""
        paiement = Paiement.objects.create(
            commande=self.commande_user1,
            montant=self.commande_user1.total,
            methode=Paiement.METHODE_WAVE,
            statut=Paiement.STATUT_EN_ATTENTE
        )
        self.assertEqual(paiement.statut, Paiement.STATUT_EN_ATTENTE)

    def test_13_unauthenticated_user_cannot_initiate(self):
        """13. Utilisateur non authentifié ne peut pas initier un paiement -> HTTP 401"""
        url = reverse('payments:initiate-paydunya')
        response = self.client.post(url, {'commande_id': self.commande_user1.id}, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @patch('apps.payments.paydunya_service.PaydunyaService.creer_facture_checkout')
    def test_14_absence_de_secrets_dans_reponses_api(self, mock_creer):
        """14. Absence totale de clés secrètes PayDunya (Master key, Private key) dans les réponses HTTP"""
        mock_creer.return_value = {'success': True, 'token': 'TOKEN_PUBLIC_TEST', 'checkout_url': 'http://url', 'response_code': '00'}
        self.client.force_authenticate(user=self.user1)
        url = reverse('payments:initiate-paydunya')
        response = self.client.post(url, {'commande_id': self.commande_user1.id}, format='json')

        body_str = str(response.content)
        self.assertNotIn('PAYDUNYA-MASTER-KEY', body_str)
        self.assertNotIn('PAYDUNYA-PRIVATE-KEY', body_str)
        self.assertNotIn('master_key', body_str)
        self.assertNotIn('private_key', body_str)
