from django.test import TestCase
from django.core.exceptions import ValidationError
from django.db.utils import IntegrityError
from decimal import Decimal

from apps.users.models import Utilisateur, ProfilClient
from apps.catalog.models import Categorie, Etablissement, Produit, VarianteProduit, OptionProduit
from apps.orders.models import (
    Panier, PanierItem, Commande, SousCommande,
    LigneCommande, LigneCommandeVariante, LigneCommandeOption, AdresseLivraison
)


class OrdersModelsTest(TestCase):

    def setUp(self):
        # Create test Client User
        self.user_client = Utilisateur.objects.create_user(
            email='moussa.client@ayyou.sn',
            numero_telephone='+221770000001',
            password='Password123!',
            prenom='Moussa',
            nom='Diop'
        )
        self.profil_client = ProfilClient.objects.create(
            utilisateur=self.user_client,
            adresse_principale='Plateau, Dakar',
            latitude=Decimal('14.6928000'),
            longitude=Decimal('-17.4467000')
        )

        # Create test Vendor User
        self.user_vendor = Utilisateur.objects.create_user(
            email='loutcha.vendor@ayyou.sn',
            numero_telephone='+221770000002',
            password='Password123!',
            prenom='Awa',
            nom='Sow'
        )

        # Create test Category
        self.category = Categorie.objects.create(
            slug='plats-nationaux',
            nom='Plats Nationaux',
            ordre=1
        )

        # Create Establishment 1 (Restaurant A)
        self.etablissement_a = Etablissement.objects.create(
            nom='Chez Loutcha',
            type_etablissement=Etablissement.TYPE_RESTAURANT,
            proprietaire=self.user_vendor,
            adresse='Plateau, Dakar',
            latitude=Decimal('14.6928000'),
            longitude=Decimal('-17.4467000')
        )

        # Create Establishment 2 (Vendor B)
        self.etablissement_b = Etablissement.objects.create(
            nom='Pâtisserie & Brunch Dakar',
            type_etablissement=Etablissement.TYPE_VENDEUR,
            proprietaire=self.user_vendor,
            adresse='Ngor, Dakar',
            latitude=Decimal('14.7500000'),
            longitude=Decimal('-17.5100000')
        )

        # Create Product 1 for Restaurant A
        self.produit_a = Produit.objects.create(
            etablissement=self.etablissement_a,
            categorie=self.category,
            nom='Thiéboudienne Rouge',
            prix_base=Decimal('4500.00'),
            image_url='https://example.com/thiebou.jpg',
            stock_disponible=100,
            stock_ayyou_reserve=50
        )

        # Create Variant for Product 1
        self.variante_a = VarianteProduit.objects.create(
            produit=self.produit_a,
            titre='Portion Gourmande XL',
            surcout_prix=Decimal('1500.00'),
            est_requis=False
        )

        # Create Option for Product 1
        self.option_sauce = OptionProduit.objects.create(
            produit=self.produit_a,
            type_option=OptionProduit.TYPE_SAUCE,
            titre='Sauce Beugueul',
            surcout_prix=Decimal('0.00'),
            est_inclus=True
        )
        self.option_supp = OptionProduit.objects.create(
            produit=self.produit_a,
            type_option=OptionProduit.TYPE_SUPPLEMENT,
            titre='Croûte de riz (Xoogn)',
            surcout_prix=Decimal('500.00')
        )

        # Create Product 2 for Vendor B
        self.produit_b = Produit.objects.create(
            etablissement=self.etablissement_b,
            categorie=self.category,
            nom='Jus de Bissap Maison',
            prix_base=Decimal('1000.00'),
            image_url='https://example.com/bissap.jpg',
            stock_disponible=200,
            stock_ayyou_reserve=100
        )

    # ------------------------------------------------------------------
    # TESTS PANIER
    # ------------------------------------------------------------------

    def test_01_creation_panier_et_unicite_actif(self):
        """Vérifie la création du panier et l'unicité d'un seul panier actif par client."""
        panier1 = Panier.objects.create(utilisateur=self.user_client, actif=True)
        self.assertTrue(panier1.actif)
        self.assertEqual(panier1.utilisateur, self.user_client)

        # Tenter de créer un deuxième panier actif pour le même utilisateur doit déclencher une erreur d'unicité
        with self.assertRaises(IntegrityError):
            Panier.objects.create(utilisateur=self.user_client, actif=True)

    def test_02_desactivation_et_nouveau_panier(self):
        """Vérifie qu'un client peut créer un nouveau panier actif si le précédent est rendu inactif."""
        panier1 = Panier.objects.create(utilisateur=self.user_client, actif=True)
        panier1.actif = False
        panier1.save()

        panier2 = Panier.objects.create(utilisateur=self.user_client, actif=True)
        self.assertTrue(panier2.actif)
        self.assertNotEqual(panier1.id, panier2.id)

    def test_03_panier_item_multi_etablissements_et_calculs(self):
        """Vérifie qu'un panier supporte des produits de plusieurs établissements avec calculs exacts."""
        panier = Panier.objects.create(utilisateur=self.user_client, actif=True)

        # Item 1: Thiéboudienne (4500) + Variante XL (+1500) + Xoogn (+500) = 6500 x 2 = 13000
        item1 = PanierItem.objects.create(
            panier=panier,
            produit=self.produit_a,
            quantite=2,
            prix_unitaire=self.produit_a.prix_base,
            variante=self.variante_a
        )
        item1.options.add(self.option_sauce, self.option_supp)

        # Item 2: Jus de Bissap (1000) x 3 = 3000
        item2 = PanierItem.objects.create(
            panier=panier,
            produit=self.produit_b,
            quantite=3,
            prix_unitaire=self.produit_b.prix_base
        )

        self.assertEqual(item1.calculer_prix_total_unitaire(), Decimal('6500.00'))
        self.assertEqual(item1.calculer_total_ligne(), Decimal('13000.00'))
        self.assertEqual(item2.calculer_total_ligne(), Decimal('3000.00'))
        self.assertEqual(panier.calculer_total(), Decimal('16000.00'))

    def test_04_panier_item_quantite_invalide(self):
        """Vérifie le rejet d'une quantité < 1 sur un article de panier."""
        panier = Panier.objects.create(utilisateur=self.user_client, actif=True)
        item = PanierItem(panier=panier, produit=self.produit_a, quantite=0, prix_unitaire=Decimal('4500.00'))
        with self.assertRaises(ValidationError):
            item.clean()

    # ------------------------------------------------------------------
    # TESTS COMMANDE & MULTI-ÉTABLISSEMENTS
    # ------------------------------------------------------------------

    def test_05_creation_commande_et_numero_unique(self):
        """Vérifie la création d'une commande avec numéro auto-généré unique et statut initial."""
        commande = Commande.objects.create(
            utilisateur=self.user_client,
            statut=Commande.STATUT_EN_ATTENTE_PAIEMENT,
            sous_total=Decimal('16000.00'),
            frais_livraison=Decimal('1500.00'),
            total=Decimal('17500.00'),
            adresse_livraison='Rue 10 x Carnot, Dakar',
            latitude_livraison=Decimal('14.6900000'),
            longitude_livraison=Decimal('-17.4400000'),
            instructions_livraison='Portail bleu',
            nom_destinataire='Moussa Diop',
            telephone_destinataire='+221770000001'
        )

        self.assertIsNotNone(commande.numero_commande)
        self.assertTrue(commande.numero_commande.startswith('AYY-'))
        self.assertEqual(commande.statut, Commande.STATUT_EN_ATTENTE_PAIEMENT)
        self.assertEqual(commande.total, Decimal('17500.00'))

    def test_06_decoupage_multi_etablissements_sous_commandes(self):
        """Vérifie qu'une commande peut être découpée en plusieurs sous-commandes par établissement."""
        commande = Commande.objects.create(
            utilisateur=self.user_client,
            adresse_livraison='Plateau, Dakar',
            nom_destinataire='Moussa Diop',
            telephone_destinataire='+221770000001'
        )

        # Sous-Commande 1: Restaurant A (Chez Loutcha)
        sc_a = SousCommande.objects.create(
            commande=commande,
            etablissement=self.etablissement_a,
            sous_total=Decimal('13000.00'),
            frais_livraison=Decimal('1000.00'),
            total=Decimal('14000.00')
        )
        LigneCommande.objects.create(
            sous_commande=sc_a,
            produit=self.produit_a,
            nom_produit_snapshot='Thiéboudienne Rouge',
            quantite=2,
            prix_unitaire=Decimal('6500.00'),
            total_ligne=Decimal('13000.00')
        )

        # Sous-Commande 2: Vendeur B (Pâtisserie & Brunch)
        sc_b = SousCommande.objects.create(
            commande=commande,
            etablissement=self.etablissement_b,
            sous_total=Decimal('3000.00'),
            frais_livraison=Decimal('500.00'),
            total=Decimal('3500.00')
        )
        LigneCommande.objects.create(
            sous_commande=sc_b,
            produit=self.produit_b,
            nom_produit_snapshot='Jus de Bissap Maison',
            quantite=3,
            prix_unitaire=Decimal('1000.00'),
            total_ligne=Decimal('3000.00')
        )

        self.assertEqual(commande.sous_commandes.count(), 2)
        commande.recalculer_totaux()
        self.assertEqual(commande.sous_total, Decimal('16000.00'))
        self.assertEqual(commande.frais_livraison, Decimal('1500.00'))
        self.assertEqual(commande.total, Decimal('17500.00'))

    # ------------------------------------------------------------------
    # TESTS SNAPSHOTS HISTORIQUES & IMMUTABILITÉ
    # ------------------------------------------------------------------

    def test_07_immutabilite_historique_des_snapshots(self):
        """Vérifie que la modification ultérieure du catalogue n'altère pas les snapshots d'une ancienne commande."""
        commande = Commande.objects.create(
            utilisateur=self.user_client,
            adresse_livraison='Plateau, Dakar',
            nom_destinataire='Moussa Diop',
            telephone_destinataire='+221770000001'
        )
        sc = SousCommande.objects.create(
            commande=commande,
            etablissement=self.etablissement_a,
            sous_total=Decimal('6500.00'),
            total=Decimal('6500.00')
        )
        ligne = LigneCommande.objects.create(
            sous_commande=sc,
            produit=self.produit_a,
            nom_produit_snapshot=self.produit_a.nom,
            quantite=1,
            prix_unitaire=Decimal('6500.00'),
            total_ligne=Decimal('6500.00')
        )
        LigneCommandeVariante.objects.create(
            ligne_commande=ligne,
            variante=self.variante_a,
            nom_variante_snapshot=self.variante_a.titre,
            prix_supplementaire_snapshot=self.variante_a.surcout_prix
        )
        LigneCommandeOption.objects.create(
            ligne_commande=ligne,
            option=self.option_supp,
            nom_option_snapshot=self.option_supp.titre,
            type_option_snapshot=self.option_supp.type_option,
            prix_supplementaire_snapshot=self.option_supp.surcout_prix
        )

        # Modifier le produit dans le catalogue (changement de nom et de prix)
        self.produit_a.nom = 'Thiéboudienne Luxe Modifiée'
        self.produit_a.prix_base = Decimal('99000.00')
        self.produit_a.save()

        # Modifier la variante dans le catalogue
        self.variante_a.titre = 'Nouvelle variante'
        self.variante_a.save()

        # Vérifier que le snapshot de la ligne de commande reste intact
        ligne.refresh_from_db()
        self.assertEqual(ligne.nom_produit_snapshot, 'Thiéboudienne Rouge')
        self.assertEqual(ligne.prix_unitaire, Decimal('6500.00'))
        self.assertEqual(ligne.variante_snapshot.nom_variante_snapshot, 'Portion Gourmande XL')
        self.assertEqual(ligne.options_snapshot.first().nom_option_snapshot, 'Croûte de riz (Xoogn)')

    # ------------------------------------------------------------------
    # TESTS SÉCURITÉ & ADRESSE DE LIVRAISON
    # ------------------------------------------------------------------

    def test_08_validation_montants_negatifs(self):
        """Vérifie que les montants négatifs déclenchent une ValidationError."""
        commande = Commande(
            utilisateur=self.user_client,
            sous_total=Decimal('-500.00'),
            total=Decimal('-500.00'),
            adresse_livraison='Dakar',
            nom_destinataire='Moussa',
            telephone_destinataire='+221770000001'
        )
        with self.assertRaises(ValidationError):
            commande.clean()

    def test_09_carnet_adresses_livraison(self):
        """Vérifie la création et la gestion du carnet d'adresses client."""
        adresse1 = AdresseLivraison.objects.create(
            utilisateur=self.user_client,
            titre='Maison',
            adresse='Villa 14, Point E, Dakar',
            latitude=Decimal('14.7000000'),
            longitude=Decimal('-17.4500000'),
            est_defaut=True
        )
        adresse2 = AdresseLivraison.objects.create(
            utilisateur=self.user_client,
            titre='Bureau',
            adresse='Immeuble Kébé, Plateau, Dakar',
            est_defaut=False
        )

        self.assertEqual(self.user_client.adresses_livraison.count(), 2)
        self.assertEqual(self.user_client.adresses_livraison.first(), adresse1)
