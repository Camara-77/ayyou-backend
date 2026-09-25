from unittest.mock import patch
from django.test import TestCase, override_settings, TransactionTestCase
from django.core import mail
from django.conf import settings
from django.db import transaction

from apps.users.models import Utilisateur
from apps.notifications.models import Notification
from apps.notifications.services import NotificationService
from apps.notifications.email_service import EmailNotificationService
from apps.notifications.dispatcher import NotificationDispatcher


class EmailNotificationServiceTestCase(TestCase):
    """
    Suite de tests unitaires et d'intégration pour le service d'emails transactionnels (Phase 13.6.C).
    """

    def setUp(self):
        self.user = Utilisateur.objects.create_user(
            email='test_email_user@ayyou.com',
            numero_telephone='+221 77 900 11 22',
            password='Password123!',
            prenom='Jean',
            nom='Dupont'
        )

    def test_1_configuration_email(self):
        """1. Vérification de la configuration des variables d'environnement email."""
        self.assertTrue(hasattr(settings, 'EMAIL_BACKEND'))
        self.assertTrue(hasattr(settings, 'DEFAULT_FROM_EMAIL'))
        self.assertIsNotNone(settings.DEFAULT_FROM_EMAIL)

    def test_2_creation_notification_email(self):
        """2. Création d'une Notification de canal EMAIL."""
        notif = NotificationService.creer_notification(
            utilisateur=self.user,
            titre="Confirmation de Commande",
            message="Votre commande #AYY-101 a été reçue.",
            type_notification=Notification.TYPE_ORDER,
            canal=Notification.CANAL_EMAIL,
            reference_type="Commande",
            reference_id="AYY-101",
            statut=Notification.STATUT_EN_ATTENTE
        )
        self.assertEqual(notif.canal, Notification.CANAL_EMAIL)
        self.assertEqual(notif.statut, Notification.STATUT_EN_ATTENTE)
        self.assertEqual(notif.utilisateur, self.user)

    def test_3_recuperation_destinataire(self):
        """3. Extraction du destinataire email depuis l'utilisateur lié."""
        notif = NotificationService.creer_notification(
            utilisateur=self.user,
            titre="Test Destinataire",
            message="Contenu",
            canal=Notification.CANAL_EMAIL
        )
        self.assertEqual(notif.utilisateur.email, 'test_email_user@ayyou.com')

    def test_4_generation_sujet(self):
        """4. Génération correcte du sujet de l'email à partir du titre de la notification."""
        notif = NotificationService.creer_notification(
            utilisateur=self.user,
            titre="Votre compte PRO a été validé !",
            message="Bienvenue sur AYYOU PRO.",
            type_notification=Notification.TYPE_PRO_VALIDATION,
            canal=Notification.CANAL_EMAIL
        )
        success = EmailNotificationService.envoyer_email_notification(notif)
        self.assertTrue(success)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].subject, "Votre compte PRO a été validé !")

    def test_5_generation_html(self):
        """5. Rendu du template HTML de notification."""
        notif = NotificationService.creer_notification(
            utilisateur=self.user,
            titre="Nouveau plat au catalogue",
            message="Découvrez le Thiéboudienne de chez Loutcha.",
            type_notification=Notification.TYPE_SYSTEM,
            canal=Notification.CANAL_EMAIL,
            reference_type="Produit",
            reference_id="45"
        )
        success = EmailNotificationService.envoyer_email_notification(notif)
        self.assertTrue(success)
        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]
        self.assertEqual(len(email.alternatives), 1)
        html_body, mime_type = email.alternatives[0]
        self.assertEqual(mime_type, "text/html")
        self.assertIn("Nouveau plat au catalogue", html_body)
        self.assertIn("Découvrez le Thiéboudienne de chez Loutcha.", html_body)
        self.assertIn("Produit #45", html_body)
        self.assertIn("Jean Dupont", html_body)

    def test_6_generation_texte(self):
        """6. Rendu du fallback texte brut de l'email."""
        notif = NotificationService.creer_notification(
            utilisateur=self.user,
            titre="Alerte Système",
            message="Maintenance programmée à 02h00.",
            type_notification=Notification.TYPE_SYSTEM,
            canal=Notification.CANAL_EMAIL
        )
        success = EmailNotificationService.envoyer_email_notification(notif)
        self.assertTrue(success)
        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]
        self.assertIn("Alerte Système", email.body)
        self.assertIn("Maintenance programmée à 02h00.", email.body)
        self.assertIn("Jean Dupont", email.body)

    def test_7_appel_service_email(self):
        """7. Appel direct du service email `EmailNotificationService.envoyer_email_notification`."""
        notif = NotificationService.creer_notification(
            utilisateur=self.user,
            titre="Test Service Direct",
            message="Message de test direct.",
            canal=Notification.CANAL_EMAIL,
            statut=Notification.STATUT_EN_ATTENTE
        )
        res = EmailNotificationService.envoyer_email_notification(notif)
        self.assertTrue(res)
        notif.refresh_from_db()
        self.assertEqual(notif.statut, Notification.STATUT_ENVOYEE)

    def test_8_email_envoye_backend_test(self):
        """8. Validation complète de l'envoi d'email avec le backend locmem."""
        notif = NotificationService.creer_notification(
            utilisateur=self.user,
            titre="Livraison attribuée",
            message="Un livreur est en route.",
            type_notification=Notification.TYPE_DELIVERY,
            canal=Notification.CANAL_EMAIL,
            reference_type="Livraison",
            reference_id="999"
        )
        self.assertEqual(len(mail.outbox), 0)
        EmailNotificationService.envoyer_email_notification(notif)

        self.assertEqual(len(mail.outbox), 1)
        sent_email = mail.outbox[0]
        self.assertEqual(sent_email.to, ['test_email_user@ayyou.com'])
        self.assertEqual(sent_email.from_email, settings.DEFAULT_FROM_EMAIL)
        self.assertEqual(sent_email.subject, "Livraison attribuée")

    def test_9_erreur_envoi_geree(self):
        """9. Gestion propre des erreurs lors de l'envoi (destinataire sans email ou exception)."""
        # A. Destinataire sans email valide
        user_sans_email = Utilisateur.objects.create_user(
            email='temp_sans_email@ayyou.com',
            numero_telephone='+221 77 900 33 44',
            password='Password123!',
            prenom='Sans',
            nom='Email'
        )
        Utilisateur.objects.filter(id=user_sans_email.id).update(email='')
        user_sans_email.refresh_from_db()

        notif_sans_email = NotificationService.creer_notification(
            utilisateur=user_sans_email,
            titre="Titre",
            message="Message",
            canal=Notification.CANAL_EMAIL,
            statut=Notification.STATUT_EN_ATTENTE
        )
        res_a = EmailNotificationService.envoyer_email_notification(notif_sans_email)
        self.assertFalse(res_a)
        notif_sans_email.refresh_from_db()
        self.assertEqual(notif_sans_email.statut, Notification.STATUT_ECHEC)

        # B. Exception d'envoi SMTP simulée
        notif_avec_erreur = NotificationService.creer_notification(
            utilisateur=self.user,
            titre="Erreur SMTP",
            message="Contenu",
            canal=Notification.CANAL_EMAIL,
            statut=Notification.STATUT_EN_ATTENTE
        )
        with patch('django.core.mail.EmailMultiAlternatives.send', side_effect=Exception("Erreur de connexion SMTP (Timeout)")):
            res_b = EmailNotificationService.envoyer_email_notification(notif_avec_erreur)
            self.assertFalse(res_b)
            notif_avec_erreur.refresh_from_db()
            self.assertEqual(notif_avec_erreur.statut, Notification.STATUT_ECHEC)

    def test_10_securite_absence_secret_logs(self):
        """10. Garantir l'absence de mot de passe, token JWT ou credential sensible dans l'email et les logs."""
        notif = NotificationService.creer_notification(
            utilisateur=self.user,
            titre="Notification Sécurisée",
            message="Aucun secret ne doit fuiter.",
            canal=Notification.CANAL_EMAIL
        )
        EmailNotificationService.envoyer_email_notification(notif)
        sent_email = mail.outbox[0]
        html_body = sent_email.alternatives[0][0]

        # Vérification qu'aucun token ou password par défaut ne figure dans l'email
        self.assertNotIn("Password123!", sent_email.body)
        self.assertNotIn("Password123!", html_body)
        self.assertNotIn("SECRET_KEY", sent_email.body)
        self.assertNotIn("JWT", sent_email.body)

    def test_11_notification_in_app_ignoree_par_email_service(self):
        """11. Les notifications de canal IN_APP ne sont pas envoyées par EmailNotificationService."""
        notif_in_app = NotificationService.creer_notification(
            utilisateur=self.user,
            titre="In App Notif",
            message="Contenu",
            canal=Notification.CANAL_IN_APP
        )
        res = EmailNotificationService.envoyer_email_notification(notif_in_app)
        self.assertFalse(res)
        self.assertEqual(len(mail.outbox), 0)

    def test_12_notification_whatsapp_ignoree_par_email_service(self):
        """12. Les notifications de canal WHATSAPP ne sont pas envoyées par EmailNotificationService."""
        notif_whatsapp = NotificationService.creer_notification(
            utilisateur=self.user,
            titre="WhatsApp Notif",
            message="Contenu",
            canal=Notification.CANAL_WHATSAPP
        )
        res = EmailNotificationService.envoyer_email_notification(notif_whatsapp)
        self.assertFalse(res)
        self.assertEqual(len(mail.outbox), 0)

    def test_13_integration_dispatcher_email(self):
        """13. Intégration complète : NotificationDispatcher -> EmailNotificationService."""
        with self.captureOnCommitCallbacks(execute=True):
            notif = NotificationDispatcher.dispatch_event(
                event_type=Notification.TYPE_ORDER,
                destinataire=self.user,
                titre="Nouvelle Commande #AYY-505",
                message="Une commande a été passée.",
                canal=Notification.CANAL_EMAIL,
                reference_type="Commande",
                reference_id="AYY-505"
            )
        self.assertEqual(notif.canal, Notification.CANAL_EMAIL)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ['test_email_user@ayyou.com'])
        self.assertEqual(mail.outbox[0].subject, "Nouvelle Commande #AYY-505")
        notif.refresh_from_db()
        self.assertEqual(notif.statut, Notification.STATUT_ENVOYEE)


class EmailTransactionOnCommitTestCase(TransactionTestCase):
    """
    Test spécifique pour la compatibilité avec transaction.on_commit().
    """

    def setUp(self):
        self.user = Utilisateur.objects.create_user(
            email='commit_user@ayyou.com',
            numero_telephone='+221 77 900 55 66',
            password='Password123!',
            prenom='Commit',
            nom='Test'
        )

    def test_14_compatibilite_transaction_on_commit(self):
        """14. Vérification que l'email n'est envoyé qu'après le commit effectif de la transaction SQL."""
        mail.outbox = []

        with transaction.atomic():
            notif = NotificationDispatcher.dispatch_event(
                event_type=Notification.TYPE_SYSTEM,
                destinataire=self.user,
                titre="Test On Commit",
                message="Avis de mise à jour.",
                canal=Notification.CANAL_EMAIL
            )
            # Durant la transaction (avant le commit), l'email ne doit pas encore être dans la boîte d'envoi locmem
            self.assertEqual(len(mail.outbox), 0)

        # Après le bloc atomic() (commit réussi), l'email a été expédié
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].subject, "Test On Commit")
        notif.refresh_from_db()
        self.assertEqual(notif.statut, Notification.STATUT_ENVOYEE)
