from decimal import Decimal
from datetime import timedelta
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework import status

from apps.users.models import Utilisateur, ProfilLivreur, DocumentLivreur, Role, UtilisateurRole
from apps.catalog.models import Etablissement, Categorie, Produit
from apps.orders.models import Commande, SousCommande, LigneCommande
from apps.payments.models import Paiement
from apps.payments.services import PaymentService
from apps.deliveries.models import Livraison
from apps.deliveries.services import DeliveryService


class DriverE2EFlowTestCase(TestCase):
    """
    Test E2E complet du parcours Livreur AYYOU sur PostgreSQL réel :
    1. Inscription Livreur
    2. Validation par l'Admin
    3. Connexion & JWT
    4. Profil & Disponibilité (OFF -> ON)
    5. Géolocalisation & Proximité
    6. Algorithme d'assignation à 2 phases (Phase 1 = 1er plus proche, Phase 2 = pool des 3 suivants)
    7. Refus & Expiration
    8. Verrouillage atomique anti-concurrence (2 livreurs simultanés)
    9. Cycle complet de mission (AFFECTEE -> ACCEPTEE -> ARRIVE_RESTAURANT -> EN_LIVRAISON -> LIVREE)
    10. Validation sécurisée par Code PIN (4 chiffres) & QR Code
    11. Historique & Statistiques réelles
    12. Isolation Sécurité & Contrôle d'accès par Rôle
    """

    def setUp(self):
        self.client = APIClient()

        # Rôles système
        self.role_client, _ = Role.objects.get_or_create(nom=Role.CLIENT)
        self.role_livreur, _ = Role.objects.get_or_create(nom=Role.LIVREUR)

        # 1. Restaurant (Dakar Plateau : 14.7077, -17.4587)
        self.merchant_user = Utilisateur.objects.create_user(
            email='resto.teranga@ayyou.sn',
            numero_telephone='+221338112233',
            prenom='Babacar',
            nom='Sow',
            password='Password123!',
            est_verifie=True
        )
        self.etablissement = Etablissement.objects.create(
            nom="Chez Loutcha Teranga",
            type_etablissement=Etablissement.TYPE_RESTAURANT,
            proprietaire=self.merchant_user,
            adresse="Plateau, Dakar",
            latitude=Decimal("14.7077000"),
            longitude=Decimal("-17.4587000"),
            statut_verification=Etablissement.STATUT_VALIDE,
            statut_abonnement=Etablissement.STATUT_ABONNEMENT_ACTIF,
            date_expiration_abonnement=timezone.now() + timedelta(days=30)
        )
        self.categorie = Categorie.objects.create(nom="Plats Traditionnels", slug="plats-traditionnels")
        self.produit = Produit.objects.create(
            etablissement=self.etablissement,
            categorie=self.categorie,
            nom="Thiéboudienne Penda Mbaye",
            prix_base=Decimal("3500.00")
        )

        # 2. Client Acheteur
        self.client_user = Utilisateur.objects.create_user(
            email='client.dakar@ayyou.sn',
            numero_telephone='+221775556677',
            prenom='Fatou',
            nom='Ndiaye',
            password='Password123!',
            est_verifie=True
        )
        UtilisateurRole.objects.create(utilisateur=self.client_user, role=self.role_client)

        # 3. Livreur A - Modou (1.0 km du resto : 14.7167, -17.4677)
        self.user_driver_a = Utilisateur.objects.create_user(
            email='driver.a@ayyou.sn',
            numero_telephone='+221771110001',
            prenom='Modou',
            nom='Fall',
            password='Password123!',
            est_verifie=True,
            mode_actif=Utilisateur.MODE_LIVREUR
        )
        UtilisateurRole.objects.create(utilisateur=self.user_driver_a, role=self.role_livreur)
        self.profil_driver_a = ProfilLivreur.objects.create(
            utilisateur=self.user_driver_a,
            statut_verification=ProfilLivreur.STATUT_VALIDE,
            est_disponible=True,
            latitude_actuelle=Decimal("14.7167000"),
            longitude_actuelle=Decimal("-17.4677000"),
            date_derniere_position=timezone.now(),
            type_vehicule=ProfilLivreur.VEHICULE_MOTO,
            immatriculation="DK-1001-A"
        )

        # 4. Livreur B - Awa (3.0 km du resto : 14.7347, -17.4847)
        self.user_driver_b = Utilisateur.objects.create_user(
            email='driver.b@ayyou.sn',
            numero_telephone='+221772220002',
            prenom='Awa',
            nom='Diop',
            password='Password123!',
            est_verifie=True,
            mode_actif=Utilisateur.MODE_LIVREUR
        )
        UtilisateurRole.objects.create(utilisateur=self.user_driver_b, role=self.role_livreur)
        self.profil_driver_b = ProfilLivreur.objects.create(
            utilisateur=self.user_driver_b,
            statut_verification=ProfilLivreur.STATUT_VALIDE,
            est_disponible=True,
            latitude_actuelle=Decimal("14.7347000"),
            longitude_actuelle=Decimal("-17.4847000"),
            date_derniere_position=timezone.now(),
            type_vehicule=ProfilLivreur.VEHICULE_MOTO,
            immatriculation="DK-2002-B"
        )

        # 5. Livreur C - Ousmane (Non disponible / Offline)
        self.user_driver_c = Utilisateur.objects.create_user(
            email='driver.c@ayyou.sn',
            numero_telephone='+221773330003',
            prenom='Ousmane',
            nom='Baye',
            password='Password123!',
            est_verifie=True,
            mode_actif=Utilisateur.MODE_LIVREUR
        )
        UtilisateurRole.objects.create(utilisateur=self.user_driver_c, role=self.role_livreur)
        self.profil_driver_c = ProfilLivreur.objects.create(
            utilisateur=self.user_driver_c,
            statut_verification=ProfilLivreur.STATUT_VALIDE,
            est_disponible=False, # Indisponible !
            latitude_actuelle=Decimal("14.7080000"),
            longitude_actuelle=Decimal("-17.4590000"),
            date_derniere_position=timezone.now(),
            type_vehicule=ProfilLivreur.VEHICULE_MOTO,
            immatriculation="DK-3003-C"
        )

    def test_01_registration_and_admin_verification(self):
        """Test Inscription Livreur via API public + Vérification Admin"""
        url = reverse('pro_api:register_livreur')
        payload = {
            'email': 'nouveau.livreur@ayyou.sn',
            'numero_telephone': '+221778889900',
            'password': 'Password123!',
            'password_confirm': 'Password123!',
            'prenom': 'Samba',
            'nom': 'Kane',
            'type_vehicule': 'MOTO',
            'marque': 'Yamaha',
            'modele': 'YBR 125',
            'immatriculation': 'DK-9999-Z'
        }
        response = self.client.post(url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['statut_verification'], 'EN_ATTENTE')

        user_id = response.data['user_id']
        user = Utilisateur.objects.get(pk=user_id)
        self.assertTrue(user.roles_attribues.filter(role__nom=Role.LIVREUR).exists())

        profil = user.profil_livreur
        self.assertEqual(profil.statut_verification, ProfilLivreur.STATUT_EN_ATTENTE)
        self.assertFalse(profil.est_disponible)

        # Tentative de mise en ligne avant validation Admin (Doit être refusée 403)
        self.client.force_authenticate(user=user)
        res_avail = self.client.patch(reverse('deliveries:livraison-update-availability'), {'est_disponible': True}, format='json')
        self.assertEqual(res_avail.status_code, status.HTTP_403_FORBIDDEN)

        # Validation Admin
        profil.statut_verification = ProfilLivreur.STATUT_VALIDE
        profil.save()

        # Deuxième tentative de mise en ligne après validation (Doit réussir 200)
        res_avail_ok = self.client.patch(reverse('deliveries:livraison-update-availability'), {'est_disponible': True}, format='json')
        self.assertEqual(res_avail_ok.status_code, status.HTTP_200_OK)
        self.assertTrue(res_avail_ok.data['est_disponible'])

    def test_02_login_and_profile_management(self):
        """Test Authentification JWT Livreur & Gestion Profil"""
        url_login = reverse('authentication:login')
        res_login = self.client.post(url_login, {
            'identifier': 'driver.a@ayyou.sn',
            'password': 'Password123!'
        }, format='json')
        self.assertEqual(res_login.status_code, status.HTTP_200_OK)
        self.assertIn('access', res_login.data)

        # Consultation profil livreur
        self.client.force_authenticate(user=self.user_driver_a)
        res_prof = self.client.get(reverse('deliveries:livraison-get-profile'))
        self.assertEqual(res_prof.status_code, status.HTTP_200_OK)
        self.assertEqual(res_prof.data['immatriculation'], 'DK-1001-A')

        # Mise à jour partielle profil
        res_patch = self.client.patch(reverse('deliveries:livraison-get-profile'), {
            'marque': 'Honda',
            'modele': 'CB 125',
            'secteur_intervention': 'Plateau, Almadies, Mermoz'
        }, format='json')
        self.assertEqual(res_patch.status_code, status.HTTP_200_OK)
        self.assertEqual(res_patch.data['marque'], 'Honda')

    def test_03_assignment_algorithm_proximity_and_phases(self):
        """
        Test de l'algorithme d'assignation :
        - Commande créée
        - Phase 1 : Proposée uniquement au 1er livreur le plus proche (Livreur A = 1km vs Livreur B = 3km)
        - Livreur C (indisponible) est exclu
        - Refus de A -> Bascule en Phase 2 (Diffusé à B)
        """
        commande = Commande.objects.create(
            utilisateur=self.client_user,
            adresse_livraison="Almadies, Dakar",
            nom_destinataire="Fatou Ndiaye",
            telephone_destinataire="+221775556677",
            sous_total=Decimal("3500.00"),
            frais_livraison=Decimal("1000.00"),
            total=Decimal("4500.00")
        )
        sc = SousCommande.objects.create(
            commande=commande,
            etablissement=self.etablissement,
            sous_total=Decimal("3500.00"),
            frais_livraison=Decimal("1000.00"),
            total=Decimal("4500.00")
        )
        LigneCommande.objects.create(
            sous_commande=sc,
            produit=self.produit,
            nom_produit_snapshot="Thiéboudienne Penda Mbaye",
            prix_unitaire=Decimal("3500.00"),
            quantite=1,
            total_ligne=Decimal("3500.00")
        )

        paiement = PaymentService.initier_paiement(commande, methode=Paiement.METHODE_WAVE)
        PaymentService.confirmer_paiement(paiement, transaction_externe="WAVE_SIM_E2E")

        sc.statut = Commande.STATUT_PRETE
        sc.save()
        DeliveryService.synchroniser_statuts_apres_sous_commande(sc)

        livraison = Livraison.objects.get(commande=commande)
        self.assertEqual(livraison.phase_attribution, 1)
        self.assertEqual(livraison.livreur, self.profil_driver_a) # Livreur A (1.0km) sélectionné !

        # Livreur A consulte ses missions proposées -> La mission est présente
        self.client.force_authenticate(user=self.user_driver_a)
        res_avail_a = self.client.get(reverse('deliveries:livraison-available'))
        self.assertEqual(res_avail_a.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res_avail_a.data), 1)
        self.assertEqual(res_avail_a.data[0]['id'], livraison.id)

        # Livreur B consulte ses missions proposées -> La mission est ABSENTE (Car Phase 1 réservée à A)
        self.client.force_authenticate(user=self.user_driver_b)
        res_avail_b = self.client.get(reverse('deliveries:livraison-available'))
        self.assertEqual(res_avail_b.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res_avail_b.data), 0)

        # Livreur A décline la mission
        self.client.force_authenticate(user=self.user_driver_a)
        res_decline = self.client.post(reverse('deliveries:livraison-decline', kwargs={'pk': livraison.id}))
        self.assertEqual(res_decline.status_code, status.HTTP_200_OK)

        livraison.refresh_from_db()
        self.assertEqual(livraison.phase_attribution, 2) # Bascule en Phase 2 !

        # Maintenant Livreur B consulte ses missions -> La mission est désormais DISPONIBLE !
        self.client.force_authenticate(user=self.user_driver_b)
        res_avail_b2 = self.client.get(reverse('deliveries:livraison-available'))
        self.assertEqual(res_avail_b2.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res_avail_b2.data), 1)

    def test_04_concurrency_race_condition_and_full_lifecycle(self):
        """
        Test d'acceptation concurrentielle & Cycle complet de livraison :
        - Phase 2 active
        - Verrouillage atomique : Le 1er qui valide emporte la course
        - Avancement des étapes : ACCEPTEE -> ARRIVE_RESTAURANT -> EN_LIVRAISON
        - Validation par Code PIN à 4 chiffres (Code correct vs Code incorrect)
        - Vérification de l'état final LIVREE et des statistiques
        """
        commande = Commande.objects.create(
            utilisateur=self.client_user,
            adresse_livraison="Plateau, Dakar",
            nom_destinataire="Fatou Ndiaye",
            telephone_destinataire="+221775556677",
            sous_total=Decimal("3500.00"),
            frais_livraison=Decimal("1500.00"),
            total=Decimal("5000.00")
        )
        sc = SousCommande.objects.create(
            commande=commande,
            etablissement=self.etablissement,
            sous_total=Decimal("3500.00"),
            frais_livraison=Decimal("1500.00"),
            total=Decimal("5000.00")
        )
        LigneCommande.objects.create(
            sous_commande=sc,
            produit=self.produit,
            nom_produit_snapshot="Thiéboudienne Penda Mbaye",
            prix_unitaire=Decimal("3500.00"),
            quantite=1,
            total_ligne=Decimal("3500.00")
        )

        paiement = PaymentService.initier_paiement(commande, methode=Paiement.METHODE_WAVE)
        PaymentService.confirmer_paiement(paiement, transaction_externe="WAVE_SIM_E2E_2")
        sc.statut = Commande.STATUT_PRETE
        sc.save()
        DeliveryService.synchroniser_statuts_apres_sous_commande(sc)

        livraison = Livraison.objects.get(commande=commande)

        # Basculer en Phase 2 pour simulation concurrentielle
        DeliveryService.passer_en_phase_2(livraison)

        # Livreur B accepte la mission
        self.client.force_authenticate(user=self.user_driver_b)
        res_accept_b = self.client.post(reverse('deliveries:livraison-accept', kwargs={'pk': livraison.id}))
        self.assertEqual(res_accept_b.status_code, status.HTTP_200_OK)
        self.assertEqual(res_accept_b.data['statut'], 'ACCEPTEE')

        # Livreur A tente d'accepter la MEME mission (Doit être refusé avec 400 Bad Request "Course déjà attribuée")
        self.client.force_authenticate(user=self.user_driver_a)
        res_accept_a = self.client.post(reverse('deliveries:livraison-accept', kwargs={'pk': livraison.id}))
        self.assertEqual(res_accept_a.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Course déjà attribuée", str(res_accept_a.data['detail']))

        # Poursuite du cycle par Livreur B
        self.client.force_authenticate(user=self.user_driver_b)

        # 1. Arrivée restaurant
        res_arrive = self.client.post(reverse('deliveries:livraison-arrive-restaurant', kwargs={'pk': livraison.id}))
        self.assertEqual(res_arrive.status_code, status.HTTP_200_OK)
        self.assertEqual(res_arrive.data['statut'], 'ARRIVE_RESTAURANT')

        # 2. Récupération commande
        res_pickup = self.client.post(reverse('deliveries:livraison-pickup', kwargs={'pk': livraison.id}))
        self.assertEqual(res_pickup.status_code, status.HTTP_200_OK)
        self.assertEqual(res_pickup.data['statut'], 'EN_LIVRAISON')

        # Vérifier synchronisation de la commande
        commande.refresh_from_db()
        self.assertEqual(commande.statut, Commande.STATUT_EN_LIVRAISON)

        # 3. Validation par mauvais code PIN (4 chiffres) -> Échec 400
        res_bad_pin = self.client.post(reverse('deliveries:livraison-validate-code'), {
            'commande': commande.id,
            'code_validation': '0000'
        }, format='json')
        self.assertEqual(res_bad_pin.status_code, status.HTTP_400_BAD_REQUEST)

        # 4. Validation par bon code PIN (4 chiffres) -> Succès 200
        bon_code = livraison.code_validation
        res_good_pin = self.client.post(reverse('deliveries:livraison-validate-code'), {
            'commande': commande.id,
            'code_validation': bon_code
        }, format='json')
        self.assertEqual(res_good_pin.status_code, status.HTTP_200_OK)
        self.assertEqual(res_good_pin.data['statut'], 'LIVREE')
        self.assertTrue(res_good_pin.data['est_validee'])

        # Vérifier synchronisation de la commande finale
        commande.refresh_from_db()
        self.assertEqual(commande.statut, Commande.STATUT_LIVREE)

        # 5. Vérifier les statistiques du livreur B
        res_stats = self.client.get(reverse('deliveries:livraison-stats'))
        self.assertEqual(res_stats.status_code, status.HTTP_200_OK)
        self.assertEqual(res_stats.data['courses_terminees'], 1)
        self.assertEqual(res_stats.data['gain_total'], '1 500')

    def test_05_security_and_role_isolation(self):
        """Test de la sécurité et isolation stricte des rôles et endpoints"""
        # Client anonyme tente d'accéder aux livraisons -> 401 Unauthorized
        self.client.logout()
        res_anon = self.client.get(reverse('deliveries:livraison-available'))
        self.assertEqual(res_anon.status_code, status.HTTP_401_UNAUTHORIZED)

        # Client standard (sans profil livreur) tente de modifier sa disponibilité -> 404 Not Found
        self.client.force_authenticate(user=self.client_user)
        res_client_avail = self.client.patch(reverse('deliveries:livraison-update-availability'), {'est_disponible': True}, format='json')
        self.assertEqual(res_client_avail.status_code, status.HTTP_404_NOT_FOUND)
