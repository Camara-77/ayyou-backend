import json
from unittest.mock import patch
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.users.models import Utilisateur, Role, UtilisateurRole
from apps.catalog.models import Etablissement, DocumentEtablissement
from apps.ai.document_verification_service import DocumentVerificationAIService
from apps.notifications.models import Notification


class AIDocumentVerificationTests(TestCase):
    def setUp(self):
        self.client = APIClient()

        # Création du rôle Super Admin
        self.super_admin_role, _ = Role.objects.get_or_create(nom='SUPER_ADMIN')
        self.client_role, _ = Role.objects.get_or_create(nom='CLIENT')
        self.pro_role, _ = Role.objects.get_or_create(nom='RESTAURANT')

        # Utilisateur Super Admin
        self.super_admin = Utilisateur.objects.create_user(
            email='admin@ayyou.sn',
            password='password123',
            prenom='Mamadou',
            nom='Diallo',
            numero_telephone='+221770000001',
            is_staff=True,
            is_superuser=True
        )
        UtilisateurRole.objects.create(utilisateur=self.super_admin, role=self.super_admin_role)

        # Utilisateur Pro (Restaurateur)
        self.pro_user = Utilisateur.objects.create_user(
            email='moussa@relais.sn',
            password='password123',
            prenom='Moussa',
            nom='Diop',
            numero_telephone='+221781234567'
        )
        UtilisateurRole.objects.create(utilisateur=self.pro_user, role=self.pro_role)

        # Utilisateur Client
        self.client_user = Utilisateur.objects.create_user(
            email='client@ayyou.sn',
            password='password123',
            prenom='Awa',
            nom='Ndiaye',
            numero_telephone='+221770000002'
        )
        UtilisateurRole.objects.create(utilisateur=self.client_user, role=self.client_role)

        # Établissement de test (Le Relais de la Corniche)
        self.etablissement = Etablissement.objects.create(
            nom='Le Relais de la Corniche',
            type_etablissement=Etablissement.TYPE_RESTAURANT,
            proprietaire=self.pro_user,
            adresse='Corniche Ouest, Dakar',
            telephone='+221781234567',
            specialite='Cuisine sénégalaise',
            statut_verification=Etablissement.STATUT_EN_ATTENTE
        )

        # Document NINEA / Registre de commerce conforme
        self.doc_ninea = DocumentEtablissement.objects.create(
            etablissement=self.etablissement,
            type_document=DocumentEtablissement.TYPE_REGISTRE_COMMERCE,
            fichier_url_ou_reference='NINEA_006492012_2V3.pdf',
            statut=DocumentEtablissement.STATUT_EN_ATTENTE,
            commentaire='Attestation fiscale et NINEA conforme'
        )

        # Document CNI du gérant
        self.doc_cni = DocumentEtablissement.objects.create(
            etablissement=self.etablissement,
            type_document=DocumentEtablissement.TYPE_CNI_GERANT,
            fichier_url_ou_reference='CNI_Moussa_Diop.jpg',
            statut=DocumentEtablissement.STATUT_EN_ATTENTE,
            commentaire='Carte Nationale d\'Identité Moussa Diop'
        )

    # -------------------------------------------------------------------------
    # TESTS SÉCURITÉ ET AUTORISATION
    # -------------------------------------------------------------------------
    def test_security_super_admin_authorized(self):
        """Le Super Admin doit pouvoir accéder à l'endpoint d'analyse IA."""
        self.client.force_authenticate(user=self.super_admin)
        url = reverse('admin_panel:business-analyze-documents', kwargs={'pk': self.etablissement.id})
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_security_client_forbidden(self):
        """Un client normal est refusé (HTTP 403)."""
        self.client.force_authenticate(user=self.client_user)
        url = reverse('admin_panel:business-analyze-documents', kwargs={'pk': self.etablissement.id})
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_security_pro_user_forbidden(self):
        """Un restaurateur ne peut pas analyser son propre dossier ni celui des autres."""
        self.client.force_authenticate(user=self.pro_user)
        url = reverse('admin_panel:business-analyze-documents', kwargs={'pk': self.etablissement.id})
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_security_anonymous_unauthorized(self):
        """Un utilisateur non connecté est refusé (HTTP 401)."""
        url = reverse('admin_panel:business-analyze-documents', kwargs={'pk': self.etablissement.id})
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    # -------------------------------------------------------------------------
    # TESTS LOGIQUE IA DOCUMENTAIRE
    # -------------------------------------------------------------------------
    def test_ai_conforming_dossier(self):
        """Un dossier complet avec documents et identité cohérente donne CONFORME."""
        report = DocumentVerificationAIService.analyze_establishment_dossier(self.etablissement)
        self.assertEqual(report['decision'], 'CONFORME')
        self.assertEqual(len(report['inconsistencies']), 0)
        self.assertGreaterEqual(report['confidence'], 0.90)

    def test_ai_non_conforming_identity_mismatch(self):
        """Une incohérence de nom entre le gérant et la CNI génère une recommandation non conforme."""
        self.doc_cni.commentaire = "CNI appartenant à Modou Ndiaye"
        self.doc_cni.fichier_url_ou_reference = "CNI_Modou_Ndiaye.jpg"
        self.doc_cni.save()

        def mock_analyze(doc, inscription):
            if doc.type_document == DocumentEtablissement.TYPE_CNI_GERANT:
                return {
                    'id': doc.id,
                    'type_document': doc.type_document,
                    'type_label': "CNI du gérant",
                    'statut_actuel': 'EN_ATTENTE',
                    'fichier_ref': 'CNI_Modou_Ndiaye.jpg',
                    'est_lisible': True,
                    'extracted_fields': {'nom_complet': 'Modou Ndiaye', 'est_lisible': True},
                    'remarque': 'Document lisible'
                }
            return {
                'id': doc.id,
                'type_document': doc.type_document,
                'type_label': "Registre de Commerce / NINEA",
                'statut_actuel': 'EN_ATTENTE',
                'fichier_ref': 'NINEA_006492012_2V3.pdf',
                'est_lisible': True,
                'extracted_fields': {'ninea': '006492012 / 2V3', 'nom_complet_gerant': 'Moussa Diop', 'est_lisible': True},
                'remarque': 'Document lisible'
            }

        with patch.object(DocumentVerificationAIService, '_analyze_single_document', side_effect=mock_analyze):
            report = DocumentVerificationAIService.analyze_establishment_dossier(self.etablissement)
            self.assertEqual(report['decision'], 'NON_CONFORME')
            self.assertGreater(len(report['inconsistencies']), 0)
            self.assertIn("Modou Ndiaye", report['inconsistencies'][0])
            self.assertGreater(len(report['rejection_reasons']), 0)

    def test_ai_unreadable_document(self):
        """Un document illisible ou flou déclenche une recommandation A_VERIFIER."""
        with patch.object(DocumentVerificationAIService, '_analyze_single_document') as mock_doc_analysis:
            mock_doc_analysis.return_value = {
                'id': self.doc_ninea.id,
                'type_document': DocumentEtablissement.TYPE_REGISTRE_COMMERCE,
                'type_label': "Registre de Commerce / NINEA",
                'statut_actuel': 'EN_ATTENTE',
                'fichier_ref': 'NINEA_flou.jpg',
                'est_lisible': False,
                'extracted_fields': {'nom_complet_gerant': 'Information non lisible', 'est_lisible': False, 'ninea': ''},
                'remarque': 'Document flou'
            }

            report = DocumentVerificationAIService.analyze_establishment_dossier(self.etablissement)
            self.assertIn(report['decision'], ['A_VERIFIER', 'NON_CONFORME'])
            self.assertGreater(len(report['inconsistencies']), 0)

    def test_ai_decision_not_automatic(self):
        """L'IA donne une recommandation mais NE MODIFIE PAS le statut de l'établissement dans la base."""
        self.client.force_authenticate(user=self.super_admin)
        url = reverse('admin_panel:business-analyze-documents', kwargs={'pk': self.etablissement.id})
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Vérification DB : le statut de vérification est TOUJOURS EN_ATTENTE
        self.etablissement.refresh_from_db()
        self.assertEqual(self.etablissement.statut_verification, Etablissement.STATUT_EN_ATTENTE)

    # -------------------------------------------------------------------------
    # TESTS ACCEPTATION, REJET ET EMAILS AUTOMATIQUES
    # -------------------------------------------------------------------------
    def test_super_admin_approve_triggers_email(self):
        """L'approbation manuelle par le Super Admin valide le dossier et déclenche l'email avec le prénom."""
        self.client.force_authenticate(user=self.super_admin)
        url = reverse('admin_panel:business-approve', kwargs={'pk': self.etablissement.id})
        response = self.client.patch(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Vérification DB
        self.etablissement.refresh_from_db()
        self.assertEqual(self.etablissement.statut_verification, Etablissement.STATUT_VALIDE)
        self.assertTrue(self.etablissement.est_verifie)

        # Vérification de la notification Email créée
        notif = Notification.objects.filter(utilisateur=self.pro_user, reference_id=str(self.etablissement.id)).first()
        self.assertIsNotNone(notif)
        self.assertIn("Bienvenue chez AYYOU", notif.titre)
        self.assertIn("Bonjour Moussa", notif.message)

    def test_super_admin_reject_triggers_email_with_custom_motif(self):
        """Le refus par le Super Admin enregistre le motif personnalisé et l'inclut dans l'email."""
        self.client.force_authenticate(user=self.super_admin)
        url = reverse('admin_panel:business-reject', kwargs={'pk': self.etablissement.id})
        custom_motif = "Nom différent entre la CNI et le NINEA. Photo du justificatif illisible."
        response = self.client.patch(url, data={'motif': custom_motif}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Vérification DB
        self.etablissement.refresh_from_db()
        self.assertEqual(self.etablissement.statut_verification, Etablissement.STATUT_REFUSE)

        # Vérification email
        notif = Notification.objects.filter(utilisateur=self.pro_user, reference_id=str(self.etablissement.id)).first()
        self.assertIsNotNone(notif)
        self.assertIn("AYYOU — Mise à jour de votre candidature", notif.titre)
        self.assertIn("Bonjour Moussa", notif.message)
        self.assertIn(custom_motif, notif.message)

    def test_resend_email_endpoint(self):
        """L'endpoint de renvoi d'email fonctionne pour un établissement validé ou refusé."""
        self.client.force_authenticate(user=self.super_admin)
        self.etablissement.statut_verification = Etablissement.STATUT_VALIDE
        self.etablissement.save()

        url = reverse('admin_panel:business-resend-email', kwargs={'pk': self.etablissement.id})
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'success')
