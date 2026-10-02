import os
from datetime import datetime, timedelta
from django.test import TestCase
from django.utils import timezone

from apps.users.models import Utilisateur
from apps.catalog.models import PublicationFeed, Produit, Etablissement, Categorie
from apps.telemetry.models import VideoEventLog
from apps.telemetry.data_preparation import FeatureExtractor, DatasetBuilder


class TemporalLeakageTestCase(TestCase):
    """
    Tests de validation anti-fuite temporelle (Anti-Temporal Leakage).
    Vérifie qu'aucun événement futur ou contemporain (>= T) n'influence
    les caractéristiques historiques calculées pour un événement cible à l'instant T.
    """

    @classmethod
    def setUpTestData(cls):
        # Catalogue minimal pour les tests
        cls.cat = Categorie.objects.create(nom="Fast Food Sénégal", slug="fast-food-sn")
        cls.etablissement = Etablissement.objects.create(
            nom="Dakar Burger",
            adresse="Fann Hock Dakar",
            telephone="+221770001122"
        )
        cls.produit = Produit.objects.create(
            nom="Burger Chawarma",
            prix_base=2000.00,
            etablissement=cls.etablissement,
            categorie=cls.cat
        )
        cls.publication = PublicationFeed.objects.create(
            etablissement=cls.etablissement,
            produit=cls.produit,
            media_url="https://example.com/burger.mp4"
        )

        # Utilisateur de test authentifié
        cls.user = Utilisateur.objects.create(
            email="leakage_test@ayyou.sn",
            nom="Leakage",
            prenom="User",
            numero_telephone="+221770009988"
        )

    def _create_event(self, utilisateur, publication, session_id, event_type, watch_time_seconds, created_at):
        evt = VideoEventLog.objects.create(
            utilisateur=utilisateur,
            publication=publication,
            session_id=session_id,
            event_type=event_type,
            watch_time_seconds=watch_time_seconds
        )
        VideoEventLog.objects.filter(pk=evt.pk).update(created_at=created_at)
        evt.refresh_from_db()
        return evt

    def test_01_authenticated_user_temporal_isolation(self):
        """
        Vérifie pour un utilisateur authentifié qu'à l'instant T :
        - features(A) = 0 interaction antérieure
        - features(B) = A uniquement (1 event)
        - features(C) = A + B uniquement (2 events)
        - et JAMAIS C dans features(B).
        """
        t0 = timezone.now() - timedelta(hours=2)
        t_A = t0 + timedelta(minutes=0)   # 10:00
        t_B = t0 + timedelta(minutes=5)   # 10:05
        t_C = t0 + timedelta(minutes=10)  # 10:10

        event_A = self._create_event(
            utilisateur=self.user,
            publication=self.publication,
            session_id="sess_auth_001",
            event_type="PLAY",
            watch_time_seconds=5.0,
            created_at=t_A
        )

        event_B = self._create_event(
            utilisateur=self.user,
            publication=self.publication,
            session_id="sess_auth_001",
            event_type="LIKE",
            watch_time_seconds=15.0,
            created_at=t_B
        )

        event_C = self._create_event(
            utilisateur=self.user,
            publication=self.publication,
            session_id="sess_auth_001",
            event_type="CART_ADD",
            watch_time_seconds=20.0,
            created_at=t_C
        )

        # Construction des lignes du dataset
        row_A = DatasetBuilder.build_dataset_row(event_A)
        row_B = DatasetBuilder.build_dataset_row(event_B)
        row_C = DatasetBuilder.build_dataset_row(event_C)

        # Assertions
        self.assertEqual(row_A['user_total_events'], 0, "A ne doit voir aucun événement antérieur")
        self.assertEqual(row_B['user_total_events'], 1, "B doit voir uniquement A (1 event)")
        self.assertEqual(row_C['user_total_events'], 2, "C doit voir uniquement A et B (2 events)")

    def test_02_future_event_addition_does_not_alter_past_features(self):
        """
        Vérifie qu'ajouter un événement futur D dans la base à 10:15
        n'altère absolument pas les features historiquement extraites pour B à 10:05.
        """
        t0 = timezone.now() - timedelta(hours=1)
        t_A = t0 + timedelta(minutes=0)
        t_B = t0 + timedelta(minutes=5)

        event_A = self._create_event(
            utilisateur=self.user,
            publication=self.publication,
            session_id="sess_auth_002",
            event_type="PLAY",
            watch_time_seconds=10.0,
            created_at=t_A
        )

        event_B = self._create_event(
            utilisateur=self.user,
            publication=self.publication,
            session_id="sess_auth_002",
            event_type="COMPLETED",
            watch_time_seconds=30.0,
            created_at=t_B
        )

        row_B_before = DatasetBuilder.build_dataset_row(event_B)
        events_before = row_B_before['user_total_events']

        # Ajout d'un événement futur D dans le temps
        t_D = t0 + timedelta(minutes=15)
        self._create_event(
            utilisateur=self.user,
            publication=self.publication,
            session_id="sess_auth_002",
            event_type="SHARE",
            watch_time_seconds=5.0,
            created_at=t_D
        )

        # Ré-extraction des features pour B
        row_B_after = DatasetBuilder.build_dataset_row(event_B)

        self.assertEqual(
            row_B_before['user_total_events'],
            row_B_after['user_total_events'],
            "L'ajout d'un événement futur D ne doit jamais modifier les features passées de B"
        )

    def test_03_anonymous_user_session_temporal_isolation(self):
        """
        Vérifie la règle anti-fuite temporelle pour une session d'utilisateur anonyme S1 :
        - features(A) = 0 event
        - features(B) = A uniquement (1 event)
        - features(C) = A + B uniquement (2 events)
        - et JAMAIS C dans features(B).
        """
        t0 = timezone.now() - timedelta(minutes=30)
        t_A = t0 + timedelta(minutes=0)
        t_B = t0 + timedelta(minutes=2)
        t_C = t0 + timedelta(minutes=4)

        session_id = "anon_session_leakage_test_001"

        event_A = self._create_event(
            utilisateur=None,
            publication=self.publication,
            session_id=session_id,
            event_type="PLAY",
            watch_time_seconds=4.0,
            created_at=t_A
        )

        event_B = self._create_event(
            utilisateur=None,
            publication=self.publication,
            session_id=session_id,
            event_type="WATCH",
            watch_time_seconds=12.0,
            created_at=t_B
        )

        event_C = self._create_event(
            utilisateur=None,
            publication=self.publication,
            session_id=session_id,
            event_type="LIKE",
            watch_time_seconds=15.0,
            created_at=t_C
        )

        row_A = DatasetBuilder.build_dataset_row(event_A)
        row_B = DatasetBuilder.build_dataset_row(event_B)
        row_C = DatasetBuilder.build_dataset_row(event_C)

        self.assertEqual(row_A['user_total_events'], 0)
        self.assertEqual(row_B['user_total_events'], 1)
        self.assertEqual(row_C['user_total_events'], 2)

    def test_04_strict_created_at_less_than_comparison(self):
        """
        Vérifie que la comparaison est stricte : created_at < T.
        L'événement cible lui-même ne doit PAS être inclus dans ses propres features.
        """
        t0 = timezone.now() - timedelta(minutes=10)
        event_solo = self._create_event(
            utilisateur=self.user,
            publication=self.publication,
            session_id="sess_solo",
            event_type="LIKE",
            watch_time_seconds=10.0,
            created_at=t0
        )
        row_solo = DatasetBuilder.build_dataset_row(event_solo)
        self.assertEqual(row_solo['user_total_events'], 0, "L'événement lui-même ne doit pas être comptabilisé dans son historique")

