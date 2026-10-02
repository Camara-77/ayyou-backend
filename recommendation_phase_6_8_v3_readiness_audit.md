# Phase 6.8 — Audit de Préparation Avant Entraînement du Modèle LightGBM V3

**Projet :** AYYOU  
**Date :** 1er Octobre 2026  
**Type de document :** Audit Indépendant de Préparation V3 (Phase 6.8)  
**Statut :** Audit de Préparation Seul — Aucun Réentraînement de V3 / Aucun Changement du Feed Live  

---

## 1. Volume Actuel

- **Nombre d'événements totaux en base (`VideoEventLog`) :** `104`
- **Nombre de sessions distinctes :** `12`
- **Utilisateurs authentifiés distincts :** `5`
- **Sessions anonymes :** `6`
- **Sessions avec utilisateur connecté :** `6`
- **Publications actives suivies :** `8`

### Évaluation par rapport aux objectifs indicatifs V3 :
- **Objectif Événements :** 1 000 → Progression actuelle : **`10.4%`** (`104 / 1 000`)
- **Objectif Sessions :** 100 → Progression actuelle : **`12.0%`** (`12 / 100`)

---

## 2. Diversité des Utilisateurs

| Critère d'Activité Utilisateur | Compte Observé | Analyse de Répartition |
|---|:---:|---|
| Utilisateurs authentifiés ayant $\ge 1$ événement | **5** | Faible nombre d'utilisateurs distincts. |
| Utilisateurs authentifiés ayant $\ge 5$ événements | **5** | Tous les utilisateurs ont fait plus de 5 actions. |
| Utilisateurs authentifiés ayant $\ge 10$ événements | **3** | Activité concentrée sur 3 utilisateurs majeurs. |

> [!WARNING]
> Avec seulement 5 utilisateurs authentifiés représentés dans l'ensemble de la base, les données manquent de diversité inter-individuelle. Le modèle risque d'apprendre des spécificités individuelles au lieu de motifs généralisables.

---

## 3. Diversité des Sessions

| Critère d'Activité Session | Compte Observé | Pourcentage des Sessions |
|---|:---:|:---:|
| Sessions ayant $\ge 3$ événements | **12** | 100.0% |
| Sessions ayant $\ge 5$ événements | **11** | 91.7% |
| Sessions ayant $\ge 10$ événements | **5** | 41.7% |

---

## 4. Diversité des Publications

L'analyse de l'activité sur l'ensemble des 8 publications du catalogue AYYOU donne les métriques suivantes :

| Pub ID | Titre / Produit | Impressions | Watch | Completed | Likes | Shares | Cart Add | Dish Click | Total Events |
|---|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **#45** | Tacos Poulet Mariné | 3 | 3 | 2 | 1 | 0 | 1 | 0 | **19** |
| **#44** | Mérou Thiof Entier Braisé | 3 | 3 | 0 | 1 | 0 | 0 | 0 | **11** |
| **#43** | Mbakhalou Saloum Traditionnel | 3 | 3 | 1 | 0 | 1 | 0 | 0 | **12** |
| **#42** | Double Smash Cheeseburger | 3 | 3 | 1 | 1 | 0 | 2 | 1 | **17** |
| **#41** | Thiéboudienne Rouge Penda Mbaye | 2 | 2 | 0 | 0 | 0 | 0 | 2 | **11** |
| **#40** | Dibi Agneau Oignons & Alloco | 3 | 2 | 2 | 0 | 1 | 0 | 0 | **12** |
| **#39** | Dibi Poulet Gourmet | 3 | 3 | 0 | 0 | 0 | 1 | 1 | **9** |
| **#38** | Dibi Agneau Haoussa | 4 | 4 | 1 | 2 | 1 | 1 | 0 | **13** |
| **Total** | **8 Publications** | **24** | **23** | **7** | **5** | **3** | **5** | **4** | **104** |

- **Publications jamais observées :** `0`
- **Couverture du catalogue :** 100% des publications actives ont été vues et ont reçu des interactions.

---

