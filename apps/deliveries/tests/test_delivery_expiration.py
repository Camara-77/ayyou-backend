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


class DeliveryExpirationTestCase(APITestCase):

    def setUp(self):
        # Création des rôles
        self.role_client, _ = Role.objects.get_or_create(nom=Role.CLIENT)
        self.role_livreur, _ = Role.objects.get_or_create(nom=Role.LIVREUR)

        # Création du client
        self.user_client = Utilisateur.objects.create_user(
            email='client@ayyou.com',
            password='password123',
            numero_telephone='+221770000001',
            nom='Client',
            prenom='Test'
        )
        self.user_client.roles_attribues.create(role=self.role_client)

        # Livreur A
        self.user_driver_a = Utilisateur.objects.create_user(
            email='driver.a@ayyou.com',
            password='password123',
            numero_telephone='+221770000002',
            nom='Livreur',
            prenom='A'
        )
        self.user_driver_a.roles_attribues.create(role=self.role_livreur)
        self.driver_a = ProfilLivreur.objects.create(
            utilisateur=self.user_driver_a,
            statut_verification=ProfilLivreur.STATUT_VALIDE,
            est_disponible=True
        )

        # Livreur B
        self.user_driver_b = Utilisateur.objects.create_user(
            email='driver.b@ayyou.com',
            password='password123',
            numero_telephone='+221770000003',
            nom='Livreur',
            prenom='B'
        )
        self.user_driver_b.roles_attribues.create(role=self.role_livreur)
        self.driver_b = ProfilLivreur.objects.create(
            utilisateur=self.user_driver_b,
            statut_verification=ProfilLivreur.STATUT_VALIDE,
            est_disponible=True
        )

        # Création d'un établissement marchand
        self.etablissement = Etablissement.objects.create(
            nom='Restaurant Teranga',
            type_etablissement=Etablissement.TYPE_RESTAURANT,
            est_verifie=True
        )

    def _creer_commande_et_livraison(self, numero='CMD-EXP-001'):
        commande = Commande.objects.create(
            numero_commande=numero,
            utilisateur=self.user_client,
            frais_livraison=1500,
            total=10000,
            statut=Commande.STATUT_PAYEE,
            nom_destinataire='Destinataire Test',
            telephone_destinataire='+221770000000',
            adresse_livraison='Plateau, Dakar'
        )
        SousCommande.objects.create(
            commande=commande,
            etablissement=self.etablissement,
            statut=Commande.STATUT_PRETE
        )
        livraison = DeliveryService.creer_livraison(commande)
        return livraison

    def test_1_attribution(self):
        """TEST 1 — Verification attribution initiale"""
        livraison = self._creer_commande_et_livraison('CMD-TEST-1')
        DeliveryService.attribuer_livraison(livraison.id, self.driver_a)

        livraison.refresh_from_db()
        self.assertEqual(livraison.livreur, self.driver_a)
        self.assertIsNotNone(livraison.date_attribution)
        
        serializer = LivraisonSerializer(livraison)
        self.assertIsNotNone(serializer.data['acceptance_deadline'])

    def test_2_acceptation_avant_expiration(self):
        """TEST 2 — Acceptation valide dans les 2 minutes"""
        livraison = self._creer_commande_et_livraison('CMD-TEST-2')
        DeliveryService.attribuer_livraison(livraison.id, self.driver_a)

        # Driver A accepte immédiatement
        DeliveryService.accepter_mission(livraison.id, self.driver_a)

        livraison.refresh_from_db()
        self.assertEqual(livraison.statut, Livraison.STATUT_ACCEPTEE)
        self.assertEqual(livraison.livreur, self.driver_a)

    def test_3_expiration_tache(self):
        """TEST 3 — Expiration automatique par la méthode/tâche"""
        livraison = self._creer_commande_et_livraison('CMD-TEST-3')
        DeliveryService.attribuer_livraison(livraison.id, self.driver_a)

        # Simulation de 3 minutes dans le passé (expiration dépassée)
        il_y_a_3_min = timezone.now() - timedelta(minutes=3)
        Livraison.objects.filter(pk=livraison.id).update(date_attribution=il_y_a_3_min)

        count = DeliveryService.expire_expired_deliveries()
        self.assertEqual(count, 1)

        livraison.refresh_from_db()
        self.assertIsNone(livraison.livreur)
        self.assertEqual(livraison.statut, Livraison.STATUT_EN_ATTENTE)
        self.assertIsNone(livraison.date_attribution)

        serializer = LivraisonSerializer(livraison)
        self.assertIsNone(serializer.data['acceptance_deadline'])

    def test_4_reapparition_available(self):
        """TEST 4 — La course expirée réapparaît dans la liste disponible"""
        livraison = self._creer_commande_et_livraison('CMD-TEST-4')
        DeliveryService.attribuer_livraison(livraison.id, self.driver_a)

        # Forcer expiration
        Livraison.objects.filter(pk=livraison.id).update(date_attribution=timezone.now() - timedelta(minutes=3))

        self.client.force_authenticate(user=self.user_driver_b)
        response = self.client.get(reverse('deliveries:livraison-available'))
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        livraison_ids = [item['id'] for item in response.data]
        self.assertIn(livraison.id, livraison_ids)

    def test_5_acceptation_apres_expiration(self):
        """TEST 5 — Tentative d'acceptation après expiration par API"""
        livraison = self._creer_commande_et_livraison('CMD-TEST-5')
        DeliveryService.attribuer_livraison(livraison.id, self.driver_a)

        # Forcer expiration
        Livraison.objects.filter(pk=livraison.id).update(date_attribution=timezone.now() - timedelta(minutes=3))

        self.client.force_authenticate(user=self.user_driver_a)
        url = reverse('deliveries:livraison-accept', kwargs={'pk': livraison.id})
        response = self.client.post(url)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("expiré", response.data['detail'].lower())

        # Vérifier que la course est libérée en BDD
        livraison.refresh_from_db()
        self.assertIsNone(livraison.livreur)
        self.assertEqual(livraison.statut, Livraison.STATUT_EN_ATTENTE)

    def test_6_fermeture_navigateur_et_expiration(self):
        """TEST 6 — Simulation fermeture navigateur et traitement backend"""
        livraison = self._creer_commande_et_livraison('CMD-TEST-6')
        DeliveryService.attribuer_livraison(livraison.id, self.driver_a)

        # Navigateur fermé, le temps s'écoule côté serveur
        Livraison.objects.filter(pk=livraison.id).update(date_attribution=timezone.now() - timedelta(minutes=2, seconds=10))

        # Tâche périodique backend ou requête ultérieure
        DeliveryService.expire_expired_deliveries()

        livraison.refresh_from_db()
        self.assertIsNone(livraison.livreur)
        self.assertEqual(livraison.statut, Livraison.STATUT_EN_ATTENTE)

    def test_7_concurrence_acceptation(self):
        """TEST 7 — Concurrence entre deux livreurs"""
        livraison = self._creer_commande_et_livraison('CMD-TEST-7')

        # Driver A accepte la course disponible
        res_a = DeliveryService.accepter_mission(livraison.id, self.driver_a)
        self.assertEqual(res_a.livreur, self.driver_a)

        # Driver B tente d'accepter immédiatement la même course
        with self.assertRaises(Exception) as cm:
            DeliveryService.accepter_mission(livraison.id, self.driver_b)
        
        self.assertIn("déjà été acceptée", str(cm.exception))

    def test_8_expiration_et_reattribution(self):
        """TEST 8 — Expiration du livreur A et acceptation par le livreur B"""
        livraison = self._creer_commande_et_livraison('CMD-TEST-8')
        DeliveryService.attribuer_livraison(livraison.id, self.driver_a)

        # Driver A ne réagit pas, 3 min passent
        Livraison.objects.filter(pk=livraison.id).update(date_attribution=timezone.now() - timedelta(minutes=3))

        # Driver B accepte la course expirée de A
        res_b = DeliveryService.accepter_mission(livraison.id, self.driver_b)
        
        livraison.refresh_from_db()
        self.assertEqual(livraison.livreur, self.driver_b)
        self.assertEqual(livraison.statut, Livraison.STATUT_ACCEPTEE)
        self.assertNotEqual(livraison.livreur, self.driver_a)

    def test_9_course_deja_acceptee_ne_doit_pas_expirer(self):
        """TEST 9 — Une course déjà ACCEPTEE sous 2 min ne doit pas expirer ultérieurement"""
        livraison = self._creer_commande_et_livraison('CMD-TEST-9')
        DeliveryService.attribuer_livraison(livraison.id, self.driver_a)
        DeliveryService.accepter_mission(livraison.id, self.driver_a)

        # 10 minutes s'écoulent après l'acceptation
        Livraison.objects.filter(pk=livraison.id).update(date_attribution=timezone.now() - timedelta(minutes=10))

        count = DeliveryService.expire_expired_deliveries()
        self.assertEqual(count, 0)

        livraison.refresh_from_db()
        self.assertEqual(livraison.statut, Livraison.STATUT_ACCEPTEE)
        self.assertEqual(livraison.livreur, self.driver_a)
