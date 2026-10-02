# AYYOU — RAPPORT DU SERVICE DE SCORING HORS FEED (PHASE 5)

## 1. Modèle
- **Modèle chargé** : `recommender_lgbm_v2.joblib`
- **Version** : `recommender_lgbm_v2`
- **Emplacement disque** : `models/recommender/recommender_lgbm_v2.joblib`
- **Métadonnées associées** : `models/recommender/recommender_lgbm_v2.json`
- **Mécanisme de chargement** : Mémoire partagée / Cache Singleton via `RecommendationScoringService.load_model()`. Aucune re-sérialisation par vidéo.

---

## 2. Features
- **Nombre de caractéristiques utilisées** : 20 (strictement identiques à la Whitelist de la Phase 4.5).
- **Ordre et Noms** : Conformes à `FEATURE_COLUMNS` (`is_authenticated`, `user_account_age_days`, `user_total_orders`, `user_avg_order_amount`, `user_total_likes`, `user_total_events`, `user_avg_watch_time`, `user_avg_completion_rate`, `user_top_category_id`, `video_recency_hours`, `video_duration_seconds`, `video_total_likes`, `video_total_shares`, `dish_price`, `dish_category_id`, `resto_rating`, `resto_reviews_count`, `feed_position`, `hour_of_day`, `day_of_week`).
- **Transformations & Imputation** : Pipeline unifié via `prepare_ml_dataframe()`.

---

## 3. Scoring
- **Scoring individuel** : `RecommendationScoringService.score_candidates([pub_id])`
- **Scoring en lot (Batch)** : `RecommendationScoringService.score_candidates([pub_1, pub_2, ...])`
- **Tri & Ordonnancement** : Résultats triés par score prédit décroissant avec affectation dynamique des rangs (`rank: 1`, `rank: 2`, ...).

---

## 4. Profils Utilisateurs
- **Utilisateur Authentifié** : Extraction unique du profil d'historique en base.
- **Visiteur Anonyme** : Suivi via `session_id`.
- **Nouveau Compte** : Géré sans aucune exception.

---

## 5. Cold Start
- **Cold Start Utilisateur** : Imputation des statistiques à 0.0 pour les nouveaux utilisateurs ou visiteurs sans télémétrie.
- **Cold Start Contenu** : Evaluation basée sur les caractéristiques statiques du plat (`dish_price`, `dish_category_id`), de l'établissement (`resto_rating`, `resto_reviews_count`) et de la fraîcheur (`video_recency_hours`).

---

## 6. Audit Data Leakage au Scoring
- **Strict Pre-exposure Rule** : `event_type`, `watch_time_seconds`, `completion_rate`, `is_skip`, `is_completed` sont strictement absents de l'entrée $X$.
- Le calcul s'exécute exclusivement avec les informations disponibles AVANT la présentation de la vidéo.

---

## 7. API de Simulation Interne
- **Endpoint** : `POST /api/telemetry/scoring/simulate/`
- **Méthode** : `POST` (Accessible hors-feed)
- **Exemple de Requête** :
```json
{
  "publication_ids": [38, 39, 40, 41],
  "session_id": "sim_session_101"
}
```
- **Exemple de Réponse** :
```json
{
  "status": "success",
  "model_version": "recommender_lgbm_v2",
  "candidates_count": 4,
  "ranked_candidates": [
    {
      "publication_id": "40",
      "predicted_score": 0.8124,
      "dish_name": "Tieboudienne",
      "resto_name": "Chez Awa",
      "dish_price": 3500.0,
      "rank": 1
    },
    {
      "publication_id": "38",
      "predicted_score": 0.7512,
      "dish_name": "Salade de Fruits",
      "resto_name": "Marché des Fruits",
      "dish_price": 1500.0,
      "rank": 2
    }
  ]
}
```

---

## 8. Tests Automatisés

Résultat exact de la commande `python manage.py test apps.telemetry` :

```text
Ran 31 tests in 18.985s

OK
```

---

## 9. Garanties de Non-Régression du Feed (Audit d'Isolation)

- **Feed modifié** : **NON**
- **HomeComponent modifié** : **NON**
- **FoodPostComponent modifié** : **NON**
- **Endpoint Feed (`/api/catalog/feed/`) modifié** : **NON**
- **Ordre chronologique du Feed** : **100% CONSERVÉ**

---

## 10. Limites du Système
- Le modèle V2 s'appuie sur un échantillon expérimental de 12 sessions.
- Le service de scoring sert d'outil d'évaluation préliminaire hors-feed et prépare la phase de simulation multi-profils.
