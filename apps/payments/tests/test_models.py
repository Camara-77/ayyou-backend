from django.test import TestCase
from django.core.exceptions import ValidationError
from django.db.utils import IntegrityError
from decimal import Decimal
from django.utils import timezone

from apps.users.models import Utilisateur
from apps.orders.models import Commande, SousCommande, LigneCommande
from apps.catalog.models import Etablissement, Produit, Categorie
from apps.payments.models import Paiement, Facture
from apps.payments.services import PaymentService


class PaiementModelTestCase(TestCase):
    def setUp(self):
        self.user = Utilisateur.objects.create_user(
            numero_telephone='+221770001122',
            email='client.test@ayyou.sn',
            prenom='Moussa',
            nom='Diop'
        )
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
        self.commande = Commande.objects.create(
            utilisateur=self.user,
            sous_total=Decimal('4500.00'),
            frais_livraison=Decimal('1000.00'),
            total=Decimal('5500.00'),
            adresse_livraison="Point E, Dakar",
            nom_destinataire="Moussa Diop",
            telephone_destinataire="+221770001122"
        )

    def test_1_creation_paiement_reussie(self):
        """1. Vérifie la création valide d'un paiement."""
        paiement = Paiement.objects.create(
            commande=self.commande,
            montant=Decimal('5500.00'),
            methode=Paiement.METHODE_WAVE,
            statut=Paiement.STATUT_EN_ATTENTE
        )
        self.assertIsNotNone(paiement.id)
        self.assertTrue(paiement.reference.startswith('PAY-'))
        self.toEqual(paiement.montant, Decimal('5500.00'))
        self.assertEqual(paiement.statut, Paiement.STATUT_EN_ATTENTE)

    def toEqual(self, a, b):
        self.assertEqual(Decimal(str(a)), Decimal(str(b)))

    def test_2_generation_reference_unique(self):
        """2. Vérifie la génération automatique d'une référence unique."""
        p1 = Paiement.objects.create(
            commande=self.commande,
            montant=Decimal('2000.00'),
            methode=Paiement.METHODE_WAVE
        )
        p2 = Paiement.objects.create(
            commande=self.commande,
            montant=Decimal('3500.00'),
            methode=Paiement.METHODE_ORANGE_MONEY
        )
        self.assertNotEqual(p1.reference, p2.reference)
        self.assertTrue(p1.reference.startswith('PAY-'))
        self.assertTrue(p2.reference.startswith('PAY-'))

    def test_3_validation_montant_valide(self):
        """3. Vérifie l'acceptation d'un montant positif avec DecimalField."""
        paiement = Paiement(
            commande=self.commande,
            montant=Decimal('1250.50'),
            methode=Paiement.METHODE_CARTE_BANCAIRE
        )
        paiement.full_clean()
        paiement.save()
        self.assertEqual(paiement.montant, Decimal('1250.50'))

    def test_4_rejet_montant_negatif_ou_nul(self):
        """4. Vérifie le rejet d'un montant négatif ou égal à zéro."""
        paiement_negatif = Paiement(
            commande=self.commande,
            montant=Decimal('-500.00'),
            methode=Paiement.METHODE_WAVE
        )
        with self.assertRaises(ValidationError):
            paiement_negatif.full_clean()

        paiement_zero = Paiement(
            commande=self.commande,
            montant=Decimal('0.00'),
            methode=Paiement.METHODE_WAVE
        )
        with self.assertRaises(ValidationError):
            paiement_zero.full_clean()

    def test_5_methodes_wave_et_orange_money(self):
        """5. Vérifie le support des méthodes Wave et Orange Money."""
        p_wave = Paiement.objects.create(
            commande=self.commande,
            montant=Decimal('5500.00'),
            methode=Paiement.METHODE_WAVE
        )
        p_om = Paiement.objects.create(
            commande=self.commande,
            montant=Decimal('5500.00'),
            methode=Paiement.METHODE_ORANGE_MONEY
        )
        self.assertEqual(p_wave.methode, 'WAVE')
        self.assertEqual(p_om.methode, 'ORANGE_MONEY')

    def test_6_statuts_cycle_de_vie_paiement(self):
        """6. Vérifie les statuts du cycle de vie du paiement."""
        paiement = Paiement.objects.create(
            commande=self.commande,
            montant=Decimal('5500.00'),
            methode=Paiement.METHODE_WAVE
        )
        self.assertEqual(paiement.statut, Paiement.STATUT_EN_ATTENTE)

        # Passer à initié
        paiement.statut = Paiement.STATUT_INITIE
        paiement.save()
        self.assertEqual(paiement.statut, 'INITIE')

        # Marquer comme payé
        paiement.marquer_comme_paye(transaction_externe="WAVE_TX_998877")
        self.assertEqual(paiement.statut, 'PAYE')
        self.assertIsNotNone(paiement.date_paiement)
        self.assertEqual(paiement.transaction_externe, "WAVE_TX_998877")

    def test_7_association_correcte_commande(self):
        """7. Vérifie l'association entre la commande et ses paiements."""
        p1 = Paiement.objects.create(
            commande=self.commande,
            montant=Decimal('5500.00'),
            methode=Paiement.METHODE_WAVE
        )
        self.assertIn(p1, self.commande.paiements.all())
        self.assertEqual(p1.commande, self.commande)

    def test_8_unicite_reference_dupliquee(self):
        """8. Vérifie le rejet d'une référence de paiement dupliquée."""
        Paiement.objects.create(
            commande=self.commande,
            reference="PAY-TEST-UNIQUE-123",
            montant=Decimal('5500.00'),
            methode=Paiement.METHODE_WAVE
        )
        with self.assertRaises(IntegrityError):
            Paiement.objects.create(
                commande=self.commande,
                reference="PAY-TEST-UNIQUE-123",
                montant=Decimal('5500.00'),
                methode=Paiement.METHODE_ORANGE_MONEY
            )

    def test_9_conservation_informations_historiques_facture(self):
        """9. Vérifie la conservation des snapshots historiques dans la facture."""
        sous_cmd = SousCommande.objects.create(
            commande=self.commande,
            etablissement=self.etablissement,
            sous_total=Decimal('4500.00'),
            frais_livraison=Decimal('1000.00'),
            total=Decimal('5500.00')
        )
        LigneCommande.objects.create(
            sous_commande=sous_cmd,
            produit=self.produit,
            nom_produit_snapshot="Thiéboudienne Rouge",
            quantite=1,
            prix_unitaire=Decimal('4500.00'),
            total_ligne=Decimal('4500.00')
        )

        paiement = PaymentService.initier_paiement(self.commande, Paiement.METHODE_WAVE)
        paiement.marquer_comme_paye(transaction_externe="WAVE_123")

        facture = PaymentService.generer_facture(self.commande, paiement)

        self.assertEqual(facture.nom_client_snapshot, "Moussa Diop")
        self.assertEqual(facture.telephone_client_snapshot, "+221770001122")
        self.assertEqual(facture.adresse_livraison_snapshot, "Point E, Dakar")
        self.assertEqual(Decimal(str(facture.montant_total)), Decimal('5500.00'))
        self.assertTrue(facture.est_payee)

        # Modifier la commande originale ne doit pas modifier les snapshots de la facture
        self.commande.nom_destinataire = "Nouveau Destinataire"
        self.commande.save()

        facture.refresh_from_db()
        self.assertEqual(facture.nom_client_snapshot, "Moussa Diop")

    def test_10_creation_facture_liee(self):
        """10. Vérifie la création d'une Facture avec référence unique."""
        facture = Facture.objects.create(
            commande=self.commande,
            nom_client_snapshot="Moussa Diop",
            telephone_client_snapshot="+221770001122",
            adresse_livraison_snapshot="Point E, Dakar",
            montant_ht=Decimal('4500.00'),
            frais_livraison=Decimal('1000.00'),
            montant_total=Decimal('5500.00'),
            est_payee=False
        )
        self.assertIsNotNone(facture.id)
        self.assertTrue(facture.numero_facture.startswith('FAC-'))
        self.assertEqual(facture.commande, self.commande)
