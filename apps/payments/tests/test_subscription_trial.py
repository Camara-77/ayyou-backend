from django.test import TestCase
from django.utils import timezone
from datetime import timedelta
from apps.users.models import Utilisateur, Role, UtilisateurRole
from apps.catalog.models import Etablissement
from apps.payments.models import Paiement, AbonnementPro
from apps.payments.services import PaymentService
from apps.pro_api.serializers import RestaurantRegistrationSerializer, VendeurRegistrationSerializer


class SubscriptionTrialTestCase(TestCase):
    def setUp(self):
        self.role_resto, _ = Role.objects.get_or_create(nom=Role.RESTAURANT)
        self.role_vendeur, _ = Role.objects.get_or_create(nom=Role.VENDEUR)

    def test_1_nouveau_restaurant_inscription_essai_gratuit(self):
        """Test 1: Un nouveau Restaurant bénéficie d'un essai gratuit de 1 mois actif dès l'inscription."""
        data = {
            'email': 'resto.new@ayyou.test',
            'numero_telephone': '+221770000001',
            'password': 'Password123!',
            'password_confirm': 'Password123!',
            'prenom': 'Jean',
            'nom': 'Ndiaye',
            'nom_etablissement': 'Resto New Dakar',
            'adresse': 'Plateau, Dakar'
        }
        serializer = RestaurantRegistrationSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        res = serializer.save()

        etab = res['etablissement']
        self.assertEqual(etab.type_etablissement, Etablissement.TYPE_RESTAURANT)
        self.assertEqual(etab.statut_abonnement, Etablissement.STATUT_ABONNEMENT_ACTIF)
        self.assertIsNotNone(etab.date_debut_abonnement)
        self.assertIsNotNone(etab.date_expiration_abonnement)
        # Vérification 1 mois calendaire
        diff = etab.date_expiration_abonnement - etab.date_debut_abonnement
        self.assertTrue(28 <= diff.days <= 31)

    def test_2_nouveau_vendeur_inscription_essai_gratuit(self):
        """Test 2: Un nouveau Vendeur bénéficie également d'un essai gratuit de 1 mois actif dès l'inscription."""
        data = {
            'email': 'vendeur.new@ayyou.test',
            'numero_telephone': '+221770000002',
            'password': 'Password123!',
            'password_confirm': 'Password123!',
            'prenom': 'Fatou',
            'nom': 'Sow',
            'nom_etablissement': 'Vendeur Kaffrine',
            'adresse': 'Almadies, Dakar'
        }
        serializer = VendeurRegistrationSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        res = serializer.save()

        etab = res['etablissement']
        self.assertEqual(etab.type_etablissement, Etablissement.TYPE_VENDEUR)
        self.assertEqual(etab.statut_abonnement, Etablissement.STATUT_ABONNEMENT_ACTIF)
        self.assertIsNotNone(etab.date_debut_abonnement)
        self.assertIsNotNone(etab.date_expiration_abonnement)

    def test_3_restaurant_acces_pendant_premier_mois(self):
        """Test 3: Pendant le 1er mois, l'accès plateforme est actif."""
        user = Utilisateur.objects.create_user(
            email='resto.active@ayyou.test',
            numero_telephone='+221770000003',
            password='Password123!'
        )
        etab = Etablissement.objects.create(
            nom="Resto Active Test",
            type_etablissement=Etablissement.TYPE_RESTAURANT,
            proprietaire=user,
            adresse="Dakar",
            statut_verification=Etablissement.STATUT_VALIDE
        )
        self.assertEqual(etab.statut_abonnement, Etablissement.STATUT_ABONNEMENT_ACTIF)
        self.assertTrue(etab.date_expiration_abonnement > timezone.now())

    def test_4_restaurant_apres_expiration(self):
        """Test 4: Après expiration du 1er mois, la commande de bascule expire le statut."""
        user = Utilisateur.objects.create_user(
            email='resto.expired@ayyou.test',
            numero_telephone='+221770000004',
            password='Password123!'
        )
        past_date = timezone.now() - timedelta(days=35)
        etab = Etablissement.objects.create(
            nom="Resto Expired Test",
            type_etablissement=Etablissement.TYPE_RESTAURANT,
            proprietaire=user,
            adresse="Dakar",
            statut_verification=Etablissement.STATUT_VALIDE,
            statut_abonnement=Etablissement.STATUT_ABONNEMENT_ACTIF,
            date_debut_abonnement=past_date - timedelta(days=30),
            date_expiration_abonnement=past_date
        )

        from apps.catalog.management.commands.expire_pro_subscriptions import Command as ExpireCommand
        cmd = ExpireCommand()
        cmd.handle()

        etab.refresh_from_db()
        self.assertEqual(etab.statut_abonnement, Etablissement.STATUT_ABONNEMENT_EXPIRE)

    def test_5_vendeur_apres_expiration(self):
        """Test 5: Vendeur expiré bascule également en statut EXPIRE après expiration."""
        user = Utilisateur.objects.create_user(
            email='vendeur.expired@ayyou.test',
            numero_telephone='+221770000005',
            password='Password123!'
        )
        past_date = timezone.now() - timedelta(days=40)
        etab = Etablissement.objects.create(
            nom="Vendeur Expired Test",
            type_etablissement=Etablissement.TYPE_VENDEUR,
            proprietaire=user,
            adresse="Dakar",
            statut_verification=Etablissement.STATUT_VALIDE,
            statut_abonnement=Etablissement.STATUT_ABONNEMENT_ACTIF,
            date_debut_abonnement=past_date - timedelta(days=30),
            date_expiration_abonnement=past_date
        )

        from apps.catalog.management.commands.expire_pro_subscriptions import Command as ExpireCommand
        cmd = ExpireCommand()
        cmd.handle()

        etab.refresh_from_db()
        self.assertEqual(etab.statut_abonnement, Etablissement.STATUT_ABONNEMENT_EXPIRE)

    def test_6_restaurant_deja_abonne_pas_de_nouvel_essai(self):
        """Test 6: Sauvegarder un établissement existant ne réinitialise pas la période d'essai."""
        user = Utilisateur.objects.create_user(
            email='resto.existing@ayyou.test',
            numero_telephone='+221770000006',
            password='Password123!'
        )
        now = timezone.now()
        etab = Etablissement.objects.create(
            nom="Resto Existing Test",
            type_etablissement=Etablissement.TYPE_RESTAURANT,
            proprietaire=user,
            adresse="Dakar"
        )
        exp_initiale = etab.date_expiration_abonnement

        # Modification du nom et save
        etab.nom = "Resto Existing Test Updated"
        etab.save()

        etab.refresh_from_db()
        self.assertEqual(etab.date_expiration_abonnement, exp_initiale)

    def test_7_restaurant_de_test_valide_et_actif(self):
        """Test 7: Le compte restaurant de test est actif, validé et a son essai gratuit."""
        from django.core.management import call_command
        call_command('setup_test_restaurant')

        user = Utilisateur.objects.get(email='restaurant.test@ayyou.test')
        self.assertTrue(user.check_password('AyyouTest@2026'))

        etab = Etablissement.objects.get(proprietaire=user)
        self.assertEqual(etab.statut_verification, Etablissement.STATUT_VALIDE)
        self.assertEqual(etab.statut_abonnement, Etablissement.STATUT_ABONNEMENT_ACTIF)
        self.assertTrue(etab.date_expiration_abonnement > timezone.now())

    def test_8_paiement_renouvellement_paytech(self):
        """Test 8: Le paiement PayTech d'abonnement pro (10 000 FCFA) prolonge la période de 1 mois."""
        user = Utilisateur.objects.create_user(
            email='resto.paytech@ayyou.test',
            numero_telephone='+221770000008',
            password='Password123!'
        )
        etab = Etablissement.objects.create(
            nom="Resto PayTech Test",
            type_etablissement=Etablissement.TYPE_RESTAURANT,
            proprietaire=user,
            adresse="Dakar",
            statut_verification=Etablissement.STATUT_VALIDE
        )

        paiement = PaymentService.initier_paiement_abonnement(etab)
        self.assertEqual(paiement.montant, 10000)

        # Confirmation du paiement
        paiement_confirme = PaymentService.confirmer_paiement_abonnement(paiement, transaction_externe="PAYTECH-TX-TEST")

        self.assertEqual(paiement_confirme.statut, Paiement.STATUT_PAYE)
        etab.refresh_from_db()
        self.assertEqual(etab.statut_abonnement, Etablissement.STATUT_ABONNEMENT_ACTIF)

        # Vérifier l'existence d'AbonnementPro
        abonnement = AbonnementPro.objects.filter(etablissement=etab).first()
        self.assertIsNotNone(abonnement)
        self.assertEqual(abonnement.montant, 10000)
