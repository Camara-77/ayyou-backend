# AYYOU — MODE ACCÉLÉRATION : RAPPORT D'INTÉGRATION TECHNIQUE DU RECOMMANDER LIGHTGBM V3

**Projet** : AYYOU  
**Phase** : 7 — Intégration Technique et Entraînement Expérimental V3  
**Statut Modèle V3** : EXPERIMENTAL / OFFLINE ONLY (Non Production Ready)  
**Mode de Recommandation par Défaut** : `chronological`  
**Date** : 2 Octobre 2026  

---

## 1. OBJECTIF ET CADRE D'INTÉGRATION

Conformément aux directives du **MODE ACCÉLÉRATION**, cette phase a consisté à finaliser l'intégration technique de bout en bout du pipeline de recommandation LightGBM V3 sans attendre artificiellement l'accumulation de 1 000 événements.

> **RÈGLES ET GARANTIES DE SÉCURITÉ RESPECTÉES** :
> - **Données Réelles Uniques** : Seuls les 104 événements réels de télémétrie ont été utilisés. Aucune donnée synthétique ou artificielle n'a été créée.
> - **Modèle V2 Préservé** : `models/recommender/recommender_lgbm_v2.joblib` et `.json` sont conservés intacts comme référence offline.
> - **Feed de Production Inchangé** : `GET /api/catalog/feed/` demeure 100 % chronologique (`-date_publication`).
> - **Frontend Angular Inchangé** : Aucun composant frontend (`HomeComponent`, `FoodPostComponent`, `VideoTelemetryService`, etc.) n'a été modifié.
> - **Statut Modèle** : V3 est explicitement qualifié de **EXPERIMENTAL / OFFLINE ONLY** et n'est pas activé en production par défaut.

---

## 2. DATASET V3 ET ISOLATION TEMPORELLE

- **Événements bruts exploités** : 104 événements réels (`VideoEventLog`).
- **Sessions représentées** : 12 sessions (6 authentifiées, 6 anonymes).
- **Utilisateurs authentifiés** : 5.
- **Publications observées** : 8 sur 8 du catalogue actif.
- **Découpage Train / Validation** : `GroupShuffleSplit` basé sur `query_session_id`.
  - Train : 9 sessions (**73 lignes**)
  - Validation : 3 sessions (**31 lignes**)
  - Overlap de session Train/Val : **0**
- **Isolation Temporelle (Anti-Leakage)** : Règle $created\_at < T$ strictly appliquée. $X$ exclut `event_type`, `watch_time_seconds`, `completion_rate`, `is_skip`, `is_completed`.

---

## 3. RÉSULTATS D'ÉVALUATION DU MODÈLE V3 ET COMPARAISON

### A. Évaluation sur Jeu de Validation (3 sessions)

| Modèle / Système | NDCG@5 | NDCG@10 | MRR | Remarques |
|---|---|---|---|---|
| **V3 LightGBM (Expérimental)** | **0.4987** | **0.7149** | **0.5833** | Entraîné sur 73 lignes train réelles |
| **Popularity Baseline** | 0.6721 | 0.7440 | 0.6667 | Tri par `video_total_likes` |
| **V2 LightGBM (Référence Offline)** | 0.7408 | 0.7491 | 0.2917 | Référence historique V2 |

*Note sur la performance Train (In-Sample V3)* : NDCG@5 = 0.9298, NDCG@10 = 0.9604, MRR = 0.8889.

---

## 4. CARACTÉRISTIQUES DOMINANTES (FEATURE IMPORTANCE)

Selon le gain d'information LightGBM :
1. `user_avg_watch_time` (Gain: 90.02) — Contribution majeure au score.
2. `resto_reviews_count` (Gain: 30.15) — Signal de confiance établissement.
3. `user_total_events` (Gain: 13.31) — Niveau d'activité historique.
4. `video_duration_seconds` (Gain: 4.03) — Caractéristique de la vidéo.

*Avertissement* : La feature importance reflète la contribution dans l'arbre de décision et ne constitue pas une preuve de causalité comportementale.

---

## 5. ARCHITECTURE D'INTÉGRATION TECHNIQUE

### A. RecommendationScoringService (Support Multi-Modèles)
Le service de scoring `RecommendationScoringService` a été adapté pour accepter le paramètre `model_version`:
```python
results = RecommendationScoringService.score_candidates(
    publication_ids=[38, 39, 40, 41],
    user_id=181,
    session_id="sess_sim_01",
    model_version="v3" # ou "v2"
)
```

### B. Endpoint de Simulation (`POST /api/telemetry/scoring/simulate/`)
L'endpoint interne de simulation supporte la sélection explicite de la version du modèle :
```json
{
    "model_version": "v3",
    "publication_ids": [38, 39, 40, 41],
    "session_id": "sess_sim_01"
}
```
Support des versions : `"v3"`, `"v2"`, `"chronological"`.

### C. Feature Flag de Configuration (`RECOMMENDATION_MODE`)
- Fichier de configuration : `config/settings.py`
- Valeur par défaut : `RECOMMENDATION_MODE = 'chronological'` (Garantit que le Feed reste 100% chronologique).

---

## 6. TESTS UNITAIRES D'INTÉGRATION

53 tests unitaires couvrent l'intégralité du module de télémétrie et de recommandation :
- Chargement et métadonnées V3 (`test_v3_model_artifacts_exist`, `test_v3_metadata_status`)
- Coexistence sans écrasement de V2 et V3 (`test_scoring_service_v2_and_v3_coexistence`)
- Prédiction V3 (`test_scoring_candidates_with_v3`)
- Simulation API V3 et Chronologique (`test_simulation_endpoint_v3`, `test_simulation_endpoint_chronological`)
- Feature flag de sécurité par défaut (`test_default_recommendation_mode_is_chronological`)

Résultat : **53 / 53 PASS (100 % OK)**.

---

## 7. DÉCISION DE LA PHASE 7

> **DÉCISION SÉLECTIONNÉE** : **`V3 EXPERIMENTAL — CONTINUE EVALUATION`**

### Justification :
L'intégration technique de V3 est 100 % finalisée et fonctionnelle. Le modèle V3 est prêt à recevoir de nouvelles données réelles pour améliorer ses scores au fur et à mesure que la télémétrie s'accumule. Le Feed réel d'AYYOU demeure protégé en mode chronologique.
