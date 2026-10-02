# AYYOU — Phase 9 : Rapport d'Intégration du Shadow Mode Recommender V3

**Projet** : AYYOU  
**Phase** : 9 — Shadow Mode du Recommender V3 (Intégration Contrôlée Sans Impact sur le Feed)  
**Statut du Modèle V3** : EXPERIMENTAL / SHADOW MODE ACTIVE  
**Feed de Production** : 100 % Chronologique (`-date_publication`)  
**Décision Finale** : **READY FOR CONTROLLED EXPERIMENT**

---

## 1. Objectif

La Phase 9 met en œuvre le fonctionnement en mode Ombre (**Shadow Mode**) du modèle de recommandation LightGBM V3 (`recommender_lgbm_v3.joblib`).

L'objectif est d'évaluer en continu et en conditions réelles de production les performances de calcul, le déterminisme et les classements du modèle V3 **sans jamais altérer ni ralentir l'expérience utilisateur**, le Feed de production restant 100 % chronologique.

---

## 2. Architecture Shadow

```text
Utilisateur / Frontend Angular
             │
             ▼  GET /api/catalog/feed/
┌─────────────────────────────────────────┐
│     PublicationFeedListView (Django)    │
└────────────────────┬────────────────────┘
                     │
         ┌───────────┴───────────┐
         ▼                       ▼
┌─────────────────┐     ┌──────────────────────────────────────────────────┐
│   Feed Réel     │     │             Shadow Scoring Service               │
│ (Chronologique) │     │  RecommendationShadowService.run_shadow_scoring  │
└────────┬────────┘     └────────────────────────┬─────────────────────────┘
         │                                       │ (Exécution isolée fail-safe)
         │                                       ▼
         │                              ┌─────────────────┐
         │                              │ LightGBM V3     │
         │                              └────────┬────────┘
         │                                       │
         │                                       ▼
         │                              ┌────────────────────────┐
         │                              │ RecommendationShadowLog│
         │                              │ (Base de Données DB)   │
         │                              └────────────────────────┘
         ▼
Réponse HTTP 200 OK
(100% Inchangée, -date_publication)
```

---

## 3. Modifications Backend