## 5. Distribution des Événements par Type

| Type d'Événement (`event_type`) | Nombre | Pourcentage | Signification Métier |
|---|---:|---:|---|
| **IMPRESSION** | 24 | 23.1% | Exposition à l'écran |
| **PLAY** | 24 | 23.1% | Démarrage de lecture |
| **WATCH** | 23 | 22.1% | Visionnage continu (Heartbeat) |
| **COMPLETED** | 7 | 6.7% | Complétion vidéo (>= 90%) |
| **SKIP** | 7 | 6.7% | Zappe rapide (< 3s) |
| **CART_ADD** | 5 | 4.8% | Conversion panier |
| **LIKE** | 5 | 4.8% | Signal social positif |
| **DISH_CLICK** | 4 | 3.8% | Consultation fiche produit |
| **SHARE** | 3 | 2.9% | Partage social |
| **PAUSE** | 2 | 1.9% | Pause de lecture |
| **Total** | **104** | **100.0%** | **Signaux forts (LIKE, SHARE, CART, CLICK, COMPLETED) = 23.1%** |

---

## 6. Qualité des Données

- **Événements valides (`TelemetryDataCleaner.is_valid_event`) :** `104 / 104` (**100.0%**)
- **Événements rejetés / invalides :** `0` (0.0%)
- **Taux de données valides :** **100.0%**
- **Événements sans `session_id` :** `0`
- **Événements sans `publication_id` :** `0`
- **Watch time négatif :** `0`
- **Completion rate hors [0, 1] :** `0`

---

## 7. Audit Temporel et Data Leakage

- **Correction Temporelle (Phase 6.6) :** Toujours active et vérifiée dans `data_preparation.py`.
- **Règle `created_at < T` :** Appliquée inconditionnellement à toutes les agrégations de features d'antécédents (`extract_user_features` et `extract_video_features`).
- **Audit des Variables Cibles :** `event_type`, `watch_time_seconds`, `completion_rate`, `is_skip`, `is_completed` sont strictement maintenues dans la variable cible $Y$ et exclues du vecteur $X$.
- **Validation Automatée :** Testée et validée par `apps/telemetry/tests/test_temporal_leakage.py` (4 tests OK).

---

## 8. Distribution de la Variable Cible (Target Relevance Score)

Le label de pertinence $Y$ calculé par `DatasetBuilder.compute_relevance_label` (0 à 4) présente la distribution suivante :

| Target Relevance Label | Signification | Nombre | Pourcentage |
|---|---|---:|---:|
| **Target 0** | Skip / Intérêt nul (< 3s) | 13 | 12.5% |
| **Target 1** | Vue partielle (< 50%) | 60 | **57.7%** |
| **Target 2** | Vue complète (>= 90% / COMPLETED) | 14 | 13.5% |
| **Target 3** | Engagement social (LIKE / SHARE) | 8 | 7.7% |
| **Target 4** | Conversion commerciale (CART_ADD / DISH_CLICK) | 9 | 8.7% |
| **Total** | | **104** | **100.0%** |

> [!NOTE]
> Le Target 1 (vue partielle) domine largement le jeu de données avec **57.7%** des lignes. Les conversions à forte valeur (Target 3 et 4) représentent conjointement 16.4% du dataset.

---

## 9. Distribution des Features & Potentiel de Personnalisation

- **Features Catalogue (`dish_price`, `resto_reviews_count`, `video_total_shares`) :** Présentent une bonne variance et permettent de différencier les vidéos.
- **Features Profil Utilisateur (`user_total_orders`, `user_avg_watch_time`, `user_top_category_id`) :** En raison du faible nombre d'utilisateurs (5 utilisateurs), la variance des features utilisateur reste extrêmement faible.
- **Potentiel de Personnalisation Actuel :** Faible. Les arbres de décision de LightGBM continueraient de favoriser presque exclusivement les caractéristiques vidéo/restaurant par rapport aux caractéristiques utilisateur.

---

## 10. Faisabilité du Découpage Train / Validation (GroupShuffleSplit)

