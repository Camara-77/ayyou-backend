# Phase 6.6 — Qualité des Données et Audit Temporel

**Projet :** AYYOU  
**Date :** 1er Octobre 2026  
**Statut :** Pipeline de Données Purgé de la Fuite Temporelle — Aucune Modification du Feed Live  

---

## 1. Volume Actuel

- **Nombre total d'événements bruts (`VideoEventLog`) :** `104`
- **Nombre de sessions distinctes :** `12`
- **Nombre d'utilisateurs authentifiés distincts :** `5`
- **Nombre de sessions anonymes distinctes :** `6`
- **Nombre de publications vidéo candidates :** `8`

---

## 2. Répartition Utilisateurs / Sessions

- **Sessions authentifiées :** 6 sessions
- **Sessions anonymes :** 6 sessions
- **Moyenne d'événements par session :** `8.67` événements/session
- **Moyenne d'événements par utilisateur authentifié :** `20.80` événements/utilisateur

---

## 3. Répartition des Événements par Type

| Type d'Événement (`event_type`) | Volume | Pourcentage du Total |
|---|:---:|:---:|
| **IMPRESSION** | 24 | 23.1% |
| **PLAY** | 24 | 23.1% |
| **WATCH** | 23 | 22.1% |
| **COMPLETED** | 7 | 6.7% |
| **SKIP** | 7 | 6.7% |
| **CART_ADD** | 5 | 4.8% |
| **LIKE** | 5 | 4.8% |
| **DISH_CLICK** | 4 | 3.8% |
| **SHARE** | 3 | 2.9% |
| **PAUSE** | 2 | 1.9% |
| **Total** | **104** | **100.0%** |

---

## 4. Qualité Temporelle

- **Horodatage `created_at` valide :** 104 / 104 (100% de dates valides)
- **Événements ordonnés chronologiquement :** Garantis par `order_by('created_at')`
- **Champ `session_id` présent :** 104 / 104 (0 manquant)
- **Association publication :** 104 / 104 (0 manquant)

---

## 5. Anomalies Détectées

- **Durées négatives (`watch_time_seconds` < 0 ou `video_duration_seconds` < 0) :** `0`
- **Événements sans `session_id` :** `0`
- **Événements sans `publication_id` :** `0`
- **Doublons stricts :** `0`

---

## 6. Correction de la Fuite Temporelle

L'anomalie de **fuite temporelle prospective (Look-Ahead Leakage)** a été corrigée dans `apps/telemetry/data_preparation.py` :
- **Avant :** `FeatureExtractor.extract_user_features()` exécutait des requêtes ORM globales sur tout l'historique utilisateur (`VideoEventLog.objects.filter(utilisateur=user)`), comptabilisant les événements ayant eu lieu **APRÈS** la date de l'événement cible ($t > T$).
- **Après :** L'argument `at_datetime` est obligatoirement transmis lors de la construction du dataset (`DatasetBuilder.build_dataset_row(event)`), appliquant la clause stricte `created_at__lt=at_datetime`.
- **Règle garantie :** Pour chaque événement cible à l'instant $T$, seuls les événements créés STRICTEMENT AVANT $T$ sont pris en compte (`created_at < T`). L'événement lui-même et les événements futurs sont rendus complètement invisibles.

---

## 7. Tests Anti-Leakage Validés

Une nouvelle suite de tests unitaires dédiée a été ajoutée dans `apps/telemetry/tests/test_temporal_leakage.py` :
1. `test_01_authenticated_user_temporal_isolation` : Vérifie que pour $T_A < T_B < T_C$, $B$ ne voit que $A$ et pas $C$.
2. `test_02_future_event_addition_does_not_alter_past_features` : Vérifie qu'ajouter un futur événement $D$ à 10:15 ne modifie pas les features de $B$ calculées à 10:05.
3. `test_03_anonymous_user_session_temporal_isolation` : Vérifie l'isolation temporelle stricte par `session_id` pour les visiteurs anonymes.
4. `test_04_strict_created_at_less_than_comparison` : Vérifie que $created\_at < T$ est strict (un événement n'est pas son propre antécédent).

---

## 8. Impact sur le Pipeline

- **Intégrité de la variable cible (Target Y) :** Conservée (représente la réaction à $T$).
- **Features de prédiction (X) :** Totalement purgées des informations futures.
- **Performance :** L'inférence en direct `RecommendationScoringService.score_candidates()` continue d'utiliser `at_datetime = timezone.now()`, préservant la réactivité.

---

## 9. État du Modèle V2

> [!WARNING]
> Le modèle `recommender_lgbm_v2.joblib` actuellement stocké dans `models/recommender/` a été entraîné avec l'ancien pipeline biaisé par la fuite temporelle.  
> **Il ne doit PAS être considéré comme un modèle propre.** Il est conservé uniquement pour assurer la reproductibilité de la simulation Phase 6 hors-feed.

---

## 10. Conditions Nécessaires pour Entraîner le Futur Modèle V3

Le réentraînement d'un modèle V3 propre ne devra être effectué qu'une fois les conditions suivantes réunies :
1. **Accumulation de nouvelles données propres :** Atteindre un seuil minimal de **1 000 événements de télémétrie** et **100+ sessions distinctes**.
2. **Diversité des publications :** Avoir au moins **25+ publications vidéo** actives.
3. **Pipeline d'entraînement V3 :** Exécuter `DatasetBuilder.build_training_dataset()` avec le filtre temporel strict `created_at__lt=T`.
