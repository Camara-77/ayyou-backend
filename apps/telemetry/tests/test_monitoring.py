import os
from django.test import TestCase
from django.utils import timezone
from datetime import timedelta

from apps.users.models import Utilisateur
from apps.catalog.models import PublicationFeed, Produit, Etablissement, Categorie
from apps.telemetry.models import VideoEventLog
from apps.telemetry.management.commands.telemetry_quality_stats import compute_telemetry_accumulation_metrics


class TelemetryMonitoringTestCase(TestCase):
    """
    Tests unitaires pour le module de surveillance et d'accumulation de la télémétrie (Phase 6.9).
    """

    @classmethod
    def setUpTestData(cls):
        cls.cat = Categorie.objects.create(nom="Burger & Fast Food", slug="burger-fast-food")
        cls.etablissement = Etablissement.objects.create(
            nom="Point E Snack",
            adresse="Point E Dakar",
            telephone="+221771112233"
        )
        cls.produit = Produit.objects.create(
            nom="Tacos XL",
            prix_base=2500.00,
            etablissement=cls.etablissement,
            categorie=cls.cat
        )
        cls.publication = PublicationFeed.objects.create(
            etablissement=cls.etablissement,
            produit=cls.produit,
            media_url="https://example.com/tacos.mp4"
        )
        cls.user = Utilisateur.objects.create(
            email="mon_user@ayyou.sn",
            nom="MonUser",
            prenom="Test",
            numero_telephone="+221772223344"
        )

    def test_01_metrics_calculation_empty_database(self):
        """Vérifie le calcul sans crash (0 division) lorsque la base est vide."""
        VideoEventLog.objects.all().delete()
        metrics = compute_telemetry_accumulation_metrics()
        self.assertEqual(metrics['total_events'], 0)
        self.assertEqual(metrics['distinct_sessions'], 0)
        self.assertEqual(metrics['pct_events'], 0.0)
        self.assertEqual(metrics['pct_sessions'], 0.0)
        self.assertEqual(metrics['data_status'], 'COLLECTING')

    def test_02_metrics_status_collecting(self):
        """Vérifie le statut COLLECTING lorsque les seuils (1000 events, 100 sessions) ne sont pas atteints."""
        VideoEventLog.objects.create(
            utilisateur=self.user,
            publication=self.publication,
            session_id="mon_sess_001",
            event_type="PLAY"
        )
        metrics = compute_telemetry_accumulation_metrics()
        self.assertEqual(metrics['total_events'], 1)
        self.assertEqual(metrics['distinct_sessions'], 1)
        self.assertEqual(metrics['data_status'], 'COLLECTING')
        self.assertEqual(metrics['pct_events'], 0.1)
        self.assertEqual(metrics['pct_sessions'], 1.0)

    def test_03_metrics_status_ready_for_audit(self):
        """Vérifie le passage au statut READY_FOR_AUDIT uniquement lorsque les deux seuils sont atteints."""
        # Simulation d'événements et sessions
        events_list = []
        t0 = timezone.now() - timedelta(days=1)
        for i in range(100):
            sess_id = f"mock_sess_{i:03d}"
            for j in range(10): # 100 sessions * 10 events = 1000 events
                events_list.append(VideoEventLog(
                    utilisateur=self.user,
                    publication=self.publication,
                    session_id=sess_id,
                    event_type="PLAY",
                    created_at=t0 + timedelta(minutes=i*10 + j)
                ))
        VideoEventLog.objects.bulk_create(events_list)

        metrics = compute_telemetry_accumulation_metrics()
        self.assertEqual(metrics['total_events'], 1000)
        self.assertEqual(metrics['distinct_sessions'], 100)
        self.assertEqual(metrics['data_status'], 'READY_FOR_AUDIT')
        self.assertEqual(metrics['pct_events'], 100.0)
        self.assertEqual(metrics['pct_sessions'], 100.0)

    def test_04_no_data_mutation_during_monitoring(self):
        """Vérifie que l'exécution des métriques de surveillance ne modifie aucun enregistrement en base."""
        count_before = VideoEventLog.objects.count()
        compute_telemetry_accumulation_metrics()
        count_after = VideoEventLog.objects.count()
        self.assertEqual(count_before, count_after, "Le calcul du monitoring ne doit pas modifier la base de données")
