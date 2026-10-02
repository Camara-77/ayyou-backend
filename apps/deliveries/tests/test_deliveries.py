from decimal import Decimal
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from django.core.exceptions import ValidationError

from apps.users.models import Utilisateur, ProfilLivreur, DocumentLivreur, Role, UtilisateurRole
from apps.catalog.models import Etablissement, Produit
from apps.orders.models import Commande, SousCommande, LigneCommande
from apps.payments.models import Paiement, Facture
from apps.payments.services import PaymentService
from apps.deliveries.models import Livraison
from apps.deliveries.services import DeliveryService


class DeliveryDomainTestCase(TestCase):
    def setUp(self):
        self.client_user = Utilisateur.objects.create_user(
            numero_telephone='+221771112233',
            email='client1@ayyou.com',
            prenom='Moussa',
            nom='Diallo'
        )
        self.other_user = Utilisateur.objects.create_user(
            numero_telephone='+221779998877',
            email='client2@ayyou.com',
            prenom='Awa',
            nom='Ndiaye'
        )

        self.etablissement = Etablissement.objects.create(
            nom="Dakar Burger",
            adresse="Plateau, Dakar",
            telephone="+221338000000"
        )
        self.produit = Produit.objects.create(
            etablissement=self.etablissement,
            nom="Burger Special",
            prix_base=Decimal("3500.00")
        )

        # Création d'une commande
        self.commande = Commande.objects.create(
            utilisateur=self.client_user,
            adresse_livraison="Mermoz, Dakar",
            nom_destinataire="Moussa Diallo",
            telephone_destinataire="+221771112233",
            sous_total=Decimal("3500.00"),
            frais_livraison=Decimal("1000.00"),
            total=Decimal("4500.00")
        )
        self.sous_commande = SousCommande.objects.create(
            commande=self.commande,
            etablissement=self.etablissement,
            sous_total=Decimal("3500.00"),
            frais_livraison=Decimal("1000.00"),
            total=Decimal("4500.00")
        )
        self.ligne = LigneCommande.objects.create(
            sous_commande=self.sous_commande,
            produit=self.produit,
            nom_produit_snapshot="Burger Special",
            prix_unitaire=Decimal("3500.00"),
            quantite=1,
            total_ligne=Decimal("3500.00")
        )

        self.api_client = APIClient()

    def test_mock_payment_flow_generates_facture_and_livraison(self):
        # 1. Initialisation paiement simulé
        paiement = PaymentService.initier_paiement(self.commande, methode=Paiement.METHODE_WAVE)
        self.assertEqual(paiement.statut, Paiement.STATUT_INITIE)

        # 2. Confirmation paiement simulé réussi
        paiement = PaymentService.confirmer_paiement(paiement, transaction_externe="SIM_WAVE_12345")
        self.assertEqual(paiement.statut, Paiement.STATUT_PAYE)

        # Vérifications
        self.commande.refresh_from_db()
        self.assertEqual(self.commande.statut, Commande.STATUT_PAYEE)

        # Facture générée
        facture = Facture.objects.get(commande=self.commande)
        self.assertTrue(facture.est_payee)

        # Passage des sous-commandes à PRETE pour déclencher la création de livraison
        for sc in self.commande.sous_commandes.all():
            sc.statut = Commande.STATUT_PRETE
            sc.save()
            DeliveryService.synchroniser_statuts_apres_sous_commande(sc)

        # Livraison générée
        livraison = Livraison.objects.get(commande=self.commande)
        self.assertIsNotNone(livraison.token_qr)
        self.assertTrue(livraison.token_qr.startswith("AYYOU-DELIVERY-"))
        self.assertEqual(len(livraison.code_validation), 4)
        self.assertTrue(livraison.code_validation.isdigit())

    def test_mock_payment_failed_and_canceled(self):
        paiement = PaymentService.initier_paiement(self.commande, methode=Paiement.METHODE_ORANGE_MONEY)
        
        # Échec simulé
        paiement_echoue = PaymentService.echouer_paiement(paiement, motif="Fonds insuffisants")
        self.assertEqual(paiement_echoue.statut, Paiement.STATUT_ECHOUE)

        # Nouveau paiement et Annulation simulée
        paiement_nouveau = PaymentService.initier_paiement(self.commande, methode=Paiement.METHODE_ORANGE_MONEY)
        paiement_annule = PaymentService.annuler_paiement(paiement_nouveau, motif="Annulé par client")
        self.assertEqual(paiement_annule.statut, Paiement.STATUT_ANNULE)

    def test_qr_token_uniqueness_and_validation(self):
        livraison1 = DeliveryService.creer_livraison(self.commande)
        
        # Deuxième commande
        commande2 = Commande.objects.create(
            utilisateur=self.other_user,
            adresse_livraison="Fann, Dakar",
            nom_destinataire="Awa Ndiaye",
            telephone_destinataire="+221779998877",
            total=Decimal("2000.00")
        )
        livraison2 = DeliveryService.creer_livraison(commande2)

        self.assertNotEqual(livraison1.token_qr, livraison2.token_qr)
        self.assertNotEqual(livraison1.code_validation, livraison2.code_validation)

    def test_validation_by_qr_code_success(self):
        livraison = DeliveryService.creer_livraison(self.commande)
        self.assertFalse(livraison.est_validee)

        # Validation par QR Token
        livraison_validee = DeliveryService.valider_par_qr(livraison.token_qr)
        self.assertTrue(livraison_validee.est_validee)
        self.assertEqual(livraison_validee.methode_validation, Livraison.METHODE_QR_CODE)
        self.assertEqual(livraison_validee.statut, Livraison.STATUT_LIVREE)

        self.commande.refresh_from_db()
        self.assertEqual(self.commande.statut, Commande.STATUT_LIVREE)

    def test_validation_by_4_digit_code_success(self):
        livraison = DeliveryService.creer_livraison(self.commande)
        self.assertFalse(livraison.est_validee)

        # Validation par Code 4 Chiffres
        livraison_validee = DeliveryService.valider_par_code(self.commande.id, livraison.code_validation)
        self.assertTrue(livraison_validee.est_validee)
        self.assertEqual(livraison_validee.methode_validation, Livraison.METHODE_CODE_VALIDATION)
        self.assertEqual(livraison_validee.statut, Livraison.STATUT_LIVREE)

        self.commande.refresh_from_db()
        self.assertEqual(self.commande.statut, Commande.STATUT_LIVREE)

    def test_rejection_of_reused_qr_or_code(self):
        livraison = DeliveryService.creer_livraison(self.commande)
        DeliveryService.valider_par_qr(livraison.token_qr)

        # Deuxième tentative avec le même QR Token
        with self.assertRaises(ValidationError):
            DeliveryService.valider_par_qr(livraison.token_qr)

        # Deuxième tentative avec le même Code 6 Chiffres
        with self.assertRaises(ValidationError):
            DeliveryService.valider_par_code(self.commande.id, livraison.code_validation)

    def test_rejection_of_invalid_qr_and_wrong_code(self):
        DeliveryService.creer_livraison(self.commande)

        # QR Invalide
        with self.assertRaises(ValidationError):
            DeliveryService.valider_par_qr("AYYOU-DELIVERY-INVALID-TOKEN-999")

        # Code Invalide
        with self.assertRaises(ValidationError):
            DeliveryService.valider_par_code(self.commande.id, "000000")

    def test_api_deliveries_isolation(self):
        livraison = DeliveryService.creer_livraison(self.commande)

        # 1. Utilisateur non authentifié
        response = self.api_client.get('/api/deliveries/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        # 2. Utilisateur d'une autre commande
        self.api_client.force_authenticate(user=self.other_user)
        response = self.api_client.get('/api/deliveries/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data if isinstance(response.data, list) else response.data.get('results', [])
        self.assertEqual(len(results), 0)

        # 3. Client propriétaire
        self.api_client.force_authenticate(user=self.client_user)
        response = self.api_client.get('/api/deliveries/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data if isinstance(response.data, list) else response.data.get('results', [])
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['code_validation'], livraison.code_validation)

    def test_api_validation_endpoints(self):
        livraison = DeliveryService.creer_livraison(self.commande)
        self.api_client.force_authenticate(user=self.client_user)

        # Test validation par QR API
        res = self.api_client.post('/api/deliveries/validate-qr/', {'token_qr': livraison.token_qr}, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertTrue(res.data['est_validee'])
        self.assertEqual(res.data['methode_validation'], 'QR_CODE')


class LivreurIntegrationTestCase(TestCase):
    """
    Suite de tests pour l'Étape 10.2 : Livreur ↔ Livraison, Missions disponibles, Acceptation, Pickup & Sécurité.
    """

    def setUp(self):
        self.api_client = APIClient()
        self.role_livreur, _ = Role.objects.get_or_create(nom=Role.LIVREUR)

        # Client standard
        self.client_user = Utilisateur.objects.create_user(
            email='client.liv@ayyou.com',
            numero_telephone='+221770009988',
            password='Password123!',
            prenom='Ibrahima',
            nom='Sarr'
        )

        # Livreur A (Validé & Disponible)
        self.user_driver_a = Utilisateur.objects.create_user(
            email='livreur.a@ayyou.com',
            numero_telephone='+221771110001',
            password='Password123!',
            prenom='Modou',
            nom='Fall'
        )
        UtilisateurRole.objects.create(utilisateur=self.user_driver_a, role=self.role_livreur)
        self.profil_driver_a = ProfilLivreur.objects.create(
            utilisateur=self.user_driver_a,
            statut_verification=ProfilLivreur.STATUT_VALIDE,
            latitude_actuelle=14.6655,
            longitude_actuelle=-17.4334
        )
        self.profil_driver_a.est_disponible = True
        self.profil_driver_a.save()

        # Livreur B (Validé & Disponible)
        self.user_driver_b = Utilisateur.objects.create_user(
            email='livreur.b@ayyou.com',
            numero_telephone='+221771110002',
            password='Password123!',
            prenom='Cheikh',
            nom='Diop'
        )
        UtilisateurRole.objects.create(utilisateur=self.user_driver_b, role=self.role_livreur)
        self.profil_driver_b = ProfilLivreur.objects.create(
            utilisateur=self.user_driver_b,
            statut_verification=ProfilLivreur.STATUT_VALIDE,
            latitude_actuelle=14.6700,
            longitude_actuelle=-17.4300
        )
        self.profil_driver_b.est_disponible = True
        self.profil_driver_b.save()

        # Livreur C (En Attente)
        self.user_driver_c = Utilisateur.objects.create_user(
            email='livreur.c@ayyou.com',
            numero_telephone='+221771110003',
            password='Password123!',
            prenom='Ousmane',
            nom='Sow'
        )
        UtilisateurRole.objects.create(utilisateur=self.user_driver_c, role=self.role_livreur)
        self.profil_driver_c = ProfilLivreur.objects.create(
            utilisateur=self.user_driver_c,
            statut_verification=ProfilLivreur.STATUT_EN_ATTENTE
        )

        # Création d'établissement et commande
        self.etablissement = Etablissement.objects.create(
            nom="Le Lagon 1",
            adresse="Corniche Est, Dakar",
            telephone="+221338210000"
        )
        self.produit = Produit.objects.create(
            etablissement=self.etablissement,
            nom="Thieboudienne P Poisson",
            prix_base=Decimal("2500.00")
        )
        self.commande = Commande.objects.create(
            utilisateur=self.client_user,
            adresse_livraison="Ngor, Dakar",
            nom_destinataire="Ibrahima Sarr",
            telephone_destinataire="+221770009988",
            sous_total=Decimal("2500.00"),
            frais_livraison=Decimal("1000.00"),
            total=Decimal("3500.00")
        )
        self.sous_commande = SousCommande.objects.create(
            commande=self.commande,
            etablissement=self.etablissement,
            sous_total=Decimal("2500.00"),
            frais_livraison=Decimal("1000.00"),
            total=Decimal("3500.00")
        )
        self.ligne = LigneCommande.objects.create(
            sous_commande=self.sous_commande,
            produit=self.produit,
            nom_produit_snapshot="Thieboudienne P Poisson",
            prix_unitaire=Decimal("2500.00"),
            quantite=1,
            total_ligne=Decimal("2500.00")
        )
        self.livraison = DeliveryService.creer_livraison(self.commande)

    def test_relation_livraison_et_profil_livreur_retention(self):
        """Vérifier la relation entre Livraison et ProfilLivreur et la stratégie SET_NULL."""
        self.assertEqual(self.livraison.livreur, self.profil_driver_a)
        self.livraison.save()

        self.livraison.refresh_from_db()
        self.assertEqual(self.livraison.livreur, self.profil_driver_a)

        # Suppression du ProfilLivreur : la livraison doit être conservée avec livreur=None
        self.profil_driver_a.delete()
        self.livraison.refresh_from_db()
        self.assertIsNone(self.livraison.livreur)
        self.assertIsNotNone(self.livraison.id)

    def test_permissions_livreur_disponibles(self):
        """Vérifier l'accès à /api/deliveries/available/ selon l'authentification et le statut_verification."""
        url = '/api/deliveries/available/'

        # 1. Non authentifié -> 401
        res = self.api_client.get(url)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

        # 2. Client standard (sans rôle Livreur) -> 403
        self.api_client.force_authenticate(user=self.client_user)
        res = self.api_client.get(url)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

        # 3. Livreur EN_ATTENTE -> 403
        self.api_client.force_authenticate(user=self.user_driver_c)
        res = self.api_client.get(url)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

        # 4. Livreur VALIDE -> 200 OK
        self.api_client.force_authenticate(user=self.user_driver_a)
        res = self.api_client.get(url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]['id'], self.livraison.id)

    def test_acceptation_mission_success_et_concurrence(self):
        """Vérifier l'acceptation d'une mission et l'anti-concurrence entre livreurs."""
        url = f'/api/deliveries/{self.livraison.id}/accept/'
        self.api_client.force_authenticate(user=self.user_driver_a)

        res = self.api_client.post(url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['statut'], Livraison.STATUT_ACCEPTEE)
        self.assertEqual(res.data['livreur_id'], self.profil_driver_a.id)

        self.livraison.refresh_from_db()
        self.assertEqual(self.livraison.statut, Livraison.STATUT_ACCEPTEE)
        self.assertEqual(self.livraison.livreur, self.profil_driver_a)

        # Deuxième livreur tente d'accepter la même livraison
        self.api_client.force_authenticate(user=self.user_driver_b)
        res2 = self.api_client.post(url)
        self.assertEqual(res2.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Course déjà attribuée", str(res2.data))

    def test_pickup_commande_et_isolation(self):
        """Vérifier la déclaration de récupération (pickup) et l'isolation entre livreurs."""
        # Livreur A accepte la mission
        DeliveryService.accepter_mission(self.livraison.id, self.profil_driver_a)

        pickup_url = f'/api/deliveries/{self.livraison.id}/pickup/'

        # Livreur B tente de faire le pickup de la livraison de Livreur A -> 400
        self.api_client.force_authenticate(user=self.user_driver_b)
        res_b = self.api_client.post(pickup_url)
        self.assertEqual(res_b.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("pas affectée à votre compte", str(res_b.data))

        # Livreur A fait le pickup -> 200 OK
        self.api_client.force_authenticate(user=self.user_driver_a)
        res_a = self.api_client.post(pickup_url)
        self.assertEqual(res_a.status_code, status.HTTP_200_OK)
        self.assertEqual(res_a.data['statut'], Livraison.STATUT_EN_LIVRAISON)

        self.livraison.refresh_from_db()
        self.commande.refresh_from_db()
        self.assertEqual(self.livraison.statut, Livraison.STATUT_EN_LIVRAISON)
        self.assertEqual(self.commande.statut, Commande.STATUT_EN_LIVRAISON)

    def test_driver_mes_livraisons_isolation(self):
        """Vérifier que le livreur consulte uniquement les livraisons qui lui sont affectées."""
        DeliveryService.accepter_mission(self.livraison.id, self.profil_driver_a)

        # Livreur B consulte mes livraisons -> 0 livraison
        self.api_client.force_authenticate(user=self.user_driver_b)
        res_b = self.api_client.get('/api/deliveries/')
        self.assertEqual(res_b.status_code, status.HTTP_200_OK)
        results_b = res_b.data if isinstance(res_b.data, list) else res_b.data.get('results', [])
        self.assertEqual(len(results_b), 0)

        # Livreur A consulte mes livraisons -> 1 livraison
        self.api_client.force_authenticate(user=self.user_driver_a)
        res_a = self.api_client.get('/api/deliveries/')
        self.assertEqual(res_a.status_code, status.HTTP_200_OK)
        results_a = res_a.data if isinstance(res_a.data, list) else res_a.data.get('results', [])
        self.assertEqual(len(results_a), 1)
        self.assertEqual(results_a[0]['id'], self.livraison.id)


class DriverProfileApiTestCase(TestCase):
    """
    Suite de tests pour l'Étape 10.4 : Consultation du profil Livreur, gestion de la disponibilité et isolation des documents.
    """

    def setUp(self):
        self.api_client = APIClient()
        self.role_livreur, _ = Role.objects.get_or_create(nom=Role.LIVREUR)

        # 1. Livreur Validé
        self.user_valide = Utilisateur.objects.create_user(
            email='valide@ayyou-pro.com',
            numero_telephone='+221772220001',
            password='Password123!',
            prenom='Babacar',
            nom='Ndiaye'
        )
        UtilisateurRole.objects.create(utilisateur=self.user_valide, role=self.role_livreur)
        self.profil_valide = ProfilLivreur.objects.create(
            utilisateur=self.user_valide,
            statut_verification=ProfilLivreur.STATUT_VALIDE,
            type_vehicule=ProfilLivreur.VEHICULE_MOTO,
            immatriculation='DK-999-AA'
        )
        self.doc_valide = DocumentLivreur.objects.create(
            profil_livreur=self.profil_valide,
            type_document=DocumentLivreur.TYPE_PERMIS_CONDUIRE,
            fichier_url_ou_reference='https://sec.ayyou.com/docs/permis1.pdf',
            statut=DocumentLivreur.STATUT_VALIDE
        )

        # 2. Livreur En Attente
        self.user_attente = Utilisateur.objects.create_user(
            email='attente@ayyou-pro.com',
            numero_telephone='+221772220002',
            password='Password123!',
            prenom='Mamadou',
            nom='Syll'
        )
        UtilisateurRole.objects.create(utilisateur=self.user_attente, role=self.role_livreur)
        self.profil_attente = ProfilLivreur.objects.create(
            utilisateur=self.user_attente,
            statut_verification=ProfilLivreur.STATUT_EN_ATTENTE
        )
        self.doc_attente = DocumentLivreur.objects.create(
            profil_livreur=self.profil_attente,
            type_document=DocumentLivreur.TYPE_PIECE_IDENTITE,
            fichier_url_ou_reference='https://sec.ayyou.com/docs/cni2.pdf',
            statut=DocumentLivreur.STATUT_EN_ATTENTE
        )

        # 3. Client sans profil livreur
        self.user_client = Utilisateur.objects.create_user(
            email='client.simple@ayyou.com',
            numero_telephone='+221772220003',
            password='Password123!',
            prenom='Fatou',
            nom='Binetou'
        )

    def test_01_recuperation_profil_livreur_connecte(self):
        """1. Vérifier la récupération réussie du profil du livreur connecté."""
        self.api_client.force_authenticate(user=self.user_valide)
        res = self.api_client.get('/api/deliveries/profile/')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['prenom'], 'Babacar')
        self.assertEqual(res.data['statut_verification'], 'VALIDE')
        self.assertEqual(res.data['immatriculation'], 'DK-999-AA')

    def test_02_isolation_profil_livreur(self):
        """2. Vérifier qu'un client sans profil livreur ne peut pas accéder à /api/deliveries/profile/."""
        self.api_client.force_authenticate(user=self.user_client)
        res = self.api_client.get('/api/deliveries/profile/')
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

    def test_03_recuperation_documents_livreur(self):
        """3. Vérifier la récupération des documents du livreur connecté."""
        self.api_client.force_authenticate(user=self.user_valide)
        res = self.api_client.get('/api/deliveries/profile/documents/')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]['type_document'], 'PERMIS_CONDUIRE')

    def test_04_isolation_documents_entre_livreurs(self):
        """4. Vérifier qu'un livreur ne voit pas les documents d'un autre livreur."""
        self.api_client.force_authenticate(user=self.user_attente)
        res = self.api_client.get('/api/deliveries/profile/documents/')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]['type_document'], 'PIECE_IDENTITE')

    def test_05_activation_disponibilite_par_livreur_valide(self):
        """5. Vérifier qu'un livreur VALIDE peut activer et désactiver sa disponibilité."""
        self.api_client.force_authenticate(user=self.user_valide)

        # Passer à True
        res1 = self.api_client.patch('/api/deliveries/profile/availability/', {'est_disponible': True}, format='json')
        self.assertEqual(res1.status_code, status.HTTP_200_OK)
        self.assertTrue(res1.data['est_disponible'])
        self.profil_valide.refresh_from_db()
        self.assertTrue(self.profil_valide.est_disponible)

        # Passer à False
        res2 = self.api_client.patch('/api/deliveries/profile/availability/', {'est_disponible': False}, format='json')
        self.assertEqual(res2.status_code, status.HTTP_200_OK)
        self.assertFalse(res2.data['est_disponible'])
        self.profil_valide.refresh_from_db()
        self.assertFalse(self.profil_valide.est_disponible)

    def test_06_refus_disponibilite_livreur_en_attente(self):
        """6. Vérifier qu'un livreur EN_ATTENTE reçoit un HTTP 403 en tentant d'activer sa disponibilité."""
        self.api_client.force_authenticate(user=self.user_attente)
        res = self.api_client.patch('/api/deliveries/profile/availability/', {'est_disponible': True}, format='json')
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn("non validé", str(res.data))

    def test_07_refus_disponibilite_livreur_refuse(self):
        """7. Vérifier qu'un livreur REFUSE reçoit un HTTP 403 en tentant d'activer sa disponibilité."""
        self.profil_attente.statut_verification = ProfilLivreur.STATUT_REFUSE
        self.profil_attente.save()

        self.api_client.force_authenticate(user=self.user_attente)
        res = self.api_client.patch('/api/deliveries/profile/availability/', {'est_disponible': True}, format='json')
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_08_refus_disponibilite_utilisateur_sans_profil_livreur(self):
        """8. Vérifier le refus pour un utilisateur sans profil livreur."""
        self.api_client.force_authenticate(user=self.user_client)
        res = self.api_client.patch('/api/deliveries/profile/availability/', {'est_disponible': True}, format='json')
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)
