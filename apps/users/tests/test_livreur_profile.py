from django.test import TestCase
from django.core.exceptions import ValidationError
from django.utils import timezone
from apps.users.models import Utilisateur, ProfilLivreur, DocumentLivreur, Role, UtilisateurRole
from apps.users.serializers import ProfilLivreurSerializer, DocumentLivreurSerializer


class ProfilLivreurTestCase(TestCase):
    """
    Tests unitaires pour le modèle et la logique métier ProfilLivreur et DocumentLivreur.
    """

    def setUp(self):
        self.user = Utilisateur.objects.create_user(
            email='livreur.test@ayyou.com',
            numero_telephone='+221770001122',
            password='Password123!',
            prenom='Modou',
            nom='Fall'
        )
        self.role_livreur, _ = Role.objects.get_or_create(nom=Role.LIVREUR)
        UtilisateurRole.objects.create(utilisateur=self.user, role=self.role_livreur)

    def test_01_creation_profil_livreur_defaut(self):
        """1. Vérifier la création par défaut d'un ProfilLivreur avec statut EN_ATTENTE et est_disponible=False."""
        profil = ProfilLivreur.objects.create(utilisateur=self.user)
        self.assertIsNotNone(profil.id)
        self.assertEqual(profil.statut_verification, ProfilLivreur.STATUT_EN_ATTENTE)
        self.assertFalse(profil.est_disponible)
        self.assertEqual(profil.type_vehicule, ProfilLivreur.VEHICULE_MOTO)
        self.assertEqual(str(profil), f"Profil Livreur de Modou Fall (En attente)")

    def test_02_contrainte_disponibilite_interdite_si_non_valide(self):
        """2. Vérifier qu'un livreur EN_ATTENTE ou REFUSE ne peut pas être disponible (ValidationError)."""
        profil = ProfilLivreur.objects.create(utilisateur=self.user)
        
        # Tenter d'activer la disponibilité en statut EN_ATTENTE
        profil.est_disponible = True
        with self.assertRaises(ValidationError):
            profil.save()

        # Passer en statut REFUSE et tenter d'activer la disponibilité
        profil.statut_verification = ProfilLivreur.STATUT_REFUSE
        with self.assertRaises(ValidationError):
            profil.save()

    def test_03_disponibilite_autorisee_si_statut_valide(self):
        """3. Vérifier qu'un livreur validé peut activer/désactiver sa disponibilité."""
        profil = ProfilLivreur.objects.create(utilisateur=self.user)
        profil.statut_verification = ProfilLivreur.STATUT_VALIDE
        profil.save()

        profil.est_disponible = True
        profil.save()
        self.assertTrue(profil.est_disponible)

        profil.est_disponible = False
        profil.save()
        self.assertFalse(profil.est_disponible)

    def test_04_champs_vehicule_et_geolocalisation(self):
        """4. Vérifier l'enregistrement des détails du véhicule et de la géolocalisation."""
        maintenant = timezone.now()
        profil = ProfilLivreur.objects.create(
            utilisateur=self.user,
            type_vehicule=ProfilLivreur.VEHICULE_VOITURE,
            marque='Toyota',
            modele='Yaris',
            immatriculation='DK-1234-AB',
            latitude_actuelle=14.6937,
            longitude_actuelle=-17.4441,
            date_derniere_position=maintenant
        )
        self.assertEqual(profil.type_vehicule, ProfilLivreur.VEHICULE_VOITURE)
        self.assertEqual(profil.marque, 'Toyota')
        self.assertEqual(profil.modele, 'Yaris')
        self.assertEqual(profil.immatriculation, 'DK-1234-AB')
        self.assertEqual(float(profil.latitude_actuelle), 14.6937)
        self.assertEqual(float(profil.longitude_actuelle), -17.4441)
        self.assertEqual(profil.date_derniere_position, maintenant)

    def test_05_creation_et_verification_document_livreur(self):
        """5. Vérifier la création et la gestion des documents justificatifs."""
        profil = ProfilLivreur.objects.create(utilisateur=self.user)
        doc = DocumentLivreur.objects.create(
            profil_livreur=profil,
            type_document=DocumentLivreur.TYPE_PERMIS_CONDUIRE,
            fichier_url_ou_reference='https://storage.ayyou.com/docs/permis_123.pdf'
        )

        self.assertIsNotNone(doc.id)
        self.assertEqual(doc.type_document, DocumentLivreur.TYPE_PERMIS_CONDUIRE)
        self.assertEqual(doc.statut, DocumentLivreur.STATUT_EN_ATTENTE)
        self.assertIn("Permis de conduire", str(doc))

        # Valider le document
        doc.statut = DocumentLivreur.STATUT_VALIDE
        doc.date_verification = timezone.now()
        doc.commentaire = "Document valide et lisible"
        doc.save()

        self.assertEqual(doc.statut, DocumentLivreur.STATUT_VALIDE)
        self.assertEqual(doc.commentaire, "Document valide et lisible")

    def test_06_serializers_profil_et_document_livreur(self):
        """6. Vérifier la sérialisation des modèles ProfilLivreur et DocumentLivreur."""
        profil = ProfilLivreur.objects.create(
            utilisateur=self.user,
            type_vehicule=ProfilLivreur.VEHICULE_MOTO,
            immatriculation='DK-5678-CD'
        )
        doc = DocumentLivreur.objects.create(
            profil_livreur=profil,
            type_document=DocumentLivreur.TYPE_PIECE_IDENTITE,
            fichier_url_ou_reference='https://storage.ayyou.com/docs/cni.jpg'
        )

        serializer = ProfilLivreurSerializer(instance=profil)
        data = serializer.data

        self.assertEqual(data['id'], profil.id)
        self.assertEqual(data['statut_verification'], 'EN_ATTENTE')
        self.assertEqual(data['statut_verification_display'], 'En attente')
        self.assertEqual(data['type_vehicule'], 'MOTO')
        self.assertEqual(data['type_vehicule_display'], 'Moto')
        self.assertEqual(len(data['documents']), 1)
        self.assertEqual(data['documents'][0]['type_document'], 'PIECE_IDENTITE')
        self.assertEqual(data['documents'][0]['type_document_display'], "Pièce d'identité")
