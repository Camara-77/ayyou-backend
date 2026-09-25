from unittest.mock import patch
from rest_framework.test import APITestCase
from rest_framework import status
from django.urls import reverse
from decimal import Decimal

from apps.users.models import Utilisateur, ProfilClient, ProfilLivreur, Role, UtilisateurRole, DocumentLivreur
from apps.catalog.models import Etablissement, Categorie, Produit, DocumentEtablissement
from apps.orders.models import Commande, SousCommande
from apps.deliveries.models import Livraison
from apps.payments.models import Paiement
from apps.admin_panel.models import AuditLog


class SuperAdminBackendTestCase(APITestCase):
    def setUp(self):
        # Create Super Admin User
        self.superadmin = Utilisateur.objects.create_superuser(
            email='admin@ayyou.com',
            numero_telephone='+221770000000',
            password='Password123!',
            prenom='Super',
            nom='Admin'
        )

        # Create Standard Client User
        self.client_user = Utilisateur.objects.create_user(
            email='client@ayyou.com',
            numero_telephone='+221771111111',
            password='Password123!',
            prenom='Jean',
            nom='Client'
        )
        ProfilClient.objects.create(utilisateur=self.client_user)

        # Create Livreur User & Profile
        self.livreur_user = Utilisateur.objects.create_user(
            email='livreur@ayyou.com',
            numero_telephone='+221772222222',
            password='Password123!',
            prenom='Moussa',
            nom='Livreur'
        )
        self.profil_livreur = ProfilLivreur.objects.create(
            utilisateur=self.livreur_user,
            statut_verification=ProfilLivreur.STATUT_EN_ATTENTE,
            type_vehicule=ProfilLivreur.VEHICULE_MOTO
        )

        # Create Business Owner & Etablissements
        self.owner_user = Utilisateur.objects.create_user(
            email='owner@ayyou.com',
            numero_telephone='+221773333333',
            password='Password123!',
            prenom='Awa',
            nom='Resto'
        )
        self.restaurant = Etablissement.objects.create(
            nom='Le Gourmet Teranga',
            type_etablissement=Etablissement.TYPE_RESTAURANT,
            proprietaire=self.owner_user,
            adresse='Plateau, Dakar',
            telephone='+221338888888',
            est_verifie=False
        )
        self.vendeur = Etablissement.objects.create(
            nom='Délices de Fatima',
            type_etablissement=Etablissement.TYPE_VENDEUR,
            proprietaire=self.owner_user,
            adresse='Medina, Dakar',
            telephone='+221339999999',
            est_verifie=False
        )

        # Create Category & Product
        self.category = Categorie.objects.create(
            slug='plats-nationaux',
            nom='Plats Nationaux',
            ordre=1
        )
        self.product = Produit.objects.create(
            etablissement=self.restaurant,
            categorie=self.category,
            nom='Thiéboudienne Rouge',
            description='Riz au poisson classique',
            prix_base=Decimal('2500.00'),
            stock_disponible=50
        )

        # Create Order & Delivery
        self.commande = Commande.objects.create(
            utilisateur=self.client_user,
            statut=Commande.STATUT_PAYEE,
            sous_total=Decimal('2500.00'),
            frais_livraison=Decimal('1000.00'),
            total=Decimal('3500.00'),
            adresse_livraison='Point E, Dakar',
            nom_destinataire='Jean Client',
            telephone_destinataire='+221771111111'
        )
        self.livraison = Livraison.objects.create(
            commande=self.commande,
            token_qr='TOKEN-TEST-QR-123456789',
            code_validation='123456',
            statut=Livraison.STATUT_EN_ATTENTE
        )
        self.paiement = Paiement.objects.create(
            commande=self.commande,
            reference='PAY-TEST-0001',
            montant=Decimal('3500.00'),
            methode=Paiement.METHODE_WAVE,
            statut=Paiement.STATUT_PAYE
        )

    def test_unauthenticated_request_rejected(self):
        url = reverse('admin_panel:dashboard')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_non_admin_user_forbidden(self):
        self.client.force_authenticate(user=self.client_user)
        url = reverse('admin_panel:dashboard')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_superadmin_dashboard_kpis(self):
        self.client.force_authenticate(user=self.superadmin)
        url = reverse('admin_panel:dashboard')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data

        self.assertIn('total_utilisateurs', data)
        self.assertIn('restaurants', data)
        self.assertIn('vendeurs', data)
        self.assertNotIn('vendeurs vendeurs', data)
        self.assertIn('livreurs', data)
        self.assertIn('dossiers_en_attente', data)

        self.assertEqual(data['total_utilisateurs'], 4)
        self.assertEqual(data['restaurants'], 1)
        self.assertEqual(data['vendeurs'], 1)
        self.assertEqual(data['livreurs'], 1)
        self.assertEqual(data['dossiers_en_attente'], 3)

    def test_superadmin_dashboard_pending_actions(self):
        self.client.force_authenticate(user=self.superadmin)
        url = reverse('admin_panel:pending_actions')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['etablissements_en_attente']), 2)
        self.assertEqual(len(response.data['livreurs_en_attente']), 1)

    def test_user_management_toggle_status_and_audit(self):
        self.client.force_authenticate(user=self.superadmin)
        url = reverse('admin_panel:user-toggle-status', kwargs={'pk': self.client_user.pk})
        response = self.client.patch(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.client_user.refresh_from_db()
        self.assertFalse(self.client_user.est_actif)

        audit_log = AuditLog.objects.filter(ressource="Utilisateur", resource_id=str(self.client_user.pk)).first()
        self.assertIsNotNone(audit_log)
        self.assertIn("TOGGLE_USER_STATUS", audit_log.action)

    def test_business_approval_and_audit(self):
        self.client.force_authenticate(user=self.superadmin)
        url = reverse('admin_panel:business-approve', kwargs={'pk': self.restaurant.pk})
        response = self.client.patch(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.restaurant.refresh_from_db()
        self.assertTrue(self.restaurant.est_verifie)

        audit_log = AuditLog.objects.filter(action="APPROVE_BUSINESS", resource_id=str(self.restaurant.pk)).first()
        self.assertIsNotNone(audit_log)
        self.assertEqual(audit_log.statut, AuditLog.STATUT_SUCCESS)

    def test_restaurant_approve_synchronizes_pending_documents(self):
        self.client.force_authenticate(user=self.superadmin)
        doc_pending = DocumentEtablissement.objects.create(
            etablissement=self.restaurant,
            type_document=DocumentEtablissement.TYPE_REGISTRE_COMMERCE,
            fichier_url_ou_reference='/media/test1.pdf',
            statut=DocumentEtablissement.STATUT_EN_ATTENTE
        )
        doc_already_valide = DocumentEtablissement.objects.create(
            etablissement=self.restaurant,
            type_document=DocumentEtablissement.TYPE_CERTIFICAT_HYGIENE,
            fichier_url_ou_reference='/media/test2.pdf',
            statut=DocumentEtablissement.STATUT_VALIDE
        )
        doc_already_refuse = DocumentEtablissement.objects.create(
            etablissement=self.restaurant,
            type_document=DocumentEtablissement.TYPE_CNI_GERANT,
            fichier_url_ou_reference='/media/test3.pdf',
            statut=DocumentEtablissement.STATUT_REFUSE
        )

        url = reverse('admin_panel:business-approve', kwargs={'pk': self.restaurant.pk})
        response = self.client.patch(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        doc_pending.refresh_from_db()
        doc_already_valide.refresh_from_db()
        doc_already_refuse.refresh_from_db()

        self.assertEqual(doc_pending.statut, DocumentEtablissement.STATUT_VALIDE)
        self.assertEqual(doc_already_valide.statut, DocumentEtablissement.STATUT_VALIDE)
        self.assertEqual(doc_already_refuse.statut, DocumentEtablissement.STATUT_REFUSE)

    def test_restaurant_reject_synchronizes_pending_documents(self):
        self.client.force_authenticate(user=self.superadmin)
        doc_pending = DocumentEtablissement.objects.create(
            etablissement=self.restaurant,
            type_document=DocumentEtablissement.TYPE_REGISTRE_COMMERCE,
            fichier_url_ou_reference='/media/test1.pdf',
            statut=DocumentEtablissement.STATUT_EN_ATTENTE
        )
        doc_already_valide = DocumentEtablissement.objects.create(
            etablissement=self.restaurant,
            type_document=DocumentEtablissement.TYPE_CERTIFICAT_HYGIENE,
            fichier_url_ou_reference='/media/test2.pdf',
            statut=DocumentEtablissement.STATUT_VALIDE
        )

        url = reverse('admin_panel:business-reject', kwargs={'pk': self.restaurant.pk})
        response = self.client.patch(url, {'motif': 'Non conforme'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        doc_pending.refresh_from_db()
        doc_already_valide.refresh_from_db()

        self.assertEqual(doc_pending.statut, DocumentEtablissement.STATUT_REFUSE)
        self.assertEqual(doc_already_valide.statut, DocumentEtablissement.STATUT_VALIDE)

    def test_vendeur_approve_synchronizes_pending_documents(self):
        self.client.force_authenticate(user=self.superadmin)
        doc_pending = DocumentEtablissement.objects.create(
            etablissement=self.vendeur,
            type_document=DocumentEtablissement.TYPE_REGISTRE_COMMERCE,
            fichier_url_ou_reference='/media/test_vendeur.pdf',
            statut=DocumentEtablissement.STATUT_EN_ATTENTE
        )

        url = reverse('admin_panel:business-approve', kwargs={'pk': self.vendeur.pk})
        response = self.client.patch(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        doc_pending.refresh_from_db()
        self.assertEqual(doc_pending.statut, DocumentEtablissement.STATUT_VALIDE)

    def test_vendeur_reject_synchronizes_pending_documents(self):
        self.client.force_authenticate(user=self.superadmin)
        doc_pending = DocumentEtablissement.objects.create(
            etablissement=self.vendeur,
            type_document=DocumentEtablissement.TYPE_REGISTRE_COMMERCE,
            fichier_url_ou_reference='/media/test_vendeur.pdf',
            statut=DocumentEtablissement.STATUT_EN_ATTENTE
        )

        url = reverse('admin_panel:business-reject', kwargs={'pk': self.vendeur.pk})
        response = self.client.patch(url, {'motif': 'Dossier rejeté'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        doc_pending.refresh_from_db()
        self.assertEqual(doc_pending.statut, DocumentEtablissement.STATUT_REFUSE)

    def test_driver_approval_and_audit(self):
        self.client.force_authenticate(user=self.superadmin)
        url = reverse('admin_panel:driver-approve', kwargs={'pk': self.profil_livreur.pk})
        response = self.client.patch(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.profil_livreur.refresh_from_db()
        self.assertEqual(self.profil_livreur.statut_verification, ProfilLivreur.STATUT_VALIDE)

        audit_log = AuditLog.objects.filter(action="APPROVE_DRIVER", resource_id=str(self.profil_livreur.pk)).first()
        self.assertIsNotNone(audit_log)

    def test_driver_approve_synchronizes_pending_documents(self):
        self.client.force_authenticate(user=self.superadmin)
        doc_pending = DocumentLivreur.objects.create(
            profil_livreur=self.profil_livreur,
            type_document=DocumentLivreur.TYPE_PIECE_IDENTITE,
            fichier_url_ou_reference='/media/driver_cni.pdf',
            statut=DocumentLivreur.STATUT_EN_ATTENTE
        )
        doc_already_valide = DocumentLivreur.objects.create(
            profil_livreur=self.profil_livreur,
            type_document=DocumentLivreur.TYPE_PERMIS_CONDUIRE,
            fichier_url_ou_reference='/media/driver_permis.pdf',
            statut=DocumentLivreur.STATUT_VALIDE
        )
        doc_already_refuse = DocumentLivreur.objects.create(
            profil_livreur=self.profil_livreur,
            type_document=DocumentLivreur.TYPE_CARTE_GRISE,
            fichier_url_ou_reference='/media/driver_grise.pdf',
            statut=DocumentLivreur.STATUT_REFUSE
        )

        url = reverse('admin_panel:driver-approve', kwargs={'pk': self.profil_livreur.pk})
        response = self.client.patch(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        doc_pending.refresh_from_db()
        doc_already_valide.refresh_from_db()
        doc_already_refuse.refresh_from_db()

        self.assertEqual(doc_pending.statut, DocumentLivreur.STATUT_VALIDE)
        self.assertEqual(doc_already_valide.statut, DocumentLivreur.STATUT_VALIDE)
        self.assertEqual(doc_already_refuse.statut, DocumentLivreur.STATUT_REFUSE)

    def test_driver_reject_synchronizes_pending_documents(self):
        self.client.force_authenticate(user=self.superadmin)
        doc_pending = DocumentLivreur.objects.create(
            profil_livreur=self.profil_livreur,
            type_document=DocumentLivreur.TYPE_PIECE_IDENTITE,
            fichier_url_ou_reference='/media/driver_cni.pdf',
            statut=DocumentLivreur.STATUT_EN_ATTENTE
        )

        url = reverse('admin_panel:driver-reject', kwargs={'pk': self.profil_livreur.pk})
        response = self.client.patch(url, {'motif': 'Permis faux'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        doc_pending.refresh_from_db()
        self.assertEqual(doc_pending.statut, DocumentLivreur.STATUT_REFUSE)
        self.profil_livreur.refresh_from_db()
        self.assertEqual(self.profil_livreur.statut_verification, ProfilLivreur.STATUT_REFUSE)
        self.assertFalse(self.profil_livreur.est_disponible)

    @patch('apps.notifications.n8n_service.N8nNotificationService.send_pro_rejection_for_etablissement')
    def test_business_rejection_triggers_n8n_event(self, mock_n8n_rejection):
        self.client.force_authenticate(user=self.superadmin)
        url = reverse('admin_panel:business-reject', kwargs={'pk': self.restaurant.pk})
        motif_text = "NINEA expiré et invalide"
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.patch(url, {'motif': motif_text}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.restaurant.refresh_from_db()
        self.assertEqual(self.restaurant.statut_verification, Etablissement.STATUT_REFUSE)
        self.assertFalse(self.restaurant.est_verifie)

        audit_log = AuditLog.objects.filter(action="REJECT_BUSINESS", resource_id=str(self.restaurant.pk)).first()
        self.assertIsNotNone(audit_log)
        self.assertEqual(audit_log.details.get('motif'), motif_text)

        mock_n8n_rejection.assert_called_once_with(self.restaurant, motif_text)

    @patch('apps.notifications.n8n_service.N8nNotificationService.send_pro_rejection_for_driver')
    def test_driver_rejection_triggers_n8n_event(self, mock_n8n_rejection):
        self.client.force_authenticate(user=self.superadmin)
        url = reverse('admin_panel:driver-reject', kwargs={'pk': self.profil_livreur.pk})
        motif_text = "Casier judiciaire non vierge"
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.patch(url, {'motif': motif_text}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.profil_livreur.refresh_from_db()
        self.assertEqual(self.profil_livreur.statut_verification, ProfilLivreur.STATUT_REFUSE)
        self.assertFalse(self.profil_livreur.est_disponible)

        audit_log = AuditLog.objects.filter(action="REJECT_DRIVER", resource_id=str(self.profil_livreur.pk)).first()
        self.assertIsNotNone(audit_log)
        self.assertEqual(audit_log.details.get('motif'), motif_text)

        mock_n8n_rejection.assert_called_once_with(self.profil_livreur, motif_text)

    def test_rejection_endpoints_security(self):
        # 1. Unauthenticated request
        url_biz = reverse('admin_panel:business-reject', kwargs={'pk': self.restaurant.pk})
        res_unauth = self.client.patch(url_biz, {'motif': 'Test'}, format='json')
        self.assertEqual(res_unauth.status_code, status.HTTP_401_UNAUTHORIZED)

        url_driver = reverse('admin_panel:driver-reject', kwargs={'pk': self.profil_livreur.pk})
        res_unauth_drv = self.client.patch(url_driver, {'motif': 'Test'}, format='json')
        self.assertEqual(res_unauth_drv.status_code, status.HTTP_401_UNAUTHORIZED)

        # 2. Non-SuperAdmin standard client user
        self.client.force_authenticate(user=self.client_user)
        res_forbidden_biz = self.client.patch(url_biz, {'motif': 'Test'}, format='json')
        self.assertEqual(res_forbidden_biz.status_code, status.HTTP_403_FORBIDDEN)

        res_forbidden_drv = self.client.patch(url_driver, {'motif': 'Test'}, format='json')
        self.assertEqual(res_forbidden_drv.status_code, status.HTTP_403_FORBIDDEN)

    def test_order_status_update_and_driver_assignment(self):
        self.client.force_authenticate(user=self.superadmin)

        # 1. Update status
        url_status = reverse('admin_panel:order-update-order-status', kwargs={'pk': self.commande.pk})
        response = self.client.patch(url_status, {'statut': Commande.STATUT_EN_PREPARATION}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.commande.refresh_from_db()
        self.assertEqual(self.commande.statut, Commande.STATUT_EN_PREPARATION)

        # 2. Validate driver first then assign
        self.profil_livreur.statut_verification = ProfilLivreur.STATUT_VALIDE
        self.profil_livreur.save()

        url_assign = reverse('admin_panel:order-assign-driver', kwargs={'pk': self.commande.pk})
        response = self.client.post(url_assign, {'driver_id': self.profil_livreur.pk}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.livraison.refresh_from_db()
        self.assertEqual(self.livraison.livreur, self.profil_livreur)
        self.assertEqual(self.livraison.statut, Livraison.STATUT_AFFECTEE)

    def test_assign_driver_statut_verification_rules(self):
        self.client.force_authenticate(user=self.superadmin)
        url_assign = reverse('admin_panel:order-assign-driver', kwargs={'pk': self.commande.pk})

        # 1. EN_ATTENTE -> refused 400
        self.profil_livreur.statut_verification = ProfilLivreur.STATUT_EN_ATTENTE
        self.profil_livreur.save()
        res_attente = self.client.post(url_assign, {'driver_id': self.profil_livreur.pk}, format='json')
        self.assertEqual(res_attente.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Livreur non validé', res_attente.data.get('error', ''))

        # 2. REFUSE -> refused 400
        self.profil_livreur.statut_verification = ProfilLivreur.STATUT_REFUSE
        self.profil_livreur.save()
        res_refuse = self.client.post(url_assign, {'driver_id': self.profil_livreur.pk}, format='json')
        self.assertEqual(res_refuse.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Livreur non validé', res_refuse.data.get('error', ''))

        # 3. VALIDE -> allowed 200
        self.profil_livreur.statut_verification = ProfilLivreur.STATUT_VALIDE
        self.profil_livreur.save()
        res_valide = self.client.post(url_assign, {'driver_id': self.profil_livreur.pk}, format='json')
        self.assertEqual(res_valide.status_code, status.HTTP_200_OK)

    def test_atomic_transaction_rollback(self):
        self.client.force_authenticate(user=self.superadmin)
        url_assign = reverse('admin_panel:order-assign-driver', kwargs={'pk': self.commande.pk})
        self.profil_livreur.statut_verification = ProfilLivreur.STATUT_VALIDE
        self.profil_livreur.save()

        # Mock AdminAuditService.log_action to raise an exception inside the atomic transaction block
        with patch('apps.admin_panel.views.AdminAuditService.log_action', side_effect=Exception("Simulated Audit Failure")):
            with self.assertRaises(Exception):
                self.client.post(url_assign, {'driver_id': self.profil_livreur.pk}, format='json')

        # Verify DB rollback: livraison remains unassigned
        self.livraison.refresh_from_db()
        self.assertIsNone(self.livraison.livreur)
        self.assertNotEqual(self.livraison.statut, Livraison.STATUT_AFFECTEE)

    def test_category_reorder_and_product_moderation(self):
        self.client.force_authenticate(user=self.superadmin)

        # Category reorder
        url_reorder = reverse('admin_panel:catalog_category-reorder')
        response = self.client.post(url_reorder, {'orders': [{'id': self.category.pk, 'ordre': 10}]}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.category.refresh_from_db()
        self.assertEqual(self.category.ordre, 10)

        # Product moderation
        url_moderate = reverse('admin_panel:catalog_product-moderate', kwargs={'pk': self.product.pk})
        response = self.client.patch(url_moderate, {'est_disponible': False}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.product.refresh_from_db()
        self.assertFalse(self.product.est_disponible)

    def test_payment_reconciliation_and_audit_log_list(self):
        self.client.force_authenticate(user=self.superadmin)

        # Payment reconcile
        url_reconcile = reverse('admin_panel:payment-reconcile', kwargs={'pk': self.paiement.pk})
        response = self.client.post(url_reconcile, {'note': 'Rapprochement bancaire OK'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.paiement.refresh_from_db()
        self.assertTrue(self.paiement.metadata.get('reconciled'))

        # Audit Log List
        url_audit = reverse('admin_panel:audit_log-list')
        response = self.client.get(url_audit)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data['results'] if isinstance(response.data, dict) and 'results' in response.data else response.data), 1)

    def test_superadmin_restaurant_detail_with_documents(self):
        from apps.catalog.models import DocumentEtablissement
        doc = DocumentEtablissement.objects.create(
            etablissement=self.restaurant,
            type_document=DocumentEtablissement.TYPE_REGISTRE_COMMERCE,
            fichier_url_ou_reference='/media/pro_uploads/documents/ninea_test.pdf',
            statut=DocumentEtablissement.STATUT_EN_ATTENTE,
            commentaire='NINEA Officiel'
        )

        self.client.force_authenticate(user=self.superadmin)
        url = reverse('admin_panel:business-detail', kwargs={'pk': self.restaurant.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.data
        self.assertEqual(data['id'], self.restaurant.pk)
        self.assertEqual(data['type_etablissement'], 'RESTAURANT')

        # Check candidate info
        self.assertEqual(data['proprietaire_email'], self.owner_user.email)
        self.assertEqual(data['proprietaire_telephone'], self.owner_user.numero_telephone)
        self.assertIsNotNone(data['candidat'])
        self.assertEqual(data['candidat']['email'], self.owner_user.email)

        # Check documents
        self.assertEqual(len(data['documents']), 1)
        doc_data = data['documents'][0]
        self.assertEqual(doc_data['type_document'], 'REGISTRE_COMMERCE')
        self.assertEqual(doc_data['commentaire'], 'NINEA Officiel')
        self.assertTrue(doc_data['fichier_url'].startswith('http') or doc_data['fichier_url'].startswith('/media/'))

    def test_superadmin_vendeur_detail_with_documents(self):
        from apps.catalog.models import DocumentEtablissement
        doc = DocumentEtablissement.objects.create(
            etablissement=self.vendeur,
            type_document=DocumentEtablissement.TYPE_CERTIFICAT_HYGIENE,
            fichier_url_ou_reference='/media/pro_uploads/documents/hygiene_test.pdf',
            statut=DocumentEtablissement.STATUT_EN_ATTENTE
        )

        self.client.force_authenticate(user=self.superadmin)
        url = reverse('admin_panel:business-detail', kwargs={'pk': self.vendeur.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.data
        self.assertEqual(data['type_etablissement'], 'VENDEUR')
        self.assertEqual(data['proprietaire_email'], self.owner_user.email)
        self.assertEqual(len(data['documents']), 1)

    def test_superadmin_driver_detail_with_documents(self):
        from apps.users.models import DocumentLivreur
        doc = DocumentLivreur.objects.create(
            profil_livreur=self.profil_livreur,
            type_document=DocumentLivreur.TYPE_PIECE_IDENTITE,
            fichier_url_ou_reference='/media/pro_uploads/documents/cni_test.pdf',
            statut=DocumentLivreur.STATUT_EN_ATTENTE
        )

        self.client.force_authenticate(user=self.superadmin)
        url = reverse('admin_panel:driver-detail', kwargs={'pk': self.profil_livreur.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.data
        self.assertEqual(data['id'], self.profil_livreur.pk)
        self.assertEqual(data['email'], self.livreur_user.email)
        self.assertEqual(data['telephone'], self.livreur_user.numero_telephone)
        self.assertEqual(len(data['documents']), 1)
        self.assertTrue(data['documents'][0]['fichier_url'].startswith('http') or data['documents'][0]['fichier_url'].startswith('/media/'))

    def test_detail_endpoint_permissions_non_admin_forbidden(self):
        self.client.force_authenticate(user=self.client_user)
        url_bus = reverse('admin_panel:business-detail', kwargs={'pk': self.restaurant.pk})
        url_drv = reverse('admin_panel:driver-detail', kwargs={'pk': self.profil_livreur.pk})

        res_bus = self.client.get(url_bus)
        res_drv = self.client.get(url_drv)

        self.assertEqual(res_bus.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(res_drv.status_code, status.HTTP_403_FORBIDDEN)

