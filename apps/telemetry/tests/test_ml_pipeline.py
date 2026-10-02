import os
import shutil
import tempfile
import pandas as pd
import numpy as np
from django.test import TestCase

from apps.telemetry.ml.dataset import (
    prepare_ml_dataframe,
    split_dataset_by_groups,
    extract_group_counts,
    FEATURE_COLUMNS,
    TARGET_COLUMN,
    GROUP_COLUMN
)
from apps.telemetry.ml.train_recommender import (
    train_lgbm_ranker,
    save_recommender_model,
    load_recommender_model
)
from apps.telemetry.ml.evaluate_recommender import (
    evaluate_model_on_dataset,
    evaluate_popularity_baseline
)


class MLPipelineTestCase(TestCase):
    def setUp(self):
        # Création d'un dataset synthétique uniquement pour tester la validité technique du code ML
        self.synthetic_data = [
            # Session 1 (User 1)
            {
                'query_session_id': 'sess_1',
                'user_id': 1,
                'publication_id': 'pub_1',
                'target_relevance': 0,
                'is_authenticated': 1,
                'user_account_age_days': 10,
                'user_total_orders': 2,
                'user_avg_order_amount': 2500.0,
                'user_total_likes': 5,
                'user_total_events': 12,
                'user_avg_watch_time': 8.5,
                'user_avg_completion_rate': 0.4,
                'user_top_category_id': 1,
                'video_recency_hours': 2.0,
                'video_duration_seconds': 20.0,
                'video_total_likes': 50,
                'video_total_shares': 5,
                'dish_price': 2500.0,
                'dish_category_id': 1,
                'resto_rating': 4.5,
                'resto_reviews_count': 100,
                'feed_position': 0,
                'hour_of_day': 12,
                'day_of_week': 2
            },
            {
                'query_session_id': 'sess_1',
                'user_id': 1,
                'publication_id': 'pub_2',
                'target_relevance': 3,
                'is_authenticated': 1,
                'user_account_age_days': 10,
                'user_total_orders': 2,
                'user_avg_order_amount': 2500.0,
                'user_total_likes': 5,
                'user_total_events': 12,
                'user_avg_watch_time': 8.5,
                'user_avg_completion_rate': 0.4,
                'user_top_category_id': 1,
                'video_recency_hours': 5.0,
                'video_duration_seconds': 15.0,
                'video_total_likes': 120,
                'video_total_shares': 20,
                'dish_price': 3000.0,
                'dish_category_id': 2,
                'resto_rating': 4.8,
                'resto_reviews_count': 200,
                'feed_position': 1,
                'hour_of_day': 12,
                'day_of_week': 2
            },
            # Session 2 (User 2)
            {
                'query_session_id': 'sess_2',
                'user_id': 2,
                'publication_id': 'pub_1',
                'target_relevance': 2,
                'is_authenticated': 0,
                'user_account_age_days': 0,
                'user_total_orders': 0,
                'user_avg_order_amount': 0.0,
                'user_total_likes': 0,
                'user_total_events': 3,
                'user_avg_watch_time': 12.0,
                'user_avg_completion_rate': 0.8,
                'user_top_category_id': None,
                'video_recency_hours': 2.0,
                'video_duration_seconds': 20.0,
                'video_total_likes': 50,
                'video_total_shares': 5,
                'dish_price': 2500.0,
                'dish_category_id': 1,
                'resto_rating': 4.5,
                'resto_reviews_count': 100,
                'feed_position': 0,
                'hour_of_day': 19,
                'day_of_week': 4
            },
            {
                'query_session_id': 'sess_2',
                'user_id': 2,
                'publication_id': 'pub_3',
                'target_relevance': 4,
                'is_authenticated': 0,
                'user_account_age_days': 0,
                'user_total_orders': 0,
                'user_avg_order_amount': 0.0,
                'user_total_likes': 0,
                'user_total_events': 3,
                'user_avg_watch_time': 12.0,
                'user_avg_completion_rate': 0.8,
                'user_top_category_id': None,
                'video_recency_hours': 10.0,
                'video_duration_seconds': 25.0,
                'video_total_likes': 200,
                'video_total_shares': 35,
                'dish_price': 4000.0,
                'dish_category_id': 1,
                'resto_rating': 4.9,
                'resto_reviews_count': 300,
                'feed_position': 1,
                'hour_of_day': 19,
                'day_of_week': 4
            },
        ]
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_prepare_ml_dataframe(self):
        df = prepare_ml_dataframe(self.synthetic_data)
        self.assertEqual(len(df), 4)
        self.assertIn(GROUP_COLUMN, df.columns)
        self.assertIn(TARGET_COLUMN, df.columns)
        for col in FEATURE_COLUMNS:
            self.assertIn(col, df.columns)

    def test_split_dataset_by_groups_no_leakage(self):
        df = prepare_ml_dataframe(self.synthetic_data)
        train_df, val_df = split_dataset_by_groups(df, test_size=0.5, random_state=42)

        train_sessions = set(train_df[GROUP_COLUMN].unique())
        val_sessions = set(val_df[GROUP_COLUMN].unique())

        # Absence de fuite : l'intersection des sessions doit être vide
        intersection = train_sessions.intersection(val_sessions)
        self.assertEqual(len(intersection), 0)

    def test_extract_group_counts(self):
        df = prepare_ml_dataframe(self.synthetic_data)
        groups = extract_group_counts(df)
        self.assertEqual(list(groups), [2, 2])

    def test_train_lgbm_ranker_synthetic(self):
        df = prepare_ml_dataframe(self.synthetic_data)
        train_df, val_df = split_dataset_by_groups(df, test_size=0.5, random_state=42)

        ranker, importances = train_lgbm_ranker(train_df, val_df)
        self.assertIsNotNone(ranker)
        self.assertIn('dish_price', importances)

    def test_save_and_load_model(self):
        df = prepare_ml_dataframe(self.synthetic_data)
        ranker, _ = train_lgbm_ranker(df, df)

        save_path = os.path.join(self.temp_dir, 'lgbm_test.joblib')
        saved_file = save_recommender_model(ranker, save_path)
        self.assertTrue(os.path.exists(saved_file))

        loaded_ranker = load_recommender_model(saved_file)
        self.assertIsNotNone(loaded_ranker)

    def test_evaluation_metrics(self):
        df = prepare_ml_dataframe(self.synthetic_data)
        ranker, _ = train_lgbm_ranker(df, df)

        metrics = evaluate_model_on_dataset(ranker, df)
        self.assertIn('ndcg@5', metrics)
        self.assertIn('ndcg@10', metrics)
        self.assertIn('mrr', metrics)

        baseline = evaluate_popularity_baseline(df)
        self.assertIn('ndcg@5', baseline)
