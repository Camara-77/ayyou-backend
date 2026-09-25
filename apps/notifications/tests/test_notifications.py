from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status

from apps.users.models import Utilisateur
from apps.notifications.models import Notification
from apps.notifications.services import NotificationService
from apps.notifications.dispatcher import NotificationDispatcher


class NotificationBackendTestCase(TestCase):
    """
    Suite de tests unitaires et d'intégration pour l'architecture Notification Backend (Phase 13.6.A).
    """

    def setUp(self):
        self.user_a = Utilisateur.objects.create_user(
            email='user_a@ayyou.com',
            numero_telephone='+221 77 100 00 01',
            password='Password123!',
            prenom='User',
            nom='A'
        )

        self.user_b = Utilisateur.objects.create_user(
            email='user_b@ayyou.com',
            numero_telephone='+221 77 100 00 02',
            password='Password123!',
            prenom='User',
            nom='B'
        )

        self.client_a = APIClient()
        self.client_a.force_authenticate(user=self.user_a)

        self.client_b = APIClient()
        self.client_b.force_authenticate(user=self.user_b)

        self.unauthenticated_client = APIClient()

    def test_1_creer_notification(self):
        """1. Création d'une notification via NotificationService."""
        notif = NotificationService.creer_notification(
            utilisateur=self.user_a,
            titre="Bienvenue sur AYYOU",
            message="Votre compte a été créé avec succès.",
            type_notification=Notification.TYPE_AUTHENTICATION,
            canal=Notification.CANAL_IN_APP
        )
        self.assertIsNotNone(notif.id)
        self.assertEqual(notif.utilisateur, self.user_a)
        self.assertEqual(notif.titre, "Bienvenue sur AYYOU")
        self.assertFalse(notif.est_lu)
        self.assertEqual(notif.statut, Notification.STATUT_ENVOYEE)

    def test_2_recuperation_par_destinataire(self):
        """2. Récupération des notifications par le destinataire authentifié."""
        NotificationService.creer_notification(
            utilisateur=self.user_a,
            titre="Notif User A",
            message="Message A"
        )
        url = reverse('notifications:notification-list')
        response = self.client_a.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data['results'] if 'results' in response.data else response.data
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['titre'], "Notif User A")

    def test_3_isolation_entre_utilisateurs(self):
        """3. Isolation stricte : User B ne peut ni voir ni modifier les notifications de User A."""
        notif_a = NotificationService.creer_notification(
            utilisateur=self.user_a,
            titre="Confidentiel A",
            message="Message confidentiel A"
        )

        # User B consulte sa liste
        url_list = reverse('notifications:notification-list')
        response_b = self.client_b.get(url_list)
        results_b = response_b.data['results'] if 'results' in response_b.data else response_b.data
        self.assertEqual(len(results_b), 0)

        # User B tente d'accéder au détail de la notif de User A
        url_detail = reverse('notifications:notification-detail', kwargs={'pk': notif_a.id})
        response_detail_b = self.client_b.get(url_detail)
        self.assertEqual(response_detail_b.status_code, status.HTTP_404_NOT_FOUND)

        # User B tente de marquer comme lue la notif de User A
        url_read_b = reverse('notifications:notification-mark-as-read', kwargs={'pk': notif_a.id})
        response_read_b = self.client_b.post(url_read_b)
        self.assertEqual(response_read_b.status_code, status.HTTP_404_NOT_FOUND)

        # La notif de User A doit rester non lue
        notif_a.refresh_from_db()
        self.assertFalse(notif_a.est_lu)

    def test_4_compteur_non_lu(self):
        """4. Vérification du compteur de notifications non lues."""
        NotificationService.creer_notification(self.user_a, "Titre 1", "Message 1")
        NotificationService.creer_notification(self.user_a, "Titre 2", "Message 2")

        url_unread = reverse('notifications:notification-unread-count')
        response = self.client_a.get(url_unread)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['unread_count'], 2)

    def test_5_marquer_comme_lu(self):
        """5. Marquage d'une notification comme lue via l'API REST."""
        notif = NotificationService.creer_notification(self.user_a, "Commande Prête", "Votre plat est prêt")
        self.assertFalse(notif.est_lu)

        url_read = reverse('notifications:notification-mark-as-read', kwargs={'pk': notif.id})
        response = self.client_a.post(url_read)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['est_lu'])
        self.assertEqual(response.data['statut'], Notification.STATUT_LU)

        notif.refresh_from_db()
        self.assertTrue(notif.est_lu)
        self.assertIsNotNone(notif.date_lecture)

    def test_6_notification_deja_lue(self):
        """6. Idempotence lorsqu'une notification déjà lue est marquée à nouveau."""
        notif = NotificationService.creer_notification(self.user_a, "Promo", "Contenu")
        NotificationService.marquer_comme_lue(notif.id, self.user_a)
        notif.refresh_from_db()
        first_read_date = notif.date_lecture

        url_read = reverse('notifications:notification-mark-as-read', kwargs={'pk': notif.id})
        response = self.client_a.post(url_read)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        notif.refresh_from_db()
        self.assertTrue(notif.est_lu)
        self.assertEqual(notif.date_lecture, first_read_date)

    def test_7_utilisateur_non_authentifie(self):
        """7. Refus d'accès (HTTP 401) pour un utilisateur anonyme non connecté."""
        url_list = reverse('notifications:notification-list')
        response = self.unauthenticated_client.get(url_list)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_8_notification_avec_reference_metier(self):
        """8. Notification associée à une référence métier (ex: Commande)."""
        notif = NotificationService.creer_notification(
            utilisateur=self.user_a,
            titre="Mise à jour commande",
            message="Votre commande est en préparation",
            type_notification=Notification.TYPE_ORDER,
            reference_type="Commande",
            reference_id="AYY-20260919-X88",
            metadata={"etablissement_nom": "Chez Loutcha"}
        )
        self.assertEqual(notif.reference_type, "Commande")
        self.assertEqual(notif.reference_id, "AYY-20260919-X88")
        self.assertEqual(notif.metadata.get("etablissement_nom"), "Chez Loutcha")

    def test_9_statut_initial_correct(self):
        """9. Validation des statuts verticaux par défaut."""
        notif = NotificationService.creer_notification(
            utilisateur=self.user_a,
            titre="Test Statut",
            message="Contenu statut"
        )
        self.assertEqual(notif.statut, Notification.STATUT_ENVOYEE)
        self.assertFalse(notif.est_lu)
        self.assertIsNone(notif.date_lecture)

    def test_10_type_et_canal_valides(self):
        """10. Validation du dispatcher et des choix de type et de canal."""
        notif = NotificationDispatcher.dispatch_event(
            event_type=Notification.TYPE_DELIVERY,
            destinataire=self.user_a,
            titre="Livreur en route",
            message="Votre livreur arrive dans 5 min",
            canal=Notification.CANAL_IN_APP,
            reference_type="Livraison",
            reference_id="101"
        )
        self.assertEqual(notif.type_notification, Notification.TYPE_DELIVERY)
        self.assertEqual(notif.canal, Notification.CANAL_IN_APP)
        self.assertEqual(notif.reference_type, "Livraison")
        self.assertEqual(notif.reference_id, "101")

    def test_11_marquer_tout_comme_lu(self):
        """11. Action bulk : marquer toutes les notifications d'un utilisateur comme lues."""
        NotificationService.creer_notification(self.user_a, "N1", "M1")
        NotificationService.creer_notification(self.user_a, "N2", "M2")

        url_mark_all = reverse('notifications:notification-mark-all-as-read')
        response = self.client_a.post(url_mark_all)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['updated_count'], 2)
        self.assertEqual(NotificationService.get_nombre_non_lues(self.user_a), 0)
