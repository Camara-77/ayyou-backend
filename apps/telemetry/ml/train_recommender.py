import os
import json
import joblib
import lightgbm as lgb
import pandas as pd
import numpy as np
from typing import Dict, Any, Tuple, Optional
from pathlib import Path
from datetime import datetime

from apps.telemetry.ml.dataset import (
    FEATURE_COLUMNS,
    TARGET_COLUMN,
    GROUP_COLUMN,
    extract_group_counts
)


def train_lgbm_ranker(
    train_df: pd.DataFrame,
    val_df: pd.DataFrame,
    hyperparams: Optional[Dict[str, Any]] = None
) -> Tuple[lgb.LGBMRanker, Dict[str, float]]:
    """
    Entraîne un modèle LightGBM LGBMRanker avec l'objectif LambdaMART.
    """
    if train_df.empty:
        raise ValueError("Le DataFrame d'entraînement est vide. Impossible d'entraîner le modèle.")

    X_train = train_df[FEATURE_COLUMNS]
    y_train = train_df[TARGET_COLUMN].values
    group_train = extract_group_counts(train_df)

    default_params = {
        'objective': 'lambdarank',
        'metric': 'ndcg',
        'eval_at': [5, 10],
        'n_estimators': 100,
        'learning_rate': 0.05,
        'num_leaves': 31,
        'random_state': 42,
        'importance_type': 'gain',
        'verbose': -1
    }

    if hyperparams:
        default_params.update(hyperparams)

    ranker = lgb.LGBMRanker(**default_params)

    if not val_df.empty:
        X_val = val_df[FEATURE_COLUMNS]
        y_val = val_df[TARGET_COLUMN].values
        group_val = extract_group_counts(val_df)

        ranker.fit(
            X_train,
            y_train,
            group=group_train,
            eval_set=[(X_val, y_val)],
            eval_group=[group_val],
            eval_at=[5, 10]
        )
    else:
        ranker.fit(
            X_train,
            y_train,
            group=group_train
        )

    # Calcul de l'importance des caractéristiques (gain)
    importances_arr = ranker.feature_importances_
    feature_importances = {col: round(float(imp), 4) for col, imp in zip(FEATURE_COLUMNS, importances_arr)}
    sorted_importances = dict(sorted(feature_importances.items(), key=lambda x: x[1], reverse=True))

    return ranker, sorted_importances


def save_recommender_model(
    model: lgb.LGBMRanker,
    filepath: str,
    metadata: Optional[Dict[str, Any]] = None
) -> str:
    """
    Sauvegarde le modèle d'entraînement (.joblib) et optionnellement ses métadonnées (.json).
    Retourne le chemin absolu du fichier de modèle (.joblib) sous forme de chaîne (string).
    """
    path = Path(filepath)
    path.parent.mkdir(parents=True, exist_ok=True)
    
    # 1. Sauvegarde du modèle joblib
    joblib.dump(model, path)
    
    # 2. Sauvegarde des métadonnées si fournies
    if metadata:
        meta_path = path.with_suffix('.json')
        meta_data_to_save = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'model_type': 'LGBMRanker (LambdaMART)',
            **metadata
        }
        with open(meta_path, 'w', encoding='utf-8') as f:
            json.dump(meta_data_to_save, f, indent=2, ensure_ascii=False)

    return str(path.resolve())


def load_recommender_model(filepath: str) -> lgb.LGBMRanker:
    """
    Recharge le modèle entraîné depuis le disque.
    """
    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(f"Fichier de modèle introuvable : {filepath}")
    return joblib.load(path)
