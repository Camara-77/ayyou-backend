import pandas as pd
import numpy as np
from typing import Dict, Any, List
from sklearn.metrics import ndcg_score

from apps.telemetry.ml.dataset import (
    FEATURE_COLUMNS,
    TARGET_COLUMN,
    GROUP_COLUMN
)


def compute_mrr_for_group(y_true: np.ndarray, y_score: np.ndarray) -> float:
    """
    Calcule le Mean Reciprocal Rank (MRR) pour un groupe de session unique.
    """
    if len(y_true) == 0:
        return 0.0

    # Ordre de tri par score prédit descendant
    order = np.argsort(-y_score)
    y_true_sorted = y_true[order]

    # Trouve la première position d'un item pertinent (target >= 2)
    relevant_indices = np.where(y_true_sorted >= 2)[0]
    if len(relevant_indices) == 0:
        return 0.0

    first_relevant_rank = relevant_indices[0] + 1  # 1-indexed
    return 1.0 / first_relevant_rank


def evaluate_model_on_dataset(model: Any, df: pd.DataFrame) -> Dict[str, float]:
    """
    Évalue les performances de ranking d'un modèle (LGBMRanker) par groupe de session.
    Métriques calculées : NDCG@5, NDCG@10, MRR.
    """
    if df.empty or len(df) == 0:
        return {'ndcg@5': 0.0, 'ndcg@10': 0.0, 'mrr': 0.0}

    X = df[FEATURE_COLUMNS]
    predictions = model.predict(X)
    df_eval = df.copy()
    df_eval['pred_score'] = predictions

    ndcg5_list = []
    ndcg10_list = []
    mrr_list = []

    grouped = df_eval.groupby(GROUP_COLUMN, sort=False)
    for session_id, group in grouped:
        y_true = group[TARGET_COLUMN].values
        y_score = group['pred_score'].values

        if len(y_true) < 2 or np.all(y_true == y_true[0]):
            continue

        # NDCG Sklearn prend une matrice (1, n_items)
        y_true_2d = np.asarray([y_true])
        y_score_2d = np.asarray([y_score])

        try:
            n5 = ndcg_score(y_true_2d, y_score_2d, k=min(5, len(y_true)))
            n10 = ndcg_score(y_true_2d, y_score_2d, k=min(10, len(y_true)))
            ndcg5_list.append(n5)
            ndcg10_list.append(n10)
        except Exception:
            pass

        mrr_val = compute_mrr_for_group(y_true, y_score)
        mrr_list.append(mrr_val)

    return {
        'ndcg@5': round(float(np.mean(ndcg5_list)), 4) if ndcg5_list else 0.0,
        'ndcg@10': round(float(np.mean(ndcg10_list)), 4) if ndcg10_list else 0.0,
        'mrr': round(float(np.mean(mrr_list)), 4) if mrr_list else 0.0,
        'evaluated_sessions_count': len(ndcg5_list)
    }


def evaluate_popularity_baseline(df: pd.DataFrame) -> Dict[str, float]:
    """
    Évalue la baseline simple de popularité globale (`video_total_likes`).
    """
    if df.empty or 'video_total_likes' not in df.columns:
        return {'ndcg@5': 0.0, 'ndcg@10': 0.0, 'mrr': 0.0}

    df_eval = df.copy()
    df_eval['pred_score'] = df_eval['video_total_likes']

    ndcg5_list = []
    ndcg10_list = []
    mrr_list = []

    grouped = df_eval.groupby(GROUP_COLUMN, sort=False)
    for session_id, group in grouped:
        y_true = group[TARGET_COLUMN].values
        y_score = group['pred_score'].values

        if len(y_true) < 2 or np.all(y_true == y_true[0]):
            continue

        y_true_2d = np.asarray([y_true])
        y_score_2d = np.asarray([y_score])

        try:
            n5 = ndcg_score(y_true_2d, y_score_2d, k=min(5, len(y_true)))
            n10 = ndcg_score(y_true_2d, y_score_2d, k=min(10, len(y_true)))
            ndcg5_list.append(n5)
            ndcg10_list.append(n10)
        except Exception:
            pass

        mrr_val = compute_mrr_for_group(y_true, y_score)
        mrr_list.append(mrr_val)

    return {
        'ndcg@5': round(float(np.mean(ndcg5_list)), 4) if ndcg5_list else 0.0,
        'ndcg@10': round(float(np.mean(ndcg10_list)), 4) if ndcg10_list else 0.0,
        'mrr': round(float(np.mean(mrr_list)), 4) if mrr_list else 0.0,
        'evaluated_sessions_count': len(ndcg5_list)
    }