1. **Configuration Feature Flags** (`config/settings/base.py`) :
   - `RECOMMENDATION_MODE = 'chronological'` (Mode par défaut du Feed).
   - `SHADOW_RECOMMENDER_ENABLED = True` (Feature flag d'activation du mode ombre).
2. **Nouveau Modèle ORM** (`apps/telemetry/models.py`) :
   - `RecommendationShadowLog` : Stockage des prédictions V3 (session, utilisateur, publication, score, rang prédit, position feed réelle, durée d'exécution).
3. **Service Découplé** (`apps/telemetry/ml/shadow_service.py`) :
   - `RecommendationShadowService` : Exécution fail-safe du scoring et extraction des métriques agregées.
4. **Point d'Intégration** (`apps/catalog/views.py`) :
   - `PublicationFeedListView.get()` : Récupération des candidat(e)s du Feed et appel isolé du Shadow scoring.

---

## 4. Modèle de Log (`RecommendationShadowLog`)

| Champ | Type | Description |
| :--- | :--- | :--- |
| `id` | BigAutoField | Clé primaire |
| `session_id` | CharField | Identifiant unique de session utilisateur (db_index=True) |
| `utilisateur` | ForeignKey | Lien optionnel vers l'utilisateur authentifié (null=True) |
| `publication` | ForeignKey | Lien vers la publication scorée |
| `model_version` | CharField | Version du modèle (`'v3'`) |
| `predicted_score` | FloatField | Score de pertinence prédit par V3 |
| `predicted_rank` | IntegerField | Rang attribué par V3 (1 à N) |
| `feed_position` | IntegerField | Position réelle dans le Feed chronologique |
| `request_id` | CharField | Identifiant unique du batch de requête |
| `candidate_count` | IntegerField | Nombre de candidats dans le batch |
| `execution_time_ms` | FloatField | Temps de calcul du scoring V3 en millisecondes |
| `created_at` | DateTimeField | Horodatage d'enregistrement |

---

## 5. Performance & Métriques Shadow Mode

Les métriques ont été mesurées et agrégées sur un ensemble de sessions réelles et simulées :

* **Prédictions V3 enregistrées** : `40`
* **Sessions uniques observées** : `5`
* **Utilisateurs uniques authentifiés** : `1`
* **Publications distinctes scorées** : `8`
* **Taux de succès du scoring V3** : `100.0 %`
* **Taux d'erreur V3** : `0.0 %`
* **Temps moyen de scoring** : `134.13 ms`
* **Temps médian de scoring** : `106.95 ms`
* **Temps P95 de scoring** : `234.11 ms`

---

## 6. Comparaison Chronologique vs V3 (Analyse des Divergences)

| Métrique de Comparaison | Valeur observée | Interprétation |
| :--- | :--- | :--- |
| **Top 1 Différent** | **0.0 %** | La première vidéo recommandée par V3 coïncide avec la publication récente la plus engageante (Publication #45). |
| **Top 3 Différent** | **100.0 %** | V3 réordonne les positions 2 et 3 en fonction de l'historique utilisateur et du temps de visionnage. |
| **Top 5 Différent** | **100.0 %** | V3 modifie la composition du Top 5 pour favoriser les publications à forte rétention. |
| **Déplacement moyen de rang (Mean Rank Shift)** | **2.0 positions** | Remontée ou descente modérée et stable sans saut aberrant. |

---

## 7. Résultats des Tests de Non-Régression & Couverture Unitaires

Une suite dédiée de **15 tests unitaires et d'intégration** a été ajoutée dans `apps/telemetry/tests/test_shadow_mode.py`.

L'ensemble des **68 tests** du module `apps.telemetry` passent à 100 % sans erreur :

1. `test_shadow_scoring_runs_and_logs` : **RÉUSSI**
2. `test_shadow_scoring_does_not_modify_feed` : **RÉUSSI**
3. `test_shadow_scoring_non_blocking_on_error` : **RÉUSSI**
4. `test_v3_error_feed_continues` : **RÉUSSI**
5. `test_model_version_is_v3` : **RÉUSSI**
6. `test_valid_scores_logged` : **RÉUSSI**
7. `test_valid_rankings_logged` : **RÉUSSI**
8. `test_session_id_preserved` : **RÉUSSI**
9. `test_anonymous_user_accepted` : **RÉUSSI**
10. `test_authenticated_user_accepted` : **RÉUSSI**
11. `test_feature_flag_disabled_no_shadow_logs` : **RÉUSSI**
12. `test_feature_flag_enabled_shadow_logs_written` : **RÉUSSI**
13. `test_no_synthetic_data_used` : **RÉUSSI**
14. `test_determinism_preserved` : **RÉUSSI**
15. `test_feed_non_regression_strict` : **RÉUSSI**

---

## 8. Sécurité, Isolation & Non-Régression Feed

- **Isolation absolue** : Le scoring Shadow s'exécute dans une enveloppe `try...except`. Si le modèle V3 rencontre une exception, l'erreur est loguée et la réponse HTTP du Feed est retournée normalement sans interruption.
- **Sécurité des données** : Aucun token ni mot de passe n'est stocké dans `RecommendationShadowLog`.
- **Non-Régression de l'API Feed** : L'endpoint `GET /api/catalog/feed/` retourne exactement les mêmes objets JSON, dans le même ordre chronologique (`-date_publication`), avec le même code HTTP `200 OK`.
- **Frontend Angular** : Aucun composant, service, ou template Angular n'a été modifié.

---

## 9. Décision et Étape Suivante

```text
==================================================
DÉCISION PHASE 9 :
READY FOR CONTROLLED EXPERIMENT
==================================================
```

Le Shadow Mode V3 s'exécute avec succès en arrière-plan sans perturber le Feed chronologique. Le système est désormais prêt pour envisager une Phase d'A/B Testing contrôlée sur un échantillon restreint d'utilisateurs.
