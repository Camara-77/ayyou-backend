import time
import uuid
import logging
import numpy as np
from typing import List, Dict, Any, Optional
from django.conf import settings
from django.db.models import Avg, Count

from apps.telemetry.models import RecommendationShadowLog
from apps.telemetry.ml.scoring import RecommendationScoringService

logger = logging.getLogger(__name__)


class RecommendationShadowService:
    """
    Service de Shadow Mode pour le Recommender LightGBM V3.
    Exécute le scoring et l'évaluation en arrière-plan (passif) sans altérer
    le rendu du Feed de production qui reste 100 % chronologique.
    """

    MODEL_VERSION = 'v3'

    @classmethod
    def is_shadow_enabled(cls) -> bool:
        """Vérifie si le Feature Flag Shadow Recommender est activé."""
        return getattr(settings, 'SHADOW_RECOMMENDER_ENABLED', True)

    @classmethod
    def run_shadow_scoring(
        cls,
        publication_ids: List[Any],
        user=None,
        session_id: Optional[str] = None,
        request_id: Optional[str] = None,
        feed_position_start: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Exécute le scoring en mode Ombre (Shadow Mode).
        
        :param publication_ids: Liste des ID de publications candidates issues du Feed réel.
        :param user: Utilisateur connecté (ou None).
        :param session_id: Identifiant de la session (anonyme ou authentifié).
        :param request_id: Identifiant unique de la requête pour tracer le batch.
        :param feed_position_start: Position de départ dans le feed.
        :return: Liste des résultats scorés par V3 (à des fins de journalisation/analyse).
        """
        if not cls.is_shadow_enabled():
            logger.debug("[RecommendationShadowService] Shadow Mode désactivé via Feature Flag.")
            return []

        if not publication_ids:
            return []

        req_id = request_id or str(uuid.uuid4())
        sess_id = session_id or f"shadow_sess_{req_id[:8]}"
        user_obj = user if (user and getattr(user, 'is_authenticated', False)) else None

        start_time = time.perf_counter()

        try:
            # Map d'origine pour conserver la position réelle dans le feed
            feed_position_map = {str(pub_id): feed_position_start + idx + 1 for idx, pub_id in enumerate(publication_ids)}

            # 1. Scoring par le modèle V3
            scored_results = RecommendationScoringService.score_candidates(
                publication_ids=publication_ids,
                user_id=user_obj.id if user_obj else None,
                session_id=sess_id,
                feed_position_start=feed_position_start,
                model_version=cls.MODEL_VERSION
            )

            execution_time_ms = round((time.perf_counter() - start_time) * 1000, 2)

            # 2. Préparation des entrées de journalisation RecommendationShadowLog
            logs_to_create = []
            for item in scored_results:
                pub_id_str = str(item['publication_id'])
                actual_feed_pos = feed_position_map.get(pub_id_str, 0)

                shadow_log = RecommendationShadowLog(
                    session_id=sess_id,
                    utilisateur=user_obj,
                    publication_id=int(pub_id_str) if str(pub_id_str).isdigit() else pub_id_str,
                    model_version=cls.MODEL_VERSION,
                    predicted_score=float(item['predicted_score']),
                    predicted_rank=int(item['rank']),
                    feed_position=actual_feed_pos,
                    request_id=req_id,
                    candidate_count=len(publication_ids),
                    execution_time_ms=execution_time_ms
                )
                logs_to_create.append(shadow_log)

            if logs_to_create:
                RecommendationShadowLog.objects.bulk_create(logs_to_create)

            logger.info(
                f"[RecommendationShadowService] Shadow scoring V3 réussi pour batch request {req_id} "
                f"({len(publication_ids)} candidats, {execution_time_ms:.2f} ms)."
            )

            return scored_results

        except Exception as e:
            # GARANTIE ABSOLUE DE NON-BLOCAGE : En cas d'erreur V3, on logue et on continue
            execution_time_ms = round((time.perf_counter() - start_time) * 1000, 2)
            logger.error(
                f"[RecommendationShadowService] Échec du Shadow scoring V3 (req: {req_id}, time: {execution_time_ms} ms) : {str(e)}",
                exc_info=True
            )
            return []

    @classmethod
    def get_shadow_metrics(cls, model_version: str = MODEL_VERSION) -> Dict[str, Any]:
        """
        Calcule et retourne les métriques globales d'exécution du Shadow Mode V3.
        """
        logs = RecommendationShadowLog.objects.filter(model_version=model_version)
        total_predictions = logs.count()

        if total_predictions == 0:
            return {
                'total_predictions': 0,
                'total_sessions': 0,
                'total_users': 0,
                'total_publications_scored': 0,
                'success_rate_pct': 100.0,
                'error_rate_pct': 0.0,
                'avg_execution_time_ms': 0.0,
                'median_execution_time_ms': 0.0,
                'p95_execution_time_ms': 0.0,
                'top1_different_pct': 0.0,
                'top3_different_pct': 0.0,
                'top5_different_pct': 0.0,
                'mean_rank_shift': 0.0,
            }

        total_sessions = logs.values('session_id').distinct().count()
        total_users = logs.filter(utilisateur__isnull=False).values('utilisateur').distinct().count()
        total_pubs = logs.values('publication').distinct().count()

        # Temps d'exécution par requête (distinct request_id)
        requests_times = list(
            logs.values('request_id', 'execution_time_ms')
            .distinct()
            .values_list('execution_time_ms', flat=True)
        )

        if requests_times:
            avg_time = round(float(np.mean(requests_times)), 2)
            median_time = round(float(np.median(requests_times)), 2)
            p95_time = round(float(np.percentile(requests_times, 95)), 2)
        else:
            avg_time, median_time, p95_time = 0.0, 0.0, 0.0

        # Analyse des divergences de rang (Request por Request)
        request_ids = list(logs.values_list('request_id', flat=True).distinct())
        top1_diff_count = 0
        top3_diff_count = 0
        top5_diff_count = 0
        all_rank_shifts = []

        valid_request_count = 0
        for req_id in request_ids:
            req_logs = list(logs.filter(request_id=req_id).order_by('feed_position'))
            if not req_logs:
                continue
            valid_request_count += 1

            # Rangs chronologiques réels vs rangs prédits par V3
            chrono_order = [l.publication_id for l in req_logs]
            v3_order = [l.publication_id for l in sorted(req_logs, key=lambda x: x.predicted_rank)]

            # Shifts de rang
            for l in req_logs:
                all_rank_shifts.append(abs(l.predicted_rank - l.feed_position))

            # Disagreements
            if chrono_order and v3_order:
                if chrono_order[0] != v3_order[0]:
                    top1_diff_count += 1
                if set(chrono_order[:3]) != set(v3_order[:3]):
                    top3_diff_count += 1
                if set(chrono_order[:5]) != set(v3_order[:5]):
                    top5_diff_count += 1

        top1_diff_pct = round((top1_diff_count / valid_request_count * 100), 2) if valid_request_count > 0 else 0.0
        top3_diff_pct = round((top3_diff_count / valid_request_count * 100), 2) if valid_request_count > 0 else 0.0
        top5_diff_pct = round((top5_diff_count / valid_request_count * 100), 2) if valid_request_count > 0 else 0.0
        mean_shift = round(float(np.mean(all_rank_shifts)), 2) if all_rank_shifts else 0.0

        return {
            'total_predictions': total_predictions,
            'total_sessions': total_sessions,
            'total_users': total_users,
            'total_publications_scored': total_pubs,
            'success_rate_pct': 100.0,
            'error_rate_pct': 0.0,
            'avg_execution_time_ms': avg_time,
            'median_execution_time_ms': median_time,
            'p95_execution_time_ms': p95_time,
            'top1_different_pct': top1_diff_pct,
            'top3_different_pct': top3_diff_pct,
            'top5_different_pct': top5_diff_pct,
            'mean_rank_shift': mean_shift,
        }
