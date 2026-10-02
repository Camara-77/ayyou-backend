import os
import json
import logging
import joblib
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from django.utils import timezone

from apps.catalog.models import PublicationFeed
from apps.telemetry.data_preparation import FeatureExtractor, TelemetryDataCleaner
from apps.telemetry.ml.dataset import (
    FEATURE_COLUMNS,
    prepare_ml_dataframe,
)

logger = logging.getLogger(__name__)


class RecommendationScoringService:
    """
    Service de scoring isolé pour le modèle de recommandation LightGBM LambdaMART (V2).
    Permet de calculer les scores de pertinence pour une liste de vidéos candidates
    avant toute exposition à l'utilisateur (0 Data Leakage).
    
    CE SERVICE EST STRICTEMENT ISOLE ET N'EST PAS CONNECTE AU FEED EN PRODUCTION.
    """

    _loaded_models: Dict[str, Tuple[Any, Dict[str, Any]]] = {}

    DEFAULT_MODEL_V2_PATH = 'models/recommender/recommender_lgbm_v2.joblib'
    DEFAULT_MODEL_V3_PATH = 'models/recommender/recommender_lgbm_v3.joblib'
    DEFAULT_MODEL_PATH = DEFAULT_MODEL_V2_PATH

    @classmethod
    def resolve_model_path(cls, model_version: Optional[str] = None, model_path: Optional[str] = None) -> str:
        if model_path:
            return model_path
        if model_version:
            mv = str(model_version).lower().strip()
            if mv in ['v3', 'v3.0', 'recommender_lgbm_v3', 'lgbm_v3']:
                return cls.DEFAULT_MODEL_V3_PATH
            elif mv in ['v2', 'v2.0', 'recommender_lgbm_v2', 'lgbm_v2']:
                return cls.DEFAULT_MODEL_V2_PATH
        
        from django.conf import settings
        default_mode = getattr(settings, 'RECOMMENDATION_MODE', 'chronological')
        if default_mode in ['v3', 'v3.0']:
            return cls.DEFAULT_MODEL_V3_PATH
        return cls.DEFAULT_MODEL_V2_PATH

    @classmethod
    def load_model(cls, model_version: Optional[str] = None, model_path: Optional[str] = None) -> Tuple[Any, Dict[str, Any]]:
        """
        Charge le modèle LightGBM et ses métadonnées associés depuis le disque (Singleton / Cache).
        """
        target_path = cls.resolve_model_path(model_version=model_version, model_path=model_path)
        abs_path = Path(target_path).resolve()

        if str(abs_path) in cls._loaded_models:
            return cls._loaded_models[str(abs_path)]

        if not abs_path.exists():
            logger.error(f"[RecommendationScoringService] Modèle introuvable à l'emplacement : {abs_path}")
            raise FileNotFoundError(f"Modèle de recommandation introuvable : {abs_path}")

        try:
            logger.info(f"[RecommendationScoringService] Chargement du modèle depuis : {abs_path}")
            model = joblib.load(abs_path)

            meta_path = abs_path.with_suffix('.json')
            metadata = {}
            if meta_path.exists():
                with open(meta_path, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)

            cls._loaded_models[str(abs_path)] = (model, metadata)

            return model, metadata
        except Exception as e:
            logger.error(f"[RecommendationScoringService] Erreur lors du chargement du modèle : {str(e)}")
            raise e

    @classmethod
    def reset_cache(cls):
        """Réinitialise le cache de modèle (utile pour les tests)."""
        cls._loaded_models.clear()

    @classmethod
    def score_candidates(
        cls,
        publication_ids: List[Any],
        user_id: Optional[int] = None,
        session_id: Optional[str] = None,
        feed_position_start: int = 0,
        model_version: Optional[str] = None,
        model_path: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Calcule les scores de pertinence pour une liste de publications candidates.
        
        :param publication_ids: Liste des ID de publications à scorer.
        :param user_id: ID de l'utilisateur authentifié (optionnel).
        :param session_id: Session ID de l'utilisateur anonyme ou authentifié (optionnel).
        :param feed_position_start: Position de départ dans le feed.
        :param model_version: Version spécifique du modèle ('v2', 'v3').
        :param model_path: Chemin spécifique vers un modèle.
        :return: Liste ordonnée de dictionnaires contenant les détails et les scores des vidéos.
        """
        if not publication_ids:
            return []

        # 1. Chargement du modèle spécifié (V2 ou V3)
        model, metadata = cls.load_model(model_version=model_version, model_path=model_path)

        # 2. Extraction du profil utilisateur ONCE (Garantie de performance)
        user_feats = FeatureExtractor.extract_user_features(user_id=user_id, session_id=session_id)

        # 3. Contexte temporel actuel
        now = timezone.now()
        current_hour = now.hour
        current_weekday = now.weekday()

        # 4. Construction des caractéristiques pour chaque vidéo candidate
        raw_rows = []
        for i, pub_id in enumerate(publication_ids):
            video_feats = FeatureExtractor.extract_video_features(pub_id)
            context_feats = {
                'feed_position': feed_position_start + i,
                'hour_of_day': current_hour,
                'day_of_week': current_weekday,
            }

            combined_row = {
                'query_session_id': session_id or 'scoring_session_simulated',
                'target_relevance': 0, # Inconnu lors du scoring (Pre-exposure)
                **user_feats,
                **video_feats,
                **context_feats,
            }
            raw_rows.append(combined_row)

        # 5. Conversion en DataFrame conforme au format d'entraînement
        df_ml = prepare_ml_dataframe(raw_rows)
        X_scoring = df_ml[FEATURE_COLUMNS]

        # 6. Prédiction par le modèle LightGBM LambdaMART
        try:
            predicted_scores = model.predict(X_scoring)
        except Exception as e:
            logger.error(f"[RecommendationScoringService] Erreur lors de la prédiction : {str(e)}")
            raise e

        # 7. Association des scores et enrichissement des résultats
        results = []
        pubs_queryset = PublicationFeed.objects.filter(pk__in=publication_ids).select_related('produit', 'etablissement')
        pubs_map = {str(p.id): p for p in pubs_queryset}

        for i, pub_id in enumerate(publication_ids):
            pub_str = str(pub_id)
            score_val = round(float(predicted_scores[i]), 4)
            pub_obj = pubs_map.get(pub_str)

            dish_name = pub_obj.produit.nom if (pub_obj and pub_obj.produit) else None
            resto_name = pub_obj.etablissement.nom if (pub_obj and pub_obj.etablissement) else None
            dish_price = float(pub_obj.produit.prix_base) if (pub_obj and pub_obj.produit) else 0.0

            results.append({
                'publication_id': pub_str,
                'predicted_score': score_val,
                'dish_name': dish_name,
                'resto_name': resto_name,
                'dish_price': dish_price,
            })

        # 8. Tri par score prédit décroissant (Ranking expérimental)
        results.sort(key=lambda item: item['predicted_score'], reverse=True)
        for rank_idx, item in enumerate(results, start=1):
            item['rank'] = rank_idx

        return results
