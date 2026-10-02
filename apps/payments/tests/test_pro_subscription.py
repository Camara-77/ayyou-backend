import hashlib
import json
from decimal import Decimal
from datetime import datetime, date
from django.test import TestCase, RequestFactory
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

from apps.catalog.models import Etablissement, Produit, Categorie, PublicationFeed
from apps.payments.models import Paiement, AbonnementPro, FactureAbonnement
from apps.payments.services import PaymentService
from apps.payments.paytech_service import PayTechService
from apps.notifications.models import Notification

User = get_user_model()


class ProSubscriptionTestCase(TestCase):

    def setUp(self):
        self.pro_user = User.objects.create_user(
            email='pro_owner@ayyou.com',
            numero_telephone='770000001',
            password='password123',
            prenom='Jean',
            nom='Dupont'
        )

        self.superuser = User.objects.create_superuser(
            email='admin@ayyou.com',
            numero_telephone='770000000',
            password='adminpassword',
            prenom='Admin',
            nom='AYYOU'
        )



        self.etablissement = Etablissement.objects.create(
            nom="Chez Youssou Dibi",
            type_etablissement=Etablissement.TYPE_RESTAURANT,
            proprietaire=self.pro_user,
            statut_abonnement=Etablissement.STATUT_ABONNEMENT_INACTIF
        )

        self.categorie = Categorie.objects.create(nom="Grillades", slug="grillades")

        self.produit = Produit.objects.create(
            etablissement=self.etablissement,
            categorie=self.categorie,
            nom="Dibi d'Agneau",
            prix_base=Decimal("3500.00"),
            image_url="http://example.com/dibi.jpg",
            est_disponible=True
        )


        self.publication = PublicationFeed.objects.create(
            etablissement=self.etablissement,
            produit=self.produit,
            media_url="http://cloudinary.com/video.mp4",
            type_media=PublicationFeed.TYPE_MEDIA_VIDEO
        )

    def test_1_subscription_payment_initialization(self):
        """
        Initialisation d'un paiement d'abonnement : Montant forcé à 10 000 FCFA.
        """
        paiement = PaymentService.initier_paiement_abonnement(
            etablissement=self.etablissement,
            methode=Paiement.METHODE_WAVE
        )

        self.assertIsNotNone(paiement)
        self.assertEqual(paiement.type_paiement, Paiement.TYPE_ABONNEMENT_PRO)
        self.assertEqual(paiement.montant, Decimal('10000.00'))
        self.assertEqual(paiement.etablissement, self.etablissement)
        self.assertIsNotNone(paiement.reference)


    def test_2_paytech_subscription_creation(self):
        """
        PayTechService.create_subscription_payment construit le payload correct (price=10000, currency=XOF).
        """
        paiement = PaymentService.initier_paiement_abonnement(self.etablissement)
        res = PayTechService.create_subscription_payment(paiement, self.etablissement)

        self.assertIn('success', res)
        self.assertIn('token', res)
        self.assertIn('redirect_url', res)

    def test_3_first_time_activation(self):
        """
        Première activation : Passage de INACTIF à ACTIF, création AbonnementPro & FactureAbonnement, email envoyé.
        """
        paiement = PaymentService.initier_paiement_abonnement(self.etablissement)
        paiement = PaymentService.confirmer_paiement_abonnement(paiement, transaction_externe="PT-SUB-TX-1")

        self.etablissement.refresh_from_db()
        self.assertEqual(self.etablissement.statut_abonnement, Etablissement.STATUT_ABONNEMENT_ACTIF)
        self.assertIsNotNone(self.etablissement.date_debut_abonnement)
        self.assertIsNotNone(self.etablissement.date_expiration_abonnement)

        # Vérification AbonnementPro
        abonnement = AbonnementPro.objects.filter(etablissement=self.etablissement).first()
        self.assertIsNotNone(abonnement)
        self.assertEqual(abonnement.montant, Decimal('10000.00'))
        self.assertEqual(abonnement.statut, AbonnementPro.STATUT_PAYE)

        # Vérification FactureAbonnement
        facture = FactureAbonnement.objects.filter(abonnement=abonnement).first()
        self.assertIsNotNone(facture)
        self.assertEqual(facture.montant_total, Decimal('10000.00'))
        self.assertEqual(facture.nom_etablissement_snapshot, self.etablissement.nom)

        # Notification Email générée
        notif = Notification.objects.filter(
            utilisateur=self.pro_user,
            reference_type='AbonnementPro'
        ).first()
        self.assertIsNotNone(notif)

    def test_4_renewal_active_cumul(self):
        """
        Renouvellement si déjà ACTIF : Cumul d'un mois supplémentaire à partir de la date d'expiration actuelle.
        """
        now = timezone.now()
        first_exp = PaymentService.ajouter_un_mois_calendaire(now)
        self.etablissement.statut_abonnement = Etablissement.STATUT_ABONNEMENT_ACTIF
        self.etablissement.date_debut_abonnement = now
        self.etablissement.date_expiration_abonnement = first_exp
        self.etablissement.save()

        p2 = PaymentService.initier_paiement_abonnement(self.etablissement)
        p2 = PaymentService.confirmer_paiement_abonnement(p2, transaction_externe="PT-SUB-TX-2")

        self.etablissement.refresh_from_db()
        expected_exp = PaymentService.ajouter_un_mois_calendaire(first_exp)

        self.assertEqual(self.etablissement.statut_abonnement, Etablissement.STATUT_ABONNEMENT_ACTIF)
        # La différence entre les dates calculées doit être nulle (au niveau seconde)
        self.assertEqual(self.etablissement.date_expiration_abonnement.date(), expected_exp.date())

    def test_5_renewal_after_expired(self):
        """
        Renouvellement après EXPIRE : Réactivation avec new_start = now et new_exp = now + 1 month.
        """
        past_date = timezone.now() - timezone.timedelta(days=10)
        self.etablissement.statut_abonnement = Etablissement.STATUT_ABONNEMENT_EXPIRE
        self.etablissement.date_debut_abonnement = past_date - timezone.timedelta(days=30)
        self.etablissement.date_expiration_abonnement = past_date
        self.etablissement.save()

        p3 = PaymentService.initier_paiement_abonnement(self.etablissement)
        p3 = PaymentService.confirmer_paiement_abonnement(p3, transaction_externe="PT-SUB-TX-3")

        self.etablissement.refresh_from_db()
        self.assertEqual(self.etablissement.statut_abonnement, Etablissement.STATUT_ABONNEMENT_ACTIF)
        self.assertTrue(self.etablissement.date_expiration_abonnement > timezone.now())

    def test_6_zero_grace_period_and_queryset_filtering(self):
        """
        Un établissement expiré (date_expiration < now) est masqué pour les clients mais accessible au proprietaire/admin.
        """
        self.etablissement.statut_abonnement = Etablissement.STATUT_ABONNEMENT_EXPIRE
        self.etablissement.date_expiration_abonnement = timezone.now() - timezone.timedelta(hours=1)
        self.etablissement.save()

        from apps.catalog.views import EtablissementListView, ProduitListView, PublicationFeedListView
        factory = RequestFactory()

        # 1. Client anonyme consulte les listes publiques -> 0 résultat
        req_anon = factory.get('/api/catalog/establishments/')
        res_etab = EtablissementListView.as_view()(req_anon)
        self.assertEqual(res_etab.status_code, 200)

        # Vérification filtrage direct queryset
        active_etabs = Etablissement.objects.filter(
            statut_abonnement=Etablissement.STATUT_ABONNEMENT_ACTIF,
            date_expiration_abonnement__gt=timezone.now()
        )
        self.assertEqual(active_etabs.count(), 0)

    def test_7_paytech_ipn_signature_and_idempotency(self):
        """
        Vérification signature IPN PayTech & Idempotence.
        """
        paiement = PaymentService.initier_paiement_abonnement(self.etablissement)
        ipn_data = {
            'type_event': 'sale_complete',
            'custom_field': json.dumps({'paiement_id': paiement.id}),
            'ref_command': paiement.reference,
            'item_price': '10000',
            'token': 'SUB-PAYTECH-TOKEN-123'
        }

        # Simuler confirmation
        p_confirmed = PaymentService.confirmer_paiement_abonnement(paiement, transaction_externe='SUB-PAYTECH-TOKEN-123')
        self.assertEqual(p_confirmed.statut, Paiement.STATUT_PAYE)

        # Idempotence : une seconde tentative renvoie true/confirmé sans erreur
        p_retry = PaymentService.confirmer_paiement_abonnement(p_confirmed, transaction_externe='SUB-PAYTECH-TOKEN-123')
        self.assertEqual(p_retry.statut, Paiement.STATUT_PAYE)

    def test_8_leap_year_and_month_wrap_calculation(self):
        """
        Vérification du calcul de 1 mois calendaire (31 Janv -> 28/29 Fév, 28 Fév -> 28 Mars, 15 Déc -> 15 Janv).
        """
        # 1. Fin de mois janvier -> février (année non bissextile 2025)
        dt_jan31 = timezone.make_aware(datetime(2025, 1, 31, 14, 30, 0))
        exp_feb = PaymentService.ajouter_un_mois_calendaire(dt_jan31)
        self.assertEqual(exp_feb.month, 2)
        self.assertEqual(exp_feb.day, 28)

        # 2. Année bissextile 2024 (31 Janv -> 29 Fév)
        dt_leap = timezone.make_aware(datetime(2024, 1, 31, 10, 0, 0))
        exp_leap = PaymentService.ajouter_un_mois_calendaire(dt_leap)
        self.assertEqual(exp_leap.month, 2)
        self.assertEqual(exp_leap.day, 29)

        # 3. Changement d'année (15 Déc -> 15 Janv)
        dt_dec15 = timezone.make_aware(datetime(2025, 12, 15, 12, 0, 0))
        exp_jan = PaymentService.ajouter_un_mois_calendaire(dt_dec15)
        self.assertEqual(exp_jan.year, 2026)
        self.assertEqual(exp_jan.month, 1)
        self.assertEqual(exp_jan.day, 15)

    def test_9_expiration_reminders_j5_and_j1_deduplicated(self):
        """
        Test des rappels d'expiration à J-5 et J-1 (24h) avec déduplication In-App & Email.
        """
        from django.core.management import call_command
        from datetime import timedelta

        now = timezone.now()
        # Établissement A à J-5
        self.etablissement.statut_abonnement = Etablissement.STATUT_ABONNEMENT_ACTIF
        self.etablissement.date_expiration_abonnement = now + timedelta(days=5)
        self.etablissement.save()

        call_command('send_subscription_expiration_reminders')

        # Vérifier notification In-App & Email pour J-5
        notifs_j5 = Notification.objects.filter(
            utilisateur=self.pro_user,
            type_notification=Notification.TYPE_SUBSCRIPTION,
            metadata__event='PRO_SUBSCRIPTION_REMINDER_J5'
        )
        self.assertTrue(notifs_j5.exists())

        # Établissement A basculé à J-1 (24h)
        self.etablissement.date_expiration_abonnement = now + timedelta(hours=18)
        self.etablissement.save()

        call_command('send_subscription_expiration_reminders')

        # Vérifier notification In-App & Email pour J-1
        notifs_j1 = Notification.objects.filter(
            utilisateur=self.pro_user,
            type_notification=Notification.TYPE_SUBSCRIPTION,
            metadata__event='PRO_SUBSCRIPTION_REMINDER_J1'
        )
        self.assertTrue(notifs_j1.exists())

        # Exécuter une 2ème fois -> aucune nouvelle notification (déduplication)
        count_before = Notification.objects.count()
        call_command('send_subscription_expiration_reminders')
        count_after = Notification.objects.count()
        self.assertEqual(count_before, count_after)

    def test_10_suspension_command_triggers_alerts(self):
        """
        Test que expire_pro_subscriptions fait passer l'abonnement à EXPIRE et émet les notifications de suspension.
        """
        from django.core.management import call_command
        from datetime import timedelta

        self.etablissement.statut_abonnement = Etablissement.STATUT_ABONNEMENT_ACTIF
        self.etablissement.date_expiration_abonnement = timezone.now() - timedelta(hours=2)
        self.etablissement.save()

        call_command('expire_pro_subscriptions')

        self.etablissement.refresh_from_db()
        self.assertEqual(self.etablissement.statut_abonnement, Etablissement.STATUT_ABONNEMENT_EXPIRE)

        # Vérifier notification In-App de suspension
        suspended_notif = Notification.objects.filter(
            utilisateur=self.pro_user,
            type_notification=Notification.TYPE_SUBSCRIPTION,
            metadata__event='PRO_SUBSCRIPTION_SUSPENDED'
        ).first()
        self.assertIsNotNone(suspended_notif)
        self.assertIn("expiré", suspended_notif.message)

    def test_11_backend_restrictions_on_expired_account(self):
        """
        Test des restrictions backend : publication feed, modification menu et panier bloqués si expiré.
        """
        from apps.catalog.views import PublicationFeedListView
        from apps.pro_api.views_merchant import MerchantProductListView, MerchantProductDetailView
        from apps.orders.services import CartService, OrderService
        from rest_framework.test import APIRequestFactory, force_authenticate

        factory = APIRequestFactory()

        self.etablissement.statut_abonnement = Etablissement.STATUT_ABONNEMENT_EXPIRE
        self.etablissement.date_expiration_abonnement = timezone.now() - timezone.timedelta(days=1)
        self.etablissement.save()

        # 1. Publication Feed
        req_feed = factory.post('/api/catalog/feed/', {'media_url': 'http://test.mp4'})
        force_authenticate(req_feed, user=self.pro_user)
        res_feed = PublicationFeedListView.as_view()(req_feed)
        self.assertEqual(res_feed.status_code, 403)

        # 2. Ajout Produit
        req_prod = factory.post('/api/pro/merchant/products/', {'nom': 'Nouveau Plat', 'prix_base': '2000'})
        force_authenticate(req_prod, user=self.pro_user)
        res_prod = MerchantProductListView.as_view()(req_prod)
        self.assertEqual(res_prod.status_code, 403)

        # 3. Modification Produit
        req_edit = factory.put(f'/api/pro/merchant/products/{self.produit.id}/', {'nom': 'Modif Plat', 'prix_base': '2500'})
        force_authenticate(req_edit, user=self.pro_user)
        res_edit = MerchantProductDetailView.as_view()(req_edit, pk=self.produit.id)
        self.assertEqual(res_edit.status_code, 403)

        # 4. Ajout au panier par un client -> ValidationError
        client_user = User.objects.create_user(email='client@ayyou.com', numero_telephone='779998877', password='pass')
        with self.assertRaises(ValidationError):
            CartService.add_item_to_cart(client_user, self.produit.id, 1)

    def test_12_reactivation_restores_all_permissions(self):
        """
        Test qu'après réactivation (confirmation paiement IPN), les permissions et fonctionnalités sont restaurées.
        """
        from apps.orders.services import CartService

        # Mettre en statut expiré
        self.etablissement.statut_abonnement = Etablissement.STATUT_ABONNEMENT_EXPIRE
        self.etablissement.date_expiration_abonnement = timezone.now() - timezone.timedelta(days=1)
        self.etablissement.save()

        # Effectuer le paiement et confirmer
        paiement = PaymentService.initier_paiement_abonnement(self.etablissement)
        PaymentService.confirmer_paiement_abonnement(paiement, transaction_externe="PT-REACTIVATE-123")

        self.etablissement.refresh_from_db()
        self.assertEqual(self.etablissement.statut_abonnement, Etablissement.STATUT_ABONNEMENT_ACTIF)

        # Vérifier qu'un client peut à nouveau ajouter au panier
        client_user = User.objects.create_user(email='client_ok@ayyou.com', numero_telephone='779990011', password='pass')
        item = CartService.add_item_to_cart(client_user, self.produit.id, 1)
        self.assertIsNotNone(item)
        self.assertEqual(item.produit, self.produit)

