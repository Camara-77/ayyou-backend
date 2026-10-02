import os
from django.core.management.base import BaseCommand
from django.db.models import Count
from apps.telemetry.models import VideoEventLog
from apps.telemetry.data_preparation import DatasetBuilder, TelemetryDataCleaner
from apps.telemetry.ml.dataset import (
    FEATURE_COLUMNS,
    TARGET_COLUMN,
    GROUP_COLUMN,
    prepare_ml_dataframe,
    split_dataset_by_groups,
)
from apps.telemetry.ml.train_recommender import train_lgbm_ranker, save_recommender_model
from apps.telemetry.ml.evaluate_recommender import evaluate_model_on_dataset, evaluate_popularity_baseline


class Command(BaseCommand):
    help = "Exécute le pipeline d'apprentissage et d'évaluation du modèle LightGBM Ranker (Phase 4)."

    def add_arguments(self, parser):
        parser.add_argument(
            '--save',
            action='store_true',
            help='Sauvegarder le modèle entraîné sur disque et exporter les métadonnées'
        )
        parser.add_argument(
            '--model-path',
            type=str,
            default='models/recommender/recommender_lgbm_v1.joblib',
            help='Chemin relatif de sauvegarde du modèle'
        )
        parser.add_argument(
            '--test-size',
            type=float,
            default=0.2,
            help='Proportion de sessions réservée au jeu de validation (ex: 0.2 pour 20%)'
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING("=================================================="))
        self.stdout.write(self.style.MIGRATE_HEADING("AYYOU — PHASE 4 : ENTRAÎNEMENT & ÉVALUATION LIGHTGBM"))
        self.stdout.write(self.style.MIGRATE_HEADING("=================================================="))

        total_events = VideoEventLog.objects.count()
        self.stdout.write("1. AUDIT DU DATASET ET DES DONNÉES RÉELLES EN BASE :")
        self.stdout.write(f"   - Événements bruts dans VideoEventLog : {total_events}")

        if total_events == 0:
            self.stdout.write(self.style.WARNING(
                "\n⚠️ CONSTAT SUR LES DONNÉES RÉELLES :\n"
                "La base de données contient 0 événement dans VideoEventLog.\n"
                "Aucun entraînement n'est possible sans données réelles."
            ))
            return

        # Construction du dataset
        raw_dataset = DatasetBuilder.build_training_dataset()
        df = prepare_ml_dataframe(raw_dataset)
        
        distinct_sessions = df[GROUP_COLUMN].nunique()
        distinct_users = df['user_id'].dropna().nunique()
        distinct_pubs = df['publication_id'].nunique()

        self.stdout.write(f"   - Lignes nettoyées du dataset : {len(df)}")
        self.stdout.write(f"   - Sessions distinctes (groupes de ranking) : {distinct_sessions}")
        self.stdout.write(f"   - Utilisateurs représentés : {distinct_users} (authentifiés)")
        self.stdout.write(f"   - Vidéos/Publications représentées : {distinct_pubs}")
        self.stdout.write("")

        # Distribution du target
        self.stdout.write("2. DISTRIBUTION DU TARGET RELEVANCE (Y) :")
        target_counts = df[TARGET_COLUMN].value_counts().sort_index()
        for label, count in target_counts.items():
            pct = (count / len(df)) * 100
            self.stdout.write(f"   - Target {label} : {count} ({pct:.1f}%)")
        self.stdout.write("")

        # Évaluation du volume réel
        self.stdout.write("3. ÉVALUATION DU VOLUME ET STATUT D'EXPÉRIMENTATION :")
        if distinct_sessions < 10:
            self.stdout.write(self.style.WARNING(
                f"   [AVERTISSEMENT VOLUME] {distinct_sessions} sessions réelles détectées.\n"
                "   Ce volume constitue un échantillon expérimental restreint.\n"
                "   L'entraînement est techniquement exécuté pour valider le pipeline hors-ligne,\n"
                "   mais ne doit PAS être considéré comme représentatif de la qualité future en production."
            ))
        else:
            self.stdout.write(self.style.SUCCESS(f"   [OK] {distinct_sessions} sessions réelles prêtes pour l'entraînement."))
        self.stdout.write("")

        # Train / Validation Split par session
        test_size = options['test_size']
        train_df, val_df = split_dataset_by_groups(df, test_size=test_size, random_state=42)
        
        train_sessions = train_df[GROUP_COLUMN].nunique()
        val_sessions = val_df[GROUP_COLUMN].nunique()

        self.stdout.write("4. DÉCOUPAGE TRAIN / VALIDATION PAR GROUPE DE SESSION (query_session_id) :")
        self.stdout.write(f"   - Train Set      : {len(train_df)} lignes ({train_sessions} sessions)")
        self.stdout.write(f"   - Validation Set : {len(val_df)} lignes ({val_sessions} sessions)")
        self.stdout.write("")

        # Entraînement LightGBM
        self.stdout.write("5. ENTRAÎNEMENT DU MODÈLE LIGHTGBM LAMBDAMART RANKER...")
        ranker, importances = train_lgbm_ranker(train_df, val_df)
        self.stdout.write("   - Algorithme : LGBMRanker (objective='lambdarank', metric='ndcg')")
        self.stdout.write("   - Parameters : n_estimators=100, learning_rate=0.05, num_leaves=31")
        self.stdout.write("")

        # Évaluation hors-ligne
        self.stdout.write("6. ÉVALUATION ET COMPARAISON DES PERFORMANCES HORS-LIGNE :")
        metrics_model = evaluate_model_on_dataset(ranker, val_df)
        metrics_baseline = evaluate_popularity_baseline(val_df)

        self.stdout.write(self.style.SUCCESS(f"   LightGBM Ranker   -> NDCG@5: {metrics_model['ndcg@5']:.4f} | NDCG@10: {metrics_model['ndcg@10']:.4f} | MRR: {metrics_model['mrr']:.4f} (Sessions évaluées: {metrics_model.get('evaluated_sessions_count', 0)})"))
        self.stdout.write(f"   Popularity Baseline -> NDCG@5: {metrics_baseline['ndcg@5']:.4f} | NDCG@10: {metrics_baseline['ndcg@10']:.4f} | MRR: {metrics_baseline['mrr']:.4f} (Sessions évaluées: {metrics_baseline.get('evaluated_sessions_count', 0)})")
        self.stdout.write("")

        # Feature Importance
        self.stdout.write("7. IMPORTANCE DES CARACTÉRISTIQUES (FEATURE IMPORTANCE - GAIN) :")
        for feat, imp in list(importances.items())[:10]:
            self.stdout.write(f"   - {feat:<30} : {imp:.4f}")
        self.stdout.write("")

        # Sauvegarde
        if options['save']:
            save_path = options['model_path']
            metadata = {
                'total_events_in_db': total_events,
                'total_cleaned_rows': len(df),
                'distinct_sessions': distinct_sessions,
                'distinct_users': distinct_users,
                'distinct_publications': distinct_pubs,
                'train_rows': len(train_df),
                'train_sessions': train_sessions,
                'validation_rows': len(val_df),
                'validation_sessions': val_sessions,
                'target_distribution': {str(k): int(v) for k, v in target_counts.items()},
                'feature_columns': FEATURE_COLUMNS,
                'hyperparams': {
                    'objective': 'lambdarank',
                    'metric': 'ndcg',
                    'eval_at': [5, 10],
                    'n_estimators': 100,
                    'learning_rate': 0.05,
                    'num_leaves': 31,
                    'random_state': 42
                },
                'feature_importances': importances,
                'metrics_lgbm': metrics_model,
                'metrics_popularity_baseline': metrics_baseline
            }
            model_file = save_recommender_model(ranker, save_path, metadata=metadata)
            meta_file = os.path.splitext(model_file)[0] + '.json'
            self.stdout.write(self.style.SUCCESS(f"8. SAUVEGARDE ET VERSIONNEMENT DU MODÈLE :"))
            self.stdout.write(f"   - Fichier Modèle     : {model_file}")
            self.stdout.write(f"   - Fichier Métadonnées : {meta_file}")
            self.stdout.write("==================================================")
