import time
import uuid
import logging
import hashlib
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from django.conf import settings
from django.db.models import Avg, Count, Q

from apps.catalog.models import PublicationFeed
from apps.telemetry.models import RecommendationExperimentLog
from apps.telemetry.ml.scoring import RecommendationScoringService

logger = logging.getLogger(__name__)


class RecommendationExperimentService:
    """
    Service d'expérimentation contrôlée (A/B testing) pour le Recommender LightGBM V3.
    Permet d'affecter les utilisateurs/sessions de manière déterministe au groupe CONTROL (chronologique)
    ou EXPERIMENT (V3), avec fallback chronologique automatique en cas d'erreur de scoring V3.
    """

    MODEL_VERSION = 'v3'

    @classmethod
    def get_experiment_group(cls, user=None, session_id: Optional[str] = None) -> Tuple[str, str]:
        """
        Détermine de manière déterministe le groupe d'un utilisateur ou d'une session anonyme.
        
        :return: Tuple (experiment_group, recommendation_mode)
                 ex: ('control', 'chronological') ou ('experiment', 'v3')
        """
        mode = getattr(settings, 'RECOMMENDATION_MODE', 'chronological')
        enabled = getattr(settings, 'RECOMMENDATION_EXPERIMENT_ENABLED', False)
        percentage = getattr(settings, 'RECOMMENDATION_EXPERIMENT_PERCENTAGE', 15)

        # Si l'expérimentation est désactivée ou si le mode principal n'est pas 'experiment'
        if mode != 'experiment' or not enabled or percentage <= 0:
            return RecommendationExperimentLog.GROUP_CONTROL, 'chronological'

        if percentage >= 100:
            return RecommendationExperimentLog.GROUP_EXPERIMENT, 'experiment'

        # Construction d'un identifiant stable pour le hachage déterministe
        identifier = None
        if user and getattr(user, 'is_authenticated', False):
            identifier = f"user_{user.id}"
        elif session_id:
            identifier = f"session_{session_id}"

        # Si aucun identifiant fiable n'est disponible -> Sécurité : rester dans CONTROL
        if not identifier:
            return RecommendationExperimentLog.GROUP_CONTROL, 'chronological'

        # Hachage déterministe via MD5 (0 à 99)
        hash_val = int(hashlib.md5(identifier.encode('utf-8')).hexdigest(), 16) % 100

        if hash_val < percentage:
            return RecommendationExperimentLog.GROUP_EXPERIMENT, 'experiment'
        else:
            return RecommendationExperimentLog.GROUP_CONTROL, 'chronological'

    @classmethod
    def process_feed_candidates(
        cls,
        candidate_pubs: List[PublicationFeed],
        user=None,
        session_id: Optional[str] = None,
        request_id: Optional[str] = None
    ) -> List[PublicationFeed]:
        """
        Traite la liste des candidat(e)s du Feed selon l'affectation au groupe d'expérimentation.
        
        - Groupe CONTROL : Traitement chronologique inchangé, traçabilité dans RecommendationExperimentLog.
        - Groupe EXPERIMENT : Scoring V3, re-classement par predicted_score DESC, traçabilité dans RecommendationExperimentLog.
        - FALLBACK : En cas de crash/erreur V3, retour automatique à la liste chronologique avec fallback_used=True.
        """
        if not candidate_pubs:
            return []

        req_id = request_id or str(uuid.uuid4())
        sess_id = session_id or f"exp_sess_{req_id[:8]}"
        user_obj = user if (user and getattr(user, 'is_authenticated', False)) else None

        group, mode = cls.get_experiment_group(user=user_obj, session_id=sess_id)

        # --- GROUPE CONTROL (100% CHRONOLOGIQUE) ---
        if group == RecommendationExperimentLog.GROUP_CONTROL:
            try:
                logs_to_create = []
                for idx, pub in enumerate(candidate_pubs, start=1):
                    logs_to_create.append(RecommendationExperimentLog(
                        session_id=sess_id,
                        utilisateur=user_obj,
                        publication=pub,
                        experiment_group=RecommendationExperimentLog.GROUP_CONTROL,
                        recommendation_mode='chronological',
                        model_version=None,
                        predicted_score=None,
                        predicted_rank=None,
                        feed_position=idx,
                        fallback_used=False,
                        scoring_time_ms=0.0,
                        request_id=req_id,
                        candidate_count=len(candidate_pubs)
                    ))
                if logs_to_create:
                    RecommendationExperimentLog.objects.bulk_create(logs_to_create)
            except Exception as exc:
                logger.error(f"[RecommendationExperimentService] Erreur logging control : {str(exc)}")

            return candidate_pubs

        # --- GROUPE EXPERIMENT (SCORÉ PAR LIGHTGBM V3) ---
        start_time = time.perf_counter()
        pub_ids = [p.id for p in candidate_pubs]

        try:
            # Scoring V3
            scored_items = RecommendationScoringService.score_candidates(
                publication_ids=pub_ids,
                user_id=user_obj.id if user_obj else None,
                session_id=sess_id,
                model_version=cls.MODEL_VERSION
            )

            scoring_time_ms = round((time.perf_counter() - start_time) * 1000, 2)

            if not scored_items or len(scored_items) != len(candidate_pubs):
                raise ValueError(f"Incohérence du nombre d'éléments scorés par V3 ({len(scored_items)} vs {len(candidate_pubs)})")

            # Vérification de la validité des scores (0 NaN / 0 Inf)
            for item in scored_items:
                score = item.get('predicted_score')
                if score is None or np.isnan(score) or np.isinf(score):
                    raise ValueError(f"Score invalide détecté (NaN/Inf/None) pour pub {item.get('publication_id')}")

            # Re-classement des publications selon l'ordre scoré V3
            pub_map = {str(p.id): p for p in candidate_pubs}
            reordered_pubs = []
            logs_to_create = []

            for final_rank, item in enumerate(scored_items, start=1):
                pub_id_str = str(item['publication_id'])
                pub_obj = pub_map.get(pub_id_str)
                if pub_obj:
                    reordered_pubs.append(pub_obj)
                    logs_to_create.append(RecommendationExperimentLog(
                        session_id=sess_id,
                        utilisateur=user_obj,
                        publication=pub_obj,
                        experiment_group=RecommendationExperimentLog.GROUP_EXPERIMENT,
                        recommendation_mode='experiment',
                        model_version=cls.MODEL_VERSION,
                        predicted_score=float(item['predicted_score']),
                        predicted_rank=int(item['rank']),
                        feed_position=final_rank,
                        fallback_used=False,
                        scoring_time_ms=scoring_time_ms,
                        request_id=req_id,
                        candidate_count=len(candidate_pubs)
                    ))

            if len(reordered_pubs) != len(candidate_pubs):
                raise ValueError("Certaines publications n'ont pas pu être réalignées après le scoring V3")

            if logs_to_create:
                RecommendationExperimentLog.objects.bulk_create(logs_to_create)

            logger.info(
                f"[RecommendationExperimentService] Scoring V3 EXPERIMENT réussi pour req {req_id} "
                f"({len(candidate_pubs)} candidats, {scoring_time_ms:.2f} ms)."
            )

            return reordered_pubs

        except Exception as e:
            # --- FALLBACK CHRONOLOGIQUE AUTOMATIQUE ---
            scoring_time_ms = round((time.perf_counter() - start_time) * 1000, 2)
            logger.warning(
                f"[RecommendationExperimentService] Échec V3 -> FALLBACK CHRONOLOGIQUE appliqué (req: {req_id}, time: {scoring_time_ms} ms) : {str(e)}"
            )

            try:
                logs_to_create = []
                for idx, pub in enumerate(candidate_pubs, start=1):
                    logs_to_create.append(RecommendationExperimentLog(
                        session_id=sess_id,
                        utilisateur=user_obj,
                        publication=pub,
                        experiment_group=RecommendationExperimentLog.GROUP_EXPERIMENT,
                        recommendation_mode='experiment',
                        model_version=cls.MODEL_VERSION,
                        predicted_score=None,
                        predicted_rank=None,
                        feed_position=idx,
                        fallback_used=True,
                        scoring_time_ms=scoring_time_ms,
                        request_id=req_id,
                        candidate_count=len(candidate_pubs)
                    ))
                if logs_to_create:
                    RecommendationExperimentLog.objects.bulk_create(logs_to_create)
            except Exception as exc_fallback:
                logger.error(f"[RecommendationExperimentService] Erreur logging fallback : {str(exc_fallback)}")

            # Retourner le Feed chronologique d'origine sans faire échouer la requête
            return candidate_pubs
