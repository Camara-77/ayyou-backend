from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient
from apps.users.models import Utilisateur, ProfilLivreur, DocumentLivreur
from apps.ai.document_verification_service import DocumentVerificationAIService

class AIDriverDocumentVerificationTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        
        # Super Admin User
        self.super_admin = Utilisateur.objects.create_superuser(
            email='admin@ayyou.com',
            numero_telephone='+221770000000',
            password='AdminPassword123!',
            nom='Admin',
            prenom='Super'
        )

        # Normal Driver User
        self.driver_user = Utilisateur.objects.create_user(
            email='driver@ayyou.com',
            numero_telephone='+221778214490',
            password='DriverPassword123!',
            nom='Seck',
            prenom='Alioune Badara',
            mode_actif=Utilisateur.MODE_LIVREUR
        )

        self.driver_profile = ProfilLivreur.objects.create(
            utilisateur=self.driver_user,
            type_vehicule='MOTO',
            marque='Yamaha',
            modele='YBR 125cc',
            immatriculation='SN-DK-7718-BC',
            statut_verification=ProfilLivreur.STATUT_EN_ATTENTE,
            est_disponible=False
        )

        # Create Driver Documents
        self.doc_cni = DocumentLivreur.objects.create(
            profil_livreur=self.driver_profile,
            type_document='PIECE_IDENTITE',
            fichier_url_ou_reference='https://example.com/cni.jpg',
            statut=DocumentLivreur.STATUT_EN_ATTENTE,
            commentaire='CNI Recto/Verso Alioune Badara Seck'
        )

        self.doc_permis = DocumentLivreur.objects.create(
            profil_livreur=self.driver_profile,
            type_document='PERMIS_CONDUIRE',
            fichier_url_ou_reference='https://example.com/permis.pdf',
            statut=DocumentLivreur.STATUT_EN_ATTENTE,
            commentaire='Permis de conduire Catégorie A'
        )

    def test_security_super_admin_only(self):
        """Vérifie que seul un Super Admin peut appeler l'endpoint d'analyse IA."""
        url = f"/api/admin/drivers/{self.driver_profile.id}/analyze-documents/"

        # Anonymous request -> 401
        res_anon = self.client.post(url, {})
        self.assertEqual(res_anon.status_code, status.HTTP_401_UNAUTHORIZED)

        # Normal driver request -> 403
        self.client.force_authenticate(user=self.driver_user)
        res_driver = self.client.post(url, {})
        self.assertEqual(res_driver.status_code, status.HTTP_403_FORBIDDEN)

        # Super admin request -> 200
        self.client.force_authenticate(user=self.super_admin)
        res_admin = self.client.post(url, {})
        self.assertEqual(res_admin.status_code, status.HTTP_200_OK)
        self.assertIn('decision', res_admin.data)
        self.assertIn('recommendation', res_admin.data)

    def test_ai_analysis_service_conforme(self):
        """Teste le service d'analyse IA pour un dossier valide."""
        report = DocumentVerificationAIService.analyze_driver_dossier(self.driver_profile)
        self.assertIn(report.get('decision'), ['CONFORME', 'NON_CONFORME', 'A_VERIFIER'])
        self.assertIn('recommendation', report)
        self.assertIn('identity_analysis', report)
        self.assertIn('driver_license_analysis', report)
        self.assertIn('vehicle_registration_analysis', report)

    def test_ai_analysis_does_not_mutate_db_status(self):
        """Vérifie que l'analyse IA ne modifie PAS le statut du livreur dans la BDD."""
        url = f"/api/admin/drivers/{self.driver_profile.id}/analyze-documents/"
        self.client.force_authenticate(user=self.super_admin)
        res = self.client.post(url, {})
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        self.driver_profile.refresh_from_db()
        self.assertEqual(self.driver_profile.statut_verification, ProfilLivreur.STATUT_EN_ATTENTE)

    def test_super_admin_approve_driver(self):
        """Vérifie que le Super Admin peut approuver le livreur."""
        url = f"/api/admin/drivers/{self.driver_profile.id}/approve/"
        self.client.force_authenticate(user=self.super_admin)
        res = self.client.patch(url, {})
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        self.driver_profile.refresh_from_db()
        self.assertEqual(self.driver_profile.statut_verification, ProfilLivreur.STATUT_VALIDE)

    def test_super_admin_reject_driver_with_motif(self):
        """Vérifie que le Super Admin peut rejeter un livreur avec un motif."""
        url = f"/api/admin/drivers/{self.driver_profile.id}/reject/"
        self.client.force_authenticate(user=self.super_admin)
        res = self.client.patch(url, {'motif': 'Permis de conduire illisible'})
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        self.driver_profile.refresh_from_db()
        self.assertEqual(self.driver_profile.statut_verification, ProfilLivreur.STATUT_REFUSE)

    def test_resend_email_driver(self):
        """Vérifie l'endpoint de renvoi d'email pour un livreur validé."""
        self.driver_profile.statut_verification = ProfilLivreur.STATUT_VALIDE
        self.driver_profile.save()

        url = f"/api/admin/drivers/{self.driver_profile.id}/resend-email/"
        self.client.force_authenticate(user=self.super_admin)
        res = self.client.post(url, {})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data.get('status'), 'success')
