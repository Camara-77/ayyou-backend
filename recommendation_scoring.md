# DOCUMENTATION TECHNIQUE — SERVICE DE SCORING HORS FEED (PHASE 5)

## 1. Objectif

Le service `RecommendationScoringService` fournit une infrastructure de scoring autonome et isolée.
Il permet de prendre en entrée un utilisateur (ou une session anonyme) et une liste de vidéos candidates, afin d'évaluer le score de pertinence prédit par le modèle **LightGBM LambdaMART V2** (`recommender_lgbm_v2.joblib`) avant toute exposition au client.

> **RÈGLE CRITIQUE D'ISOLEMENT :**
> Ce service est **100% indépendant**. Le Feed de production d'AYYOU reste **100% CHRONOLOGIQUE et INCHANGÉ**. `RecommendationScoringService` est réservé à la simulation, aux tests et à la validation.

---

## 2. Architecture

```text
               +----------------------------------+
               |  Requête de Simulation / Test   |
               +----------------------------------+
                                |
                                v
               +----------------------------------+
               | RecommendationScoringSimulation  |
               |  (Endpoint /api/.../simulate/)   |
               +----------------------------------+
                                |
                                v
               +----------------------------------+
               |   RecommendationScoringService   |
               |     (Singleton / Model Cache)    |
               +----------------------------------+
                 /                              \
                /                                \
               v                                  v
+-------------------------------+  +-------------------------------+
|  FeatureExtractor (User/Ctx)  |  | FeatureExtractor (Video/Ctx)  |
+-------------------------------+  +-------------------------------+
                \                                /
                 \                              /
                  v                            v
               +----------------------------------+
               |  LightGBM V2 (.joblib + .json)   |
               +----------------------------------+
                                |
                                v
               +----------------------------------+
               | Tri & Classement Expérimental    |
               |       (Ranked Candidates)        |
               +----------------------------------+
```

---

## 3. Modèle utilisé

- **Fichier Modèle** : [`models/recommender/recommender_lgbm_v2.joblib`](file:///c:/Users/HP/Desktop/Ayyou-backend/models/recommender/recommender_lgbm_v2.joblib)
- **Fichier Métadonnées** : [`models/recommender/recommender_lgbm_v2.json`](file:///c:/Users/HP/Desktop/Ayyou-backend/models/recommender/recommender_lgbm_v2.json)
- **Chargement** : Chargé via `joblib` avec mise en cache singleton (aucun rechargement disque par vidéo).

---

## 4. Features (Whitelist Stricte)

Le scoring utilise les 20 caractéristiques exactes entraînées en Phase 4.5 :
- **Profil Utilisateur** : `is_authenticated`, `user_account_age_days`, `user_total_orders`, `user_avg_order_amount`, `user_total_likes`, `user_total_events`, `user_avg_watch_time`, `user_avg_completion_rate`, `user_top_category_id`.
- **Contenu Vidéo** : `video_recency_hours`, `video_duration_seconds`, `video_total_likes`, `video_total_shares`, `dish_price`, `dish_category_id`, `resto_rating`, `resto_reviews_count`.
- **Contexte** : `feed_position`, `hour_of_day`, `day_of_week`.

---

## 5. Construction du contexte utilisateur

- **Utilisateur Authentifié** : Les caractéristiques de profil (`user_total_orders`, `user_avg_watch_time`, `user_top_category_id`) sont extraites une seule fois par batch d'évaluation pour optimiser le temps de réponse.
- **Visiteur Anonyme** : Les agrégations télémétriques s'effectuent à chaud à partir de son `session_id`.

---

## 6. Construction du contexte vidéo

Pour chaque vidéo candidate dans `publication_ids` :
- Extraction des propriétés statiques du plat (`dish_price`, `dish_category_id`).
- Extraction des métriques de l'établissement (`resto_rating`, `resto_reviews_count`).
- Agrégation des statistiques historiques de popularité (`video_total_likes`, `video_total_shares`).

---

## 7. Cold Start Utilisateur

Lorsqu'un utilisateur authentifié ou anonyme ne possède aucun historique :
- `is_authenticated` = True ou False.
- Les agrégations numériques (`user_total_events`, `user_avg_watch_time`, `user_avg_completion_rate`) s'initialisent proprement à `0.0`.
- Aucun crash ni exception n'est levé.

---

## 8. Cold Start Contenu

Lorsqu'une nouvelle vidéo est publiée sans historique de visionnage :
- `video_recency_hours` est calculé en fonction de la date de création.
- `video_total_likes` et `video_total_shares` s'initialisent à `0`.
- Les caractéristiques statiques du plat et du restaurant orientent la prédiction.

---

## 9. Zero Data Leakage

Le scoring s'exécute **strictement avant l'exposition** de la vidéo à l'utilisateur :
- Les colonnes post-interaction (`event_type`, `watch_time_seconds`, `completion_rate`, `is_skip`, `is_completed`) sont totalement **absentes** des caractéristiques d'entrée $X$.

---

## 10. API de Simulation Interne

- **Route** : `POST /api/telemetry/scoring/simulate/`
- **Corps de requête** :
```json
{
  "publication_ids": [38, 39, 40, 41],
  "session_id": "sim_session_101"
}
```
- **Réponse HTTP 200 OK** :
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
    }, ...
  ]
}
```

---

## 11. Exemple de Scoring Python

```python
from apps.telemetry.ml.scoring import RecommendationScoringService

# Scoring de 4 candidats pour l'utilisateur #185
results = RecommendationScoringService.score_candidates(
    publication_ids=[38, 39, 40, 41],
    user_id=185
)
# Retrouve la liste triée par score décroissant
```

---

## 12. Tests

Suite de tests automatisés dédiée dans `apps/telemetry/tests/test_scoring.py` (10 tests unitaires et d'intégration validant le chargement, les fallbacks, le cold start, le tri et l'API).

---

## 13. Limites

- Le modèle V2 s'appuie sur un échantillon expérimental de 12 sessions.
- Le scoring hors-feed sert d'outil d'évaluation préliminaire avant toute mise en production.

---

## 14. Version du modèle

- **Version active** : `recommender_lgbm_v2`
- **Version V1** : Conservée intacte sur disque pour référence historique.

---

## 15. Pourquoi le Feed n'est pas encore connecté

Le Feed d'AYYOU reste chronologique car le modèle de recommandation nécessite d'être testé et simulé sur un volume plus important de sessions utilisateurs qualifiées afin de garantir un ordonnancement optimal sans risque de dégrader l'expérience utilisateur.