Une simulation du découpage par groupes de sessions (`query_session_id`) avec `test_size=0.2` et `random_state=42` donne les résultats suivants :
- **Jeu d'Entraînement (Train) :** 73 lignes de données (**9 sessions**)
- **Jeu de Validation (Validation) :** 31 lignes de données (**3 sessions**)

### Évaluation Critique :
Une validation s'appuyant sur seulement **3 sessions de test** est statistiquement trop vulnérable à la variance aléatoire. Une fluctuation sur une seule session de test modifierait radicalement le score NDCG/MRR.

---

## 11. Comparaison avec la Référence V2

- **Rappel Métriques V2 (Modèle sur 104 events avec ancienne méthode) :**
  - LightGBM V2 : `NDCG@5 = 0.7408` | `NDCG@10 = 0.7659` | `MRR = 0.2917`
  - Popularity Baseline : `NDCG@5 = 0.6721` | `NDCG@10 = 0.7440` | `MRR = 0.6667`
- **Objectif pour V3 :** Le futur modèle V3 devra surpasser le MRR de la popularité (`0.6667`) tout en maintenant un NDCG@5 supérieur à `0.75` sur un échantillon de validation contenant au moins **20+ sessions de test distinctes**.

---

## 12. Grille de Évaluation de Préparation V3

| Critère d'Évaluation | Catégorie Attribuée | Justification de l'Audit |
|---|:---:|---|
| **1. Volume Global** | **D — Insuffisant** | 104 événements (10.4% du seuil 1 000). |
| **2. Diversité Utilisateurs** | **D — Insuffisant** | Seulement 5 utilisateurs authentifiés représentés. |
| **3. Diversité Sessions** | **D — Insuffisant** | 12 sessions au total (12.0% du seuil 100). |
| **4. Diversité Publications** | **B — Validé Expérimental** | 8/8 publications suivies et observées. |
| **5. Diversité Événements** | **A — Validé Technique** | Tous les types d'événements sont représentés (23.1% signaux forts). |
| **6. Qualité des Données** | **A — Validé Technique** | 100% de données valides (0 erreur, 0 date manquante). |
| **7. Qualité Temporelle** | **A — Validé Technique** | Règle `created_at < T` active et testée. |
| **8. Isolation Data Leakage** | **A — Validé Technique** | Aucune variable post-exposition dans X. |
| **9. Distribution Target** | **C — À Surveiller** | Concentration de 57.7% sur le Target 1. |
| **10. Faisabilité Train/Val** | **D — Insuffisant** | Seulement 3 sessions dans le jeu de validation. |
| **11. Potentiel Personnalisation**| **D — Insuffisant** | Nombre d'utilisateurs trop restreint pour différencier les profils. |

---

## 13. Décision Technique Officielle Concernant V3

Sur la base des mesures empiriques de la base de données :

> [!IMPORTANT]
> **DÉCISION TECHNIQUE : OPTION B**  
> **"Les données nécessitent encore une accumulation avant l'entraînement V3."**

### Justification Détaillée :
1. Bien que le pipeline de données soit **techniquement irréprochable** (100% de données valides, 0 fuite temporelle, 0 data leakage), le volume (104 événements sur 12 sessions) et la diversité utilisateur (5 utilisateurs) restent **trop faibles**.
2. Entraîner le modèle V3 prématurément sur 9 sessions train provoquerait un **sur-apprentissage (overfitting) massif** et ne produirait pas d'amélioration généralisable par rapport à V2.
3. La validation sur 3 sessions seulement ne permettrait pas de mesurer scientifiquement la performance du modèle.

---

## 14. Conditions et Prochaines Étapes Recommandées

1. **Continuer la collecte passive de télémétrie** en production avec le Feed chronologique actuel.
2. **Ré-exécuter l'audit de préparation Phase 6.8** dès que la base aura atteint la tranche de **500 à 1 000 événements de télémétrie**.
3. **Préserver le modèle V2** dans `models/recommender/recommender_lgbm_v2.joblib` sans modification.
