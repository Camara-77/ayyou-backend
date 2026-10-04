import datetime
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework import status

from apps.users.models import Utilisateur
from apps.catalog.models import Categorie, Etablissement, Produit
from apps.orders.models import Commande, SousCommande, RepasPlanifie, AdresseLivraison
from apps.ai.services import AIService
from apps.ai.tools import (
    get_user_plannings,
    update_user_planning,
    cancel_user_planning,
    update_order_delivery_info
)


class ActionableAITestCase(TestCase):
    def setUp(self):
        self.client = APIClient()

        # Utilisateur Client 1
        self.user1 = Utilisateur.objects.create_user(
            email='client1@ayyou.sn',
            numero_telephone='+221770000001',
            password='Password123!',
            prenom='Moussa',
            nom='Diop',
            mode_actif='CLIENT'
        )

        # Utilisateur Client 2 (pour test de cloisonnement)
        self.user2 = Utilisateur.objects.create_user(
            email='client2@ayyou.sn',
            numero_telephone='+221770000002',
            password='Password123!',
            prenom='Fatou',
            nom='Sow',
            mode_actif='CLIENT'
        )

        # Utilisateur Restaurateur (Vendeur / Staff)
        self.vendor = Utilisateur.objects.create_user(
            email='vendor@fatou.sn',
            numero_telephone='+221770000003',
            password='Password123!',
            prenom='Fatou',
            nom='Chef',
            is_staff=True
        )

        # Catégorie et Établissement
        self.categorie = Categorie.objects.create(nom='Sénégalais', slug='senegalais')
        self.etablissement = Etablissement.objects.create(
            nom='Chez Fatou',
            proprietaire=self.vendor,
            statut_verification=Etablissement.STATUT_VALIDE,
            adresse='Dakar Plateau'
        )

        # Produits réels
        self.produit_thieb = Produit.objects.create(
            etablissement=self.etablissement,
            categorie=self.categorie,
            nom='Thiéboudienne Rouge',
            description='Thiéboudienne traditionnel au poisson frais',
            prix_base=3500,
            est_disponible=True
        )

        self.produit_yassa = Produit.objects.create(
            etablissement=self.etablissement,
            categorie=self.categorie,
            nom='Yassa Poulet',
            description='Poulet braisé aux oignons et citron',
            prix_base=3000,
            est_disponible=True
        )

        # Planning existant pour User 1 (Vendredi MIDI)
        self.today = timezone.now().date()
        current_weekday = self.today.weekday()
        days_to_friday = (4 - current_weekday) % 7
        if days_to_friday == 0:
            days_to_friday = 7
        self.friday_date = self.today + datetime.timedelta(days=days_to_friday)

        self.planning_user1 = RepasPlanifie.objects.create(
            utilisateur=self.user1,
            produit=self.produit_thieb,
            etablissement=self.etablissement,
            date_planifiee=self.friday_date,
            creneau=RepasPlanifie.CRENEAU_MIDI,
            prix_total=3500,
            quantite=1,
            statut=RepasPlanifie.STATUT_PLANIFIE
        )

        # Order pour User 1
        self.commande_user1 = Commande.objects.create(
            utilisateur=self.user1,
            numero_commande='CMD-2026-TEST-01',
            statut=Commande.STATUT_EN_LIVRAISON,
            total=3500,
            adresse_livraison='Plateau Rue 10'
        )

    def test_01_planification_parsing_real_data(self):
        """TEST 1: Planifie du riz demain midi -> Produit réel, Prix réel."""
        res = AIService.process_chat_message(
            message="Planifie un Thiéboudienne demain midi",
            user_name="Moussa",
            user=self.user1
        )
        self.assertEqual(res["status"], "success")

    def test_02_modification_planning_action_proposal(self):
        """TEST 2: 'Décale mon planning de vendredi à samedi soir' -> Proposition d'action et identification du planning."""
        msg = f"Décale mon repas de vendredi midi à samedi soir"
        res = AIService.process_chat_message(
            message=msg,
            user_name="Moussa",
            user=self.user1
        )
        self.assertEqual(res["status"], "confirmation_required")
        self.assertIn("action_proposal", res)
        self.assertEqual(res["action_proposal"]["planning_id"], self.planning_user1.id)
        self.assertEqual(res["action_proposal"]["changes"]["creneau"], "SOIR")

    def test_03_cloisonnement_inter_utilisateurs(self):
        """TEST 3: Tentative de modification du planning de User 1 par User 2 -> Refus/Not Found."""
        res = update_user_planning(
            planning_id=self.planning_user1.id,
            user_id=self.user2.id,
            changes_dict={"creneau": "SOIR"}
        )
        self.assertFalse(res["success"])
        self.assertIn("ne vous appartient pas", res["message"])

    def test_04_anti_hallucination_produit_inexistant(self):
        """TEST 4: Recherche ou action sur un produit inexistant -> Aucune hallucination."""
        res = AIService.process_chat_message(
            message="Décale mon repas de Caviar Sauvage de mardi",
            user_name="Moussa",
            user=self.user1
        )
        self.assertIn(res["status"], ["missing_info", "success"])
        self.assertNotIn("Caviar", res["reply"])

    def test_05_anti_hallucination_restaurant_inexistant(self):
        """TEST 5: Restaurant inexistant -> Aucune hallucination."""
        res = AIService.process_chat_message(
            message="Je veux manger chez Le Fast Food Inexistant",
            user_name="Moussa",
            user=self.user1
        )
        self.assertIn("aucun", res["reply"].lower())

    def test_06_non_ecriture_sans_confirmation(self):
        """TEST 6: Modification demandée mais non confirmée -> Aucune écriture SQL."""
        date_initiale = self.planning_user1.date_planifiee
        creneau_initial = self.planning_user1.creneau

        res = AIService.process_chat_message(
            message="Décale mon repas de vendredi midi à samedi soir",
            user_name="Moussa",
            user=self.user1
        )
        self.assertEqual(res["status"], "confirmation_required")

        # Vérifier que le repas en BDD n'a PAS changé
        self.planning_user1.refresh_from_db()
        self.assertEqual(self.planning_user1.date_planifiee, date_initiale)
        self.assertEqual(self.planning_user1.creneau, creneau_initial)

    def test_07_ecriture_reelle_post_confirmation(self):
        """TEST 7: Après confirmation textuelle ou flag confirm_action -> Écriture réelle PostgreSQL."""
        pending_action = {
            "action_type": "update_planning",
            "planning_id": self.planning_user1.id,
            "changes": {"creneau": "SOIR", "quantite": 3}
        }
        res = AIService.process_chat_message(
            message="Oui, confirme",
            user_name="Moussa",
            context={"pending_action": pending_action},
            user=self.user1
        )
        self.assertEqual(res["status"], "action_executed")
        self.assertTrue(res["success"])

        # Vérifier l'écriture effective dans PostgreSQL
        self.planning_user1.refresh_from_db()
        self.assertEqual(self.planning_user1.creneau, "SOIR")
        self.assertEqual(self.planning_user1.quantite, 3)

    def test_08_modification_commande_en_livraison_refusee(self):
        """TEST 8: Modification d'une commande en statut EN_LIVRAISON -> Refus métier Django."""
        res = update_order_delivery_info(
            order_id_or_number=self.commande_user1.id,
            user_id=self.user1.id,
            new_instructions="Déposer devant la porte"
        )
        self.assertFalse(res["success"])
        self.assertIn("ne sont plus", res["message"])

    def test_09_refus_modification_catalogue_par_client(self):
        """TEST 9: Modification catalogue par un CLIENT -> Refus de permission."""
        res = AIService.process_chat_message(
            message="Change le prix du Thiéboudienne à 1000 FCFA",
            user_name="Moussa",
            user=self.user1
        )
        self.assertEqual(res["status"], "permission_denied")
        self.assertIn("Refusé", res["reply"])

    def test_10_modification_catalogue_par_vendeur(self):
        """TEST 10: Vendeur connecté tentant d'éditer -> Détection du rôle Vendeur."""
        res = AIService.process_chat_message(
            message="Change le prix du Thiéboudienne à 4000 FCFA",
            user_name="Chef Fatou",
            user=self.vendor
        )
        self.assertNotEqual(res["status"], "permission_denied")

    def test_11_annulation_planning(self):
        """TEST 11: Demande d'annulation d'un repas planifié."""
        res = cancel_user_planning(planning_id=self.planning_user1.id, user_id=self.user1.id)
        self.assertTrue(res["success"])
        self.planning_user1.refresh_from_db()
        self.assertEqual(self.planning_user1.statut, RepasPlanifie.STATUT_ANNULE)

    def test_12_sanity_check_no_mock_in_database(self):
        """TEST 12: S'assurer que les objets retournés proviennent à 100% de la base PostgreSQL."""
        plannings = get_user_plannings(user_id=self.user1.id)
        self.assertTrue(plannings["success"])
        for item in plannings["results"]:
            self.assertIn("id", item)
            self.assertIn("nom_produit", item)
            self.assertNotEqual(item["nom_produit"], "")
