from decimal import Decimal
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.users.models import Utilisateur
from apps.catalog.models import Etablissement, Categorie, Produit
from apps.orders.models import Commande, SousCommande, LigneCommande
from apps.payments.models import Paiement, Facture
from apps.payments.services import PaymentService


class PaiementAPITestCase(APITestCase):
    def setUp(self):
        # Client principal
        self.user_a = Utilisateur.objects.create_user(
            numero_telephone='+221770001111',
            email='user_a@ayyou.sn',
            prenom='Moussa',
            nom='Diop'
        )
        # Deuxième client (pour test d'isolation)
        self.user_b = Utilisateur.objects.create_user(
            numero_telephone='+221770002222',
            email='user_b@ayyou.sn',
            prenom='Fatou',
            nom='Ndiaye'
        )

        # Établissement et produit
        self.etablissement = Etablissement.objects.create(
            nom="Chez Loutcha",
            type_etablissement=Etablissement.TYPE_RESTAURANT,
            adresse="Plateau, Dakar",
            telephone="+221338210000"
        )
        self.categorie = Categorie.objects.create(nom="Plats Nationaux")
        self.produit = Produit.objects.create(
            etablissement=self.etablissement,
            categorie=self.categorie,
            nom="Thiéboudienne Rouge",
            prix_base=Decimal('4500.00'),
            est_disponible=True
        )

        # Commande pour User A
        self.commande_a = Commande.objects.create(
            utilisateur=self.user_a,
            sous_total=Decimal('4500.00'),
            frais_livraison=Decimal('1000.00'),
            total=Decimal('5500.00'),
            adresse_livraison="Point E, Dakar",
            nom_destinataire="Moussa Diop",
            telephone_destinataire="+221770001111"
        )
        self.sc_a = SousCommande.objects.create(
            commande=self.commande_a,
            etablissement=self.etablissement,
            sous_total=Decimal('4500.00'),
            frais_livraison=Decimal('1000.00'),
            total=Decimal('5500.00')
        )
        self.ligne_a = LigneCommande.objects.create(
            sous_commande=self.sc_a,
            produit=self.produit,
            nom_produit_snapshot="Thiéboudienne Rouge",
            quantite=1,
            prix_unitaire=Decimal('4500.00'),
            total_ligne=Decimal('4500.00')
        )

        # Commande pour User B
        self.commande_b = Commande.objects.create(
            utilisateur=self.user_b,
            sous_total=Decimal('9000.00'),
            frais_livraison=Decimal('1000.00'),
            total=Decimal('10000.00'),
            adresse_livraison="Almadies, Dakar",
            nom_destinataire="Fatou Ndiaye",
            telephone_destinataire="+221770002222"
        )

        self.list_tx_url = reverse('payments:paiement-list')
        self.list_facture_url = reverse('payments:facture-list')

    def test_1_unauthenticated_access_denied(self):
        """1. Vérifie le rejet de l'accès non authentifié (401)."""
        response_tx = self.client.get(self.list_tx_url)
        self.assertEqual(response_tx.status_code, status.HTTP_401_UNAUTHORIZED)

        response_fac = self.client.get(self.list_facture_url)
        self.assertEqual(response_fac.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_2_initier_paiement_success(self):
        """2. Vérifie l'initialisation réussie d'un paiement via l'API."""
        self.client.force_authenticate(user=self.user_a)
        payload = {
            'commande': self.commande_a.id,
            'methode': Paiement.METHODE_WAVE
        }
        response = self.client.post(self.list_tx_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['statut'], Paiement.STATUT_INITIE)
        self.assertTrue(response.data['reference'].startswith('PAY-'))
        self.assertEqual(Decimal(str(response.data['montant'])), Decimal('5500.00'))

    def test_3_ignorer_montant_client_tampering(self):
        """3. Vérifie que le montant envoyé par le client est ignoré au profit du total serveur."""
        self.client.force_authenticate(user=self.user_a)
        payload = {
            'commande': self.commande_a.id,
            'methode': Paiement.METHODE_WAVE,
            'montant': '1.00'  # Tentative de falsification de prix
        }
        response = self.client.post(self.list_tx_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        # Le montant doit être 5500.00 et non 1.00
        self.assertEqual(Decimal(str(response.data['montant'])), Decimal('5500.00'))

    def test_4_isolation_client_payer_commande_autre_utilisateur(self):
        """4. Vérifie qu'un client ne peut pas initier un paiement pour la commande d'un autre."""
        self.client.force_authenticate(user=self.user_a)
        payload = {
            'commande': self.commande_b.id,  # Commande appartenant à User B
            'methode': Paiement.METHODE_WAVE
        }
        response = self.client.post(self.list_tx_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('commande', response.data)

    def test_5_isolation_client_voir_transaction_autre_utilisateur(self):
        """5. Vérifie l'isolation des transactions de paiement entre utilisateurs."""
        # User B crée un paiement
        paiement_b = PaymentService.initier_paiement(self.commande_b, Paiement.METHODE_ORANGE_MONEY)

        # User A essaie de consulter le paiement de User B
        self.client.force_authenticate(user=self.user_a)
        detail_url = reverse('payments:paiement-detail', kwargs={'pk': paiement_b.id})
        response = self.client.get(detail_url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_6_confirmer_paiement_simulation(self):
        """6. Vérifie l'endpoint de confirmation de paiement et ses effets de bord."""
        self.client.force_authenticate(user=self.user_a)
        paiement = PaymentService.initier_paiement(self.commande_a, Paiement.METHODE_WAVE)

        confirm_url = reverse('payments:paiement-confirmer', kwargs={'pk': paiement.id})
        payload = {'transaction_externe': 'WAVE_TX_TEST_999'}
        response = self.client.post(confirm_url, payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['statut'], Paiement.STATUT_PAYE)
        self.assertEqual(response.data['transaction_externe'], 'WAVE_TX_TEST_999')

        # Vérifier la mise à jour de la commande
        self.commande_a.refresh_from_db()
        self.assertEqual(self.commande_a.statut, Commande.STATUT_PAYEE)

        # Vérifier la mise à jour de la sous-commande
        self.sc_a.refresh_from_db()
        self.assertEqual(self.sc_a.statut, Commande.STATUT_PAYEE)

        # Vérifier la génération de la facture
        facture = Facture.objects.get(commande=self.commande_a)
        self.assertTrue(facture.est_payee)
        self.assertIsNotNone(facture.date_paiement)
        self.assertEqual(facture.montant_total, Decimal('5500.00'))

    def test_7_echouer_paiement_simulation(self):
        """7. Vérifie l'endpoint de simulation d'échec de paiement."""
        self.client.force_authenticate(user=self.user_a)
        paiement = PaymentService.initier_paiement(self.commande_a, Paiement.METHODE_WAVE)

        echouer_url = reverse('payments:paiement-echouer', kwargs={'pk': paiement.id})
        response = self.client.post(echouer_url, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['statut'], Paiement.STATUT_ECHOUE)

    def test_8_annuler_paiement_simulation(self):
        """8. Vérifie l'endpoint de simulation d'annulation de paiement."""
        self.client.force_authenticate(user=self.user_a)
        paiement = PaymentService.initier_paiement(self.commande_a, Paiement.METHODE_WAVE)

        annuler_url = reverse('payments:paiement-annuler', kwargs={'pk': paiement.id})
        response = self.client.post(annuler_url, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['statut'], Paiement.STATUT_ANNULE)

    def test_9_bloquer_confirmation_paiement_deja_paye(self):
        """9. Vérifie l'idempotence de la confirmation pour un paiement déjà payé."""
        self.client.force_authenticate(user=self.user_a)
        paiement = PaymentService.initier_paiement(self.commande_a, Paiement.METHODE_WAVE)
        PaymentService.confirmer_paiement(paiement, "TX_1")

        confirm_url = reverse('payments:paiement-confirmer', kwargs={'pk': paiement.id})
        response = self.client.post(confirm_url, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['statut'], Paiement.STATUT_PAYE)

    def test_10_bloquer_confirmation_paiement_echoue_ou_annule(self):
        """10. Vérifie le rejet de la confirmation d'un paiement échoué ou annulé."""
        self.client.force_authenticate(user=self.user_a)
        paiement = PaymentService.initier_paiement(self.commande_a, Paiement.METHODE_WAVE)
        PaymentService.echouer_paiement(paiement, "Solde insuffisant")

        confirm_url = reverse('payments:paiement-confirmer', kwargs={'pk': paiement.id})
        response = self.client.post(confirm_url, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('detail', response.data)

    def test_11_bloquer_echec_ou_annulation_paiement_deja_paye(self):
        """11. Vérifie l'impossibilité de marquer comme échoué ou annulé un paiement déjà payé."""
        self.client.force_authenticate(user=self.user_a)
        paiement = PaymentService.initier_paiement(self.commande_a, Paiement.METHODE_WAVE)
        PaymentService.confirmer_paiement(paiement, "TX_PAID")

        echouer_url = reverse('payments:paiement-echouer', kwargs={'pk': paiement.id})
        response_echouer = self.client.post(echouer_url, format='json')
        self.assertEqual(response_echouer.status_code, status.HTTP_400_BAD_REQUEST)

        annuler_url = reverse('payments:paiement-annuler', kwargs={'pk': paiement.id})
        response_annuler = self.client.post(annuler_url, format='json')
        self.assertEqual(response_annuler.status_code, status.HTTP_400_BAD_REQUEST)

    def test_12_lister_et_consulter_factures(self):
        """12. Vérifie le listage et la consultation détaillée des factures du client."""
        paiement = PaymentService.initier_paiement(self.commande_a, Paiement.METHODE_WAVE)
        PaymentService.confirmer_paiement(paiement, "TX_FAC_1")

        self.client.force_authenticate(user=self.user_a)
        response_list = self.client.get(self.list_facture_url)
        self.assertEqual(response_list.status_code, status.HTTP_200_OK)
        raw_data = response_list.data['results'] if isinstance(response_list.data, dict) and 'results' in response_list.data else response_list.data
        self.assertEqual(len(raw_data), 1)

        facture_id = raw_data[0]['id']
        detail_url = reverse('payments:facture-detail', kwargs={'pk': facture_id})
        response_detail = self.client.get(detail_url)

        self.assertEqual(response_detail.status_code, status.HTTP_200_OK)
        self.assertEqual(response_detail.data['nom_client_snapshot'], "Moussa Diop")
        self.assertEqual(Decimal(str(response_detail.data['montant_total'])), Decimal('5500.00'))

    def test_13_isolation_client_voir_facture_autre_utilisateur(self):
        """13. Vérifie qu'un utilisateur ne peut pas voir la facture d'un autre utilisateur."""
        paiement_b = PaymentService.initier_paiement(self.commande_b, Paiement.METHODE_WAVE)
        PaymentService.confirmer_paiement(paiement_b, "TX_FAC_B")
        facture_b = Facture.objects.get(commande=self.commande_b)

        self.client.force_authenticate(user=self.user_a)
        detail_url = reverse('payments:facture-detail', kwargs={'pk': facture_b.id})
        response = self.client.get(detail_url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_14_methode_paiement_invalide(self):
        """14. Vérifie le rejet d'une méthode de paiement non supportée."""
        self.client.force_authenticate(user=self.user_a)
        payload = {
            'commande': self.commande_a.id,
            'methode': 'BITCOIN'
        }
        response = self.client.post(self.list_tx_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_15_reutilisation_paiement_existant(self):
        """15. Vérifie qu'un paiement non finalisé est mis à jour si ré-initié avec une autre méthode."""
        self.client.force_authenticate(user=self.user_a)
        payload1 = {'commande': self.commande_a.id, 'methode': Paiement.METHODE_WAVE}
        res1 = self.client.post(self.list_tx_url, payload1, format='json')
        id1 = res1.data['id']

        payload2 = {'commande': self.commande_a.id, 'methode': Paiement.METHODE_ORANGE_MONEY}
        res2 = self.client.post(self.list_tx_url, payload2, format='json')
        id2 = res2.data['id']

        self.assertEqual(id1, id2)
        self.assertEqual(res2.data['methode'], Paiement.METHODE_ORANGE_MONEY)
