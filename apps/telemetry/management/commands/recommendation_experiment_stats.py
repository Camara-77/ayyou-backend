import numpy as np
from django.core.management.base import BaseCommand
from django.conf import settings
from django.db.models import Avg, Count, Q

from apps.telemetry.models import RecommendationExperimentLog, VideoEventLog


class Command(BaseCommand):
    help = 'Affiche le tableau de bord des métriques comparatives CONTROL vs EXPERIMENT (A/B testing Recommender V3).'

    def handle(self, *args, **options):
        mode = getattr(settings, 'RECOMMENDATION_MODE', 'chronological')
        enabled = getattr(settings, 'RECOMMENDATION_EXPERIMENT_ENABLED', False)
        percentage = getattr(settings, 'RECOMMENDATION_EXPERIMENT_PERCENTAGE', 15)

        self.stdout.write(self.style.MIGRATE_HEADING("\n=================================================="))
        self.stdout.write(self.style.MIGRATE_HEADING("RECOMMENDATION EXPERIMENT DASHBOARD"))
        self.stdout.write(self.style.MIGRATE_HEADING("=================================================="))

        self.stdout.write("\nSTATUS")
        self.stdout.write("-------")
        self.stdout.write(f"enabled: {str(enabled).lower()}")
        self.stdout.write(f"percentage: {percentage}%")
        self.stdout.write(f"mode: {mode}")

        # Metrics from RecommendationExperimentLog
        control_logs = RecommendationExperimentLog.objects.filter(experiment_group=RecommendationExperimentLog.GROUP_CONTROL)
        exp_logs = RecommendationExperimentLog.objects.filter(experiment_group=RecommendationExperimentLog.GROUP_EXPERIMENT)

        ctrl_sessions_count = control_logs.values('session_id').distinct().count()
        ctrl_users_count = control_logs.filter(utilisateur__isnull=False).values('utilisateur').distinct().count()
        ctrl_impressions_count = control_logs.count()

        exp_sessions_count = exp_logs.values('session_id').distinct().count()
        exp_users_count = exp_logs.filter(utilisateur__isnull=False).values('utilisateur').distinct().count()
        exp_impressions_count = exp_logs.count()

        self.stdout.write("\nGROUPS")
        self.stdout.write("------")
        self.stdout.write("CONTROL:")
        self.stdout.write(f"  sessions: {ctrl_sessions_count}")
        self.stdout.write(f"  users: {ctrl_users_count}")
        self.stdout.write(f"  impressions: {ctrl_impressions_count}")

        self.stdout.write("\nEXPERIMENT V3:")
        self.stdout.write(f"  sessions: {exp_sessions_count}")
        self.stdout.write(f"  users: {exp_users_count}")
        self.stdout.write(f"  impressions: {exp_impressions_count}")

        # Link telemetry events by session_id to calculate engagement metrics
        ctrl_session_ids = set(control_logs.values_list('session_id', flat=True))
        exp_session_ids = set(exp_logs.values_list('session_id', flat=True))

        def calc_engagement(session_ids):
            if not session_ids:
                return {
                    'avg_watch_time': "0.00s",
                    'completion_rate': "0.00%",
                    'skip_rate': "0.00%",
                    'dish_click_rate': "0.00%",
                    'cart_add_rate': "0.00%"
                }

            events = VideoEventLog.objects.filter(session_id__in=session_ids)
            total_ev = events.count()
            if total_ev == 0:
                return {
                    'avg_watch_time': "0.00s",
                    'completion_rate': "0.00%",
                    'skip_rate': "0.00%",
                    'dish_click_rate': "0.00%",
                    'cart_add_rate': "0.00%"
                }

            watch_events = events.filter(event_type__in=[VideoEventLog.EVENT_WATCH, VideoEventLog.EVENT_COMPLETED])
            avg_wt = watch_events.aggregate(Avg('watch_time_seconds'))['watch_time_seconds__avg'] or 0.0

            completed_cnt = events.filter(event_type=VideoEventLog.EVENT_COMPLETED).count()
            skip_cnt = events.filter(event_type=VideoEventLog.EVENT_SKIP).count()
            dish_cnt = events.filter(event_type=VideoEventLog.EVENT_DISH_CLICK).count()
            cart_cnt = events.filter(event_type=VideoEventLog.EVENT_CART_ADD).count()

            # Base par nombre total de sessions distinctes
            num_sess = len(session_ids)
            comp_rate = (completed_cnt / num_sess * 100) if num_sess > 0 else 0.0
            skip_rate = (skip_cnt / num_sess * 100) if num_sess > 0 else 0.0
            dish_rate = (dish_cnt / num_sess * 100) if num_sess > 0 else 0.0
            cart_rate = (cart_cnt / num_sess * 100) if num_sess > 0 else 0.0

            return {
                'avg_watch_time': f"{avg_wt:.2f}s",
                'completion_rate': f"{comp_rate:.2f}%",
                'skip_rate': f"{skip_rate:.2f}%",
                'dish_click_rate': f"{dish_rate:.2f}%",
                'cart_add_rate': f"{cart_rate:.2f}%"
            }

        ctrl_eng = calc_engagement(ctrl_session_ids)
        exp_eng = calc_engagement(exp_session_ids)

        self.stdout.write("\nENGAGEMENT")
        self.stdout.write("----------")
        self.stdout.write("CONTROL:")
        for k, v in ctrl_eng.items():
            self.stdout.write(f"  {k}: {v}")

        self.stdout.write("\nEXPERIMENT V3:")
        for k, v in exp_eng.items():
            self.stdout.write(f"  {k}: {v}")

        # Performance and Fallback metrics
        exp_requests_logs = exp_logs.values('request_id', 'scoring_time_ms', 'fallback_used').distinct()
        req_times = [l['scoring_time_ms'] for l in exp_requests_logs if l['scoring_time_ms'] > 0]
        total_exp_reqs = len(exp_requests_logs)
        fallback_reqs = len([l for l in exp_requests_logs if l['fallback_used']])

        avg_scoring = f"{np.mean(req_times):.2f} ms" if req_times else "0.00 ms"
        p95_scoring = f"{np.percentile(req_times, 95):.2f} ms" if req_times else "0.00 ms"
        fallback_rate = f"{(fallback_reqs / total_exp_reqs * 100):.2f}%" if total_exp_reqs > 0 else "0.00%"

        self.stdout.write("\nPERFORMANCE")
        self.stdout.write("-----------")
        self.stdout.write(f"V3 avg scoring: {avg_scoring}")
        self.stdout.write(f"V3 P95: {p95_scoring}")
        self.stdout.write(f"fallback rate: {fallback_rate}\n")
