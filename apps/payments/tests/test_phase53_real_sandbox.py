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


class Phase53RealSandboxTest(TestCase):
    """
    Test d'intégration complet validant le parcours réel Phase 5.3 avec le tunnel Ngrok et PayDunya Sandbox.
    """

    def setUp(self):
        self.client = APIClient()

        # Client AYYOU
        self.user = Utilisateur.objects.create_user(
            numero_telephone='+221778889900',
            email='client.phase53@ayyou.com',
            prenom='Babacar',
            nom='Faye'
        )

        # Propriétaire & Établissement
        self.proprio = Utilisateur.objects.create_user(
            numero_telephone='+221771112233',
            email='resto.phase53@ayyou.com',
            prenom='Ousmane',
            nom='Kane'
        )
        self.etablissement = Etablissement.objects.create(
            proprietaire=self.proprio,
            nom="Le Baobab Gourmet",
            type_etablissement=Etablissement.TYPE_RESTAURANT,
            statut_verification=Etablissement.STATUT_VALIDE
        )

        # Commande client (Montant total = 12 500 FCFA)
        self.commande = Commande.objects.create(
            utilisateur=self.user,
            numero_commande="AYY-20260921-TEST53",
            statut=Commande.STATUT_EN_ATTENTE_PAIEMENT,
            sous_total=Decimal('10000.00'),
            frais_livraison=Decimal('2500.00'),
            total=Decimal('12500.00'),
            adresse_livraison="Mermoz Pyrotechnie, Dakar",
            nom_destinataire="Babacar Faye",
            telephone_destinataire="+221778889900"
        )
        self.sous_commande = SousCommande.objects.create(
            commande=self.commande,
            etablissement=self.etablissement,
            statut=Commande.STATUT_EN_ATTENTE_PAIEMENT,
            sous_total=Decimal('10000.00'),
            frais_livraison=Decimal('2500.00'),
            total=Decimal('12500.00')
        )

    @patch('apps.payments.paydunya_service.PaydunyaService.creer_facture_checkout')
    @patch('apps.payments.paydunya_service.PaydunyaService.verifier_facture')
    def test_full_sandbox_payment_workflow_with_ngrok_ipn(self, mock_verifier, mock_creer):
        # Configuration des mocks PayDunya Sandbox
        mock_creer.return_value = {
            'success': True,
            'token': 'SANDBOX_TOKEN_PHASE53_ABC',
            'checkout_url': 'https://app.paydunya.com/sandbox-checkout/invoice/SANDBOX_TOKEN_PHASE53_ABC',
            'response_code': '00',
            'description': 'Invoice created successfully'
        }

        # 1. ÉTAPE 1 : Initiation du paiement via POST /api/payments/initiate/
        self.client.force_authenticate(user=self.user)
        initiate_url = reverse('payments:initiate-paydunya')

        # Le client transmet commande_id & methode
        payload = {
            'commande_id': self.commande.id,
            'methode': Paiement.METHODE_WAVE,
            # Le frontend tente d'envoyer un montant altéré (ex: 1.00 FCFA) qui DOIT être ignoré par le serveur
            'montant': '1.00'
        }

        res_initiate = self.client.post(initiate_url, payload, format='json')

        # Vérification réponses initiation
        self.assertEqual(res_initiate.status_code, status.HTTP_201_CREATED)
        self.assertIn('checkout_url', res_initiate.data)
        self.assertEqual(res_initiate.data['token'], 'SANDBOX_TOKEN_PHASE53_ABC')
        self.assertEqual(res_initiate.data['checkout_url'], 'https://app.paydunya.com/sandbox-checkout/invoice/SANDBOX_TOKEN_PHASE53_ABC')

        # Vérification que le montant enregistré est STRICTEMENT 12 500.00 FCFA
        paiement_db = Paiement.objects.get(id=res_initiate.data['payment_id'])
        self.assertEqual(paiement_db.montant, Decimal('12500.00'))
        self.assertEqual(paiement_db.statut, Paiement.STATUT_INITIE)
        self.assertEqual(paiement_db.transaction_externe, 'SANDBOX_TOKEN_PHASE53_ABC')

        # 2. ÉTAPE 2 : Réception du Webhook IPN transmis à https://running-custody-neatness.ngrok-free.dev/api/payments/ipn/
        mock_verifier.return_value = {
            'success': True,
            'status': 'completed',
            'response_code': '00',
            'custom_data': {
                'paiement_id': str(paiement_db.id),
                'commande_id': str(self.commande.id),
                'reference': paiement_db.reference
            }
        }

        ipn_url = reverse('payments:paydunya-ipn')
        ipn_payload = {'token': 'SANDBOX_TOKEN_PHASE53_ABC'}

        # 3. Premier appel IPN (Paiement effectué sur PayDunya)
        res_ipn_1 = self.client.post(ipn_url, ipn_payload, format='json')
        self.assertEqual(res_ipn_1.status_code, status.HTTP_200_OK)
        self.assertEqual(res_ipn_1.data['status'], 'success')

        # Refresh depuis la base de données
        paiement_db.refresh_from_db()
        self.commande.refresh_from_db()
        self.sous_commande.refresh_from_db()

        # 4. ÉTAPE 3 : Vérifications métier complètes post-paiement
        # A. Statut Paiement
        self.assertEqual(paiement_db.statut, Paiement.STATUT_PAYE)
        self.assertIsNotNone(paiement_db.date_paiement)

        # B. Statut Commande et Sous-Commandes
        self.assertEqual(self.commande.statut, Commande.STATUT_PAYEE)
        self.assertEqual(self.sous_commande.statut, Commande.STATUT_PAYEE)

        # C. Facture immuable créée et marquée payée
        facture = Facture.objects.get(commande=self.commande)
        self.assertTrue(facture.est_payee)
        self.assertEqual(facture.montant_total, Decimal('12500.00'))
        self.assertEqual(facture.nom_client_snapshot, "Babacar Faye")

        # D. Fiche de Livraison créée quand la commande devient PRETE
        from apps.deliveries.services import DeliveryService
        self.sous_commande.statut = Commande.STATUT_PRETE
        self.sous_commande.save()
        DeliveryService.synchroniser_statuts_apres_sous_commande(self.sous_commande)

        livraison = Livraison.objects.get(commande=self.commande)
        self.assertIsNotNone(livraison.token_qr)
        self.assertGreater(len(livraison.token_qr), 10)
        self.assertIsNotNone(livraison.code_validation)
        self.assertEqual(len(livraison.code_validation), 4)
        self.assertTrue(livraison.code_validation.isdigit())

        # 5. ÉTAPE 4 : Endpoint de statut GET /api/payments/transactions/{id}/status/
        status_url = reverse('payments:paiement-status-check', kwargs={'pk': paiement_db.id})
        res_status = self.client.get(status_url)
        self.assertEqual(res_status.status_code, status.HTTP_200_OK)
        self.assertTrue(res_status.data['est_paye'])
        self.assertEqual(res_status.data['statut'], Paiement.STATUT_PAYE)

        # 6. ÉTAPE 5 : Test d'idempotence (Deuxième appel IPN identique)
        res_ipn_2 = self.client.post(ipn_url, ipn_payload, format='json')
        self.assertEqual(res_ipn_2.status_code, status.HTTP_200_OK)
        self.assertEqual(res_ipn_2.data['status'], 'already_confirmed')

        # Garanti : 0 doublon de livraison et 0 doublon de facture
        self.assertEqual(Livraison.objects.filter(commande=self.commande).count(), 1)
        self.assertEqual(Facture.objects.filter(commande=self.commande).count(), 1)
