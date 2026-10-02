import pandas as pd
import numpy as np
from typing import Tuple, List, Dict, Any, Optional
from sklearn.model_selection import GroupShuffleSplit
from apps.telemetry.data_preparation import DatasetBuilder, TelemetryDataCleaner


# Liste officielle des colonnes de Caractéristiques (Features X) autorisées - EXCLUT les fuites de données
FEATURE_COLUMNS = [
    'is_authenticated',
    'user_account_age_days',
    'user_total_orders',
    'user_avg_order_amount',
    'user_total_likes',
    'user_total_events',
    'user_avg_watch_time',
    'user_avg_completion_rate',
    'user_top_category_id',
    'video_recency_hours',
    'video_duration_seconds',
    'video_total_likes',
    'video_total_shares',
    'dish_price',
    'dish_category_id',
    'resto_rating',
    'resto_reviews_count',
    'feed_position',
    'hour_of_day',
    'day_of_week'
]

# Colonne Cible (Target Y)
TARGET_COLUMN = 'target_relevance'
GROUP_COLUMN = 'query_session_id'


def prepare_ml_dataframe(raw_dataset: List[Dict[str, Any]]) -> pd.DataFrame:
    """
    Transforme la liste de dictionnaires brute produite par DatasetBuilder
    en un DataFrame pandas nettoyé et type-safe.
    """
    if not raw_dataset:
        # Retourne un DataFrame vide aux colonnes conformes
        cols = [GROUP_COLUMN, TARGET_COLUMN] + FEATURE_COLUMNS
        return pd.DataFrame(columns=cols)

    df = pd.DataFrame(raw_dataset)

    # Imputation des valeurs manquantes et encodage sécurisé
    if 'is_authenticated' in df.columns:
        df['is_authenticated'] = df['is_authenticated'].astype(int)

    # Remplace les NaN numériques par 0
    numeric_cols = [col for col in FEATURE_COLUMNS if col != 'is_authenticated']
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        else:
            df[col] = 0

    if TARGET_COLUMN in df.columns:
        df[TARGET_COLUMN] = pd.to_numeric(df[TARGET_COLUMN], errors='coerce').fillna(0).astype(int)

    return df


def split_dataset_by_groups(
    df: pd.DataFrame,
    test_size: float = 0.2,
    random_state: int = 42
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Effectue la séparation Train/Validation basée sur les groupes de sessions (`query_session_id`)
    afin d'éviter tout Data Leakage entre les ensembles d'entraînement et de validation.
    """
    if df.empty or len(df) < 2:
        return df, df

    unique_groups = df[GROUP_COLUMN].nunique()
    if unique_groups <= 1:
        # Si un seul groupe existe, impossible de splitter par groupe -> retourne le df sur les deux
        return df, df

    gss = GroupShuffleSplit(n_splits=1, test_size=test_size, random_state=random_state)
    groups = df[GROUP_COLUMN]

    train_idx, val_idx = next(gss.split(df, groups=groups))

    train_df = df.iloc[train_idx].copy()
    val_df = df.iloc[val_idx].copy()

    # Tri obligatoire par query_session_id pour la structure de groupe LightGBM
    train_df = train_df.sort_values(by=GROUP_COLUMN).reset_index(drop=True)
    val_df = val_df.sort_values(by=GROUP_COLUMN).reset_index(drop=True)

    return train_df, val_df


def extract_group_counts(df: pd.DataFrame) -> np.ndarray:
    """
    Extrait le tableau des tailles de groupes (nombre de lignes par session)
    nécessaire pour l'entraînement d'un LGBMRanker (group parameter).
    """
    if df.empty:
        return np.array([], dtype=int)

    # Note: df doit être trié par GROUP_COLUMN
    group_sizes = df.groupby(GROUP_COLUMN, sort=False).size().to_numpy()
    return group_sizes
