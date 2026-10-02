from datetime import timedelta
from django.utils import timezone
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.users.models import Utilisateur, Role, ProfilLivreur
from apps.catalog.models import Etablissement
from apps.orders.models import Commande, SousCommande
from apps.deliveries.models import Livraison
from apps.deliveries.services import DeliveryService
from apps.deliveries.serializers import LivraisonSerializer


class ProgressiveAssignmentTestCase(APITestCase):

    def setUp(self):
        self.role_client, _ = Role.objects.get_or_create(nom=Role.CLIENT)
        self.role_livreur, _ = Role.objects.get_or_create(nom=Role.LIVREUR)

        # Client
        self.user_client = Utilisateur.objects.create_user(
            email='client@ayyou.com', password='password123', numero_telephone='+221770000001',
            nom='Client', prenom='Test'
        )
        self.user_client.roles_attribues.create(role=self.role_client)

        # Restaurant at Dakar Plateau (14.6655, -17.4334)
        self.etablissement = Etablissement.objects.create(
            nom='Restaurant Dakar Plateau',
            type_etablissement=Etablissement.TYPE_RESTAURANT,
            est_verifie=True,
            latitude=14.6655,
            longitude=-17.4334
        )

        # Drivers with positions at different distances from Restaurant
        # Driver 1: Very close (14.6660, -17.4330 ~ 0.1km)
        self.driver_1 = self._creer_livreur('driver1@ayyou.com', '+221770000010', 'D1', 14.6660, -17.4330)
        # Driver 2: Close (14.6700, -17.4300 ~ 0.6km)
        self.driver_2 = self._creer_livreur('driver2@ayyou.com', '+221770000020', 'D2', 14.6700, -17.4300)
        # Driver 3: Medium (14.6900, -17.4200 ~ 3.0km)
        self.driver_3 = self._creer_livreur('driver3@ayyou.com', '+221770000030', 'D3', 14.6900, -17.4200)
        # Driver 4: Far (14.7200, -17.4000 ~ 7.5km)
        self.driver_4 = self._creer_livreur('driver4@ayyou.com', '+221770000040', 'D4', 14.7200, -17.4000)
        # Driver 5: Very far (14.7500, -17.3800 ~ 12km)
        self.driver_5 = self._creer_livreur('driver5@ayyou.com', '+221770000050', 'D5', 14.7500, -17.3800)

    def _creer_livreur(self, email, tel, name, lat, lng):
        user = Utilisateur.objects.create_user(
            email=email, password='password123', numero_telephone=tel, nom='Livreur', prenom=name
        )
        user.roles_attribues.create(role=self.role_livreur)
        profil = ProfilLivreur.objects.create(
            utilisateur=user,
            statut_verification=ProfilLivreur.STATUT_VALIDE,
            est_disponible=True,
            latitude_actuelle=lat,
            longitude_actuelle=lng
        )
        return profil

    def _creer_livraison(self, numero='CMD-PROG-001'):
        commande = Commande.objects.create(
            numero_commande=numero,
            utilisateur=self.user_client,
            frais_livraison=1500,
            total=10000,
            statut=Commande.STATUT_PAYEE,
            nom_destinataire='Client Destinataire',
            telephone_destinataire='+221770000000',
            adresse_livraison='Fann, Dakar'
        )
        SousCommande.objects.create(
            commande=commande,
            etablissement=self.etablissement,
            statut=Commande.STATUT_PRETE
        )
        return DeliveryService.creer_livraison(commande)

    def test_1_phase_1_selection_livreur_le_plus_proche(self):
        """TEST 1 — La Phase 1 sélectionne le livreur le plus proche (Driver 1) pour 90s"""
        livraison = self._creer_livraison('CMD-P1-001')
        livraison.refresh_from_db()

        self.assertEqual(livraison.phase_attribution, 1)
        self.assertEqual(livraison.livreur, self.driver_1)
        self.assertEqual(livraison.statut, Livraison.STATUT_AFFECTEE)
        self.assertIn(self.driver_1.id, livraison.propositions_livreurs.get('phase_1', []))

    def test_2_transition_phase_1_vers_phase_2_apres_90s(self):
        """TEST 2 — Expiration 90s de la Phase 1 -> Transition auto vers Phase 2 avec 3 livreurs suivants (Driver 2, 3, 4)"""
        livraison = self._creer_livraison('CMD-P1-002')

        # Simuler écoulement de 95 secondes
        Livraison.objects.filter(pk=livraison.id).update(date_attribution=timezone.now() - timedelta(seconds=95))

        count = DeliveryService.expire_expired_deliveries()
        self.assertEqual(count, 1)

        livraison.refresh_from_db()
        self.assertEqual(livraison.phase_attribution, 2)
        self.assertIsNone(livraison.livreur)
        p2_ids = livraison.propositions_livreurs.get('phase_2', [])
        self.assertEqual(len(p2_ids), 3)
        self.assertIn(self.driver_2.id, p2_ids)
        self.assertIn(self.driver_3.id, p2_ids)
        self.assertIn(self.driver_4.id, p2_ids)
        self.assertNotIn(self.driver_1.id, p2_ids)
        self.assertIn(self.driver_1.id, livraison.propositions_livreurs.get('expires', []))

    def test_3_acceptation_phase_2_premier_arrive(self):
        """TEST 3 — En Phase 2, le premier des 3 livreurs à accepter gagne la livraison, le second reçoit une erreur"""
        livraison = self._creer_livraison('CMD-P2-003')

        # Forcer le passage en Phase 2
        Livraison.objects.filter(pk=livraison.id).update(date_attribution=timezone.now() - timedelta(seconds=95))
        DeliveryService.expire_expired_deliveries()
        livraison.refresh_from_db()

        # Driver 3 accepte la course Phase 2
        liv_acc = DeliveryService.accepter_mission(livraison.id, self.driver_3)
        self.assertEqual(liv_acc.livreur, self.driver_3)
        self.assertEqual(liv_acc.statut, Livraison.STATUT_ACCEPTEE)

        # Driver 2 tente ensuite d'accepter la même course
        with self.assertRaises(Exception) as cm:
            DeliveryService.accepter_mission(livraison.id, self.driver_2)

        self.assertIn("Course déjà attribuée", str(cm.exception))

    def test_4_refus_phase_1_declenche_immediatement_phase_2(self):
        """TEST 4 — Si Driver 1 décline la mission Phase 1, bascule immédiate en Phase 2"""
        livraison = self._creer_livraison('CMD-P1-004')
        livraison.refresh_from_db()

        # Driver 1 décline
        DeliveryService.refuser_mission(livraison.id, self.driver_1)

        livraison.refresh_from_db()
        self.assertEqual(livraison.phase_attribution, 2)
        self.assertIn(self.driver_1.id, livraison.propositions_livreurs.get('refuses', []))
        p2_ids = livraison.propositions_livreurs.get('phase_2', [])
        self.assertIn(self.driver_2.id, p2_ids)

    def test_5_livreur_ayant_refuse_ou_expire_ne_peut_plus_accepter(self):
        """TEST 5 — Un livreur qui a décliné ou laissé expirer la livraison ne peut plus l'accepter"""
        livraison = self._creer_livraison('CMD-P1-005')
        DeliveryService.refuser_mission(livraison.id, self.driver_1)

        # Driver 1 tente d'accepter en Phase 2
        with self.assertRaises(Exception) as cm:
            DeliveryService.accepter_mission(livraison.id, self.driver_1)

        self.assertIn("déclinée ou laissée expirer", str(cm.exception))

    def test_6_visibilite_api_available_selon_phase(self):
        """TEST 6 — Filtrage de l'endpoint available par phase d'attribution"""
        livraison = self._creer_livraison('CMD-P1-006')

        # Phase 1 : Seul Driver 1 voit la mission
        self.client.force_authenticate(user=self.driver_1.utilisateur)
        res1 = self.client.get(reverse('deliveries:livraison-available'))
        self.assertEqual(res1.status_code, status.HTTP_200_OK)
        self.assertIn(livraison.id, [item['id'] for item in res1.data])

        # Driver 2 ne doit PAS voir la mission en Phase 1
        self.client.force_authenticate(user=self.driver_2.utilisateur)
        res2 = self.client.get(reverse('deliveries:livraison-available'))
        self.assertEqual(res2.status_code, status.HTTP_200_OK)
        self.assertNotIn(livraison.id, [item['id'] for item in res2.data])

        # Passage en Phase 2
        Livraison.objects.filter(pk=livraison.id).update(date_attribution=timezone.now() - timedelta(seconds=95))
        DeliveryService.expire_expired_deliveries()

        # Driver 2 voit maintenant la mission en Phase 2
        self.client.force_authenticate(user=self.driver_2.utilisateur)
        res2_p2 = self.client.get(reverse('deliveries:livraison-available'))
        self.assertIn(livraison.id, [item['id'] for item in res2_p2.data])

        # Driver 1 (qui a laissé expirer Phase 1) ne la voit plus
        self.client.force_authenticate(user=self.driver_1.utilisateur)
        res1_p2 = self.client.get(reverse('deliveries:livraison-available'))
        self.assertNotIn(livraison.id, [item['id'] for item in res1_p2.data])
