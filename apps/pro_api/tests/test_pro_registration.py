from rest_framework.test import APITestCase
from rest_framework import status
from django.urls import reverse

from apps.users.models import Utilisateur, Role, ProfilLivreur
from apps.catalog.models import Etablissement


class ProRegistrationAPITests(APITestCase):

    def setUp(self):
        self.restaurant_url = reverse('pro_api:register_restaurant')
        self.vendeur_url = reverse('pro_api:register_vendeur')
        self.livreur_url = reverse('pro_api:register_livreur')
        self.status_url = reverse('pro_api:pro_status')

    def test_register_restaurant_success(self):
        payload = {
            "email": "resto.test@ayyou.com",
            "numero_telephone": "+221771112233",
            "password": "Password123!",
            "password_confirm": "Password123!",
            "prenom": "Mamadou",
            "nom": "Diallo",
            "nom_etablissement": "Chez Mamadou Test",
            "adresse": "Avenue Cheikh Anta Diop",
            "specialite": "Thieboudienne"
        }
        response = self.client.post(self.restaurant_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['statut_verification'], 'EN_ATTENTE')
        self.assertEqual(response.data['type_etablissement'], 'RESTAURANT')

        user = Utilisateur.objects.get(email="resto.test@ayyou.com")
        self.assertTrue(user.roles_attribues.filter(role__nom=Role.RESTAURANT).exists())
        self.assertTrue(user.check_password("Password123!"))

        etab = Etablissement.objects.get(id=response.data['etablissement_id'])
        self.assertEqual(etab.type_etablissement, Etablissement.TYPE_RESTAURANT)
        self.assertEqual(etab.statut_verification, Etablissement.STATUT_EN_ATTENTE)
        self.assertFalse(etab.est_verifie)
        self.assertEqual(etab.proprietaire, user)

    def test_register_restaurant_password_mismatch_fails(self):
        payload = {
            "email": "resto.mismatch@ayyou.com",
            "numero_telephone": "+221771119988",
            "password": "Password123!",
            "password_confirm": "WrongPassword!",
            "prenom": "Mamadou",
            "nom": "Diallo",
            "nom_etablissement": "Chez Mamadou Mismatch",
            "adresse": "Avenue Cheikh Anta Diop"
        }
        response = self.client.post(self.restaurant_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("password_confirm", response.data)

    def test_register_vendeur_success(self):
        payload = {
            "email": "vendeur.test@ayyou.com",
            "numero_telephone": "+221772223344",
            "password": "Password123!",
            "password_confirm": "Password123!",
            "prenom": "Fatou",
            "nom": "Ndiaye",
            "nom_etablissement": "Épicerie Fatou",
            "adresse": "Médina Rue 15"
        }
        response = self.client.post(self.vendeur_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['type_etablissement'], 'VENDEUR')

        user = Utilisateur.objects.get(email="vendeur.test@ayyou.com")
        self.assertTrue(user.roles_attribues.filter(role__nom=Role.VENDEUR).exists())
        self.assertTrue(user.check_password("Password123!"))

        etab = Etablissement.objects.get(id=response.data['etablissement_id'])
        self.assertEqual(etab.type_etablissement, Etablissement.TYPE_VENDEUR)
        self.assertEqual(etab.statut_verification, Etablissement.STATUT_EN_ATTENTE)
        self.assertFalse(etab.est_verifie)

    def test_register_livreur_success(self):
        payload = {
            "email": "livreur.test@ayyou.com",
            "numero_telephone": "+221773334455",
            "password": "Password123!",
            "password_confirm": "Password123!",
            "prenom": "Ousmane",
            "nom": "Sow",
            "type_vehicule": "MOTO",
            "immatriculation": "DK-9999-ZZ"
        }
        response = self.client.post(self.livreur_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['statut_verification'], 'EN_ATTENTE')

        user = Utilisateur.objects.get(email="livreur.test@ayyou.com")
        self.assertTrue(user.roles_attribues.filter(role__nom=Role.LIVREUR).exists())
        self.assertTrue(user.check_password("Password123!"))

        profil = ProfilLivreur.objects.get(utilisateur=user)
        self.assertEqual(profil.statut_verification, ProfilLivreur.STATUT_EN_ATTENTE)
        self.assertFalse(profil.est_disponible)
        self.assertEqual(profil.type_vehicule, "MOTO")

    def test_duplicate_email_or_phone_rejected(self):
        # Register a first user
        Utilisateur.objects.create_user(
            email="existant@ayyou.com",
            numero_telephone="+221770000000",
            password="Password123!",
            prenom="Existing",
            nom="User"
        )

        # Try duplicate email
        payload_dup_email = {
            "email": "existant@ayyou.com",
            "numero_telephone": "+221779998877",
            "password": "Password123!",
            "prenom": "Dup",
            "nom": "Test",
            "nom_etablissement": "Boutique Dup",
            "adresse": "Dakar"
        }
        resp = self.client.post(self.restaurant_url, payload_dup_email, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("email", resp.data)

        # Try duplicate phone
        payload_dup_phone = {
            "email": "nouveau@ayyou.com",
            "numero_telephone": "+221770000000",
            "password": "Password123!",
            "prenom": "Dup",
            "nom": "Test",
            "type_vehicule": "MOTO"
        }
        resp2 = self.client.post(self.livreur_url, payload_dup_phone, format='json')
        self.assertEqual(resp2.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("numero_telephone", resp2.data)

    def test_invalid_data_rejected(self):
        payload_invalid = {
            "email": "not-an-email",
            "password": "123"  # too short
        }
        resp = self.client.post(self.restaurant_url, payload_invalid, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_pro_status_endpoint(self):
        # Register restaurant candidate
        payload = {
            "email": "candidate@ayyou.com",
            "numero_telephone": "+221775556677",
            "password": "Password123!",
            "password_confirm": "Password123!",
            "prenom": "Candidate",
            "nom": "Status",
            "nom_etablissement": "Etab Status Test",
            "adresse": "Ouakam"
        }
        resp = self.client.post(self.restaurant_url, payload, format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)

        user = Utilisateur.objects.get(email="candidate@ayyou.com")
        self.client.force_authenticate(user=user)

        resp_status = self.client.get(self.status_url)
        self.assertEqual(resp_status.status_code, status.HTTP_200_OK)
        self.assertEqual(resp_status.data['merchant_status'], 'EN_ATTENTE')
        self.assertFalse(resp_status.data['is_approved'])

    def test_register_restaurant_with_documents_success(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        from apps.catalog.models import DocumentEtablissement

        pdf_file = SimpleUploadedFile("ninea.pdf", b"%PDF-1.4 test ninea content", content_type="application/pdf")
        img_file = SimpleUploadedFile("facade.jpg", b"fake image bytes", content_type="image/jpeg")

        payload = {
            "email": "resto.docs@ayyou.com",
            "numero_telephone": "+221774445566",
            "password": "Password123!",
            "password_confirm": "Password123!",
            "prenom": "Awa",
            "nom": "Sarr",
            "nom_etablissement": "Delices d'Awa",
            "adresse": "Almadies",
            "ninea_file": pdf_file,
            "photo_facade": img_file,
        }
        response = self.client.post(self.restaurant_url, payload, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        etab = Etablissement.objects.get(id=response.data['etablissement_id'])
        self.assertTrue(etab.couverture_url.startswith('/media/') or 'pro_uploads' in etab.couverture_url)

        docs = DocumentEtablissement.objects.filter(etablissement=etab)
        self.assertEqual(docs.count(), 1)
        self.assertEqual(docs.first().type_document, DocumentEtablissement.TYPE_REGISTRE_COMMERCE)

    def test_register_livreur_with_documents_success(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        from apps.users.models import DocumentLivreur

        cni_file = SimpleUploadedFile("cni.pdf", b"%PDF-1.4 test cni content", content_type="application/pdf")
        permis_file = SimpleUploadedFile("permis.jpg", b"fake permis bytes", content_type="image/jpeg")

        payload = {
            "email": "livreur.docs@ayyou.com",
            "numero_telephone": "+221778889900",
            "password": "Password123!",
            "password_confirm": "Password123!",
            "prenom": "Modou",
            "nom": "Diop",
            "type_vehicule": "MOTO",
            "cni_file": cni_file,
            "permis_file": permis_file
        }
        response = self.client.post(self.livreur_url, payload, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        user = Utilisateur.objects.get(email="livreur.docs@ayyou.com")
        profil = ProfilLivreur.objects.get(utilisateur=user)

        docs = DocumentLivreur.objects.filter(profil_livreur=profil)
        self.assertEqual(docs.count(), 2)
        doc_types = set(docs.values_list('type_document', flat=True))
        self.assertIn(DocumentLivreur.TYPE_PIECE_IDENTITE, doc_types)
        self.assertIn(DocumentLivreur.TYPE_PERMIS_CONDUIRE, doc_types)

