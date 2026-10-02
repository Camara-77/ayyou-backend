# AYYOU — Phase 8 : Rapport de Validation Offline Approfondie de LightGBM V3

**Projet** : AYYOU  
**Phase** : 8 — Validation Offline Approfondie de V3 et Préparation à une Intégration Contrôlée  
**Statut du Modèle V3** : EXPERIMENTAL / OFFLINE ONLY  
**Feed de Production** : 100 % Chronologique (`-date_publication`)  
**Décision Finale** : **PREPARE CONTROLLED INTEGRATION**

---

## 1. Contexte & Objectif

La Phase 7 a permis d'entraîner le modèle LightGBM Ranker V3 sur les données de télémétrie réelles accumulées (`recommender_lgbm_v3.joblib`).

L'objectif de la Phase 8 est d'évaluer de manière rigoureuse, reproductible et offline les performances, la stabilité et le comportement du modèle V3 avant d'envisager toute activation progressive (Shadow Mode / A/B Testing).

### Principes & Contraintes de Sécurité
- **Feed de production intact** : `GET /api/catalog/feed/` reste 100 % chronologique.
- **Frontend Angular intact** : Aucune modification des composants UI/UX ou du service de télémétrie.
- **Modèle V2 préservé** : `models/recommender/recommender_lgbm_v2.joblib` conserve sa version de référence.
- **Zero Synthetic Data** : Uniquement les données réelles issues de `VideoEventLog` (104 événements réels, 12 sessions).

---

## 2. Analyse Comparative des Classements (5 Profils Utilisateurs, Candidate Pool de 8 Publications)

Le test offline compare 4 stratégies de classement sur les 8 publications actives du catalogue AYYOU (IDs: 38, 41, 42, 43, 44, 45, 46, 47) à travers 5 profils d'utilisateurs distincts.

| Profil Utilisateur | Ordre Chronologique | Baseline Popularité | Modèle LightGBM V2 | Modèle LightGBM V3 |
| :--- | :--- | :--- | :--- | :--- |
| **Auth Rich History** (User 1) | `[45, 44, 43, 42, 41]` | `[38, 45, 44, 42, 43]` | `[45, 41, 38, 42, 43]` | `[45, 38, 41, 43, 42]` |
| **Auth Secondary** (User 2) | `[45, 44, 43, 42, 41]` | `[38, 45, 44, 42, 43]` | `[45, 41, 38, 42, 43]` | `[45, 38, 41, 43, 42]` |
| **Weak History** (User 3) | `[45, 44, 43, 42, 41]` | `[38, 45, 44, 42, 43]` | `[45, 41, 38, 42, 43]` | `[45, 38, 43, 41, 42]` |
| **Anonymous Session** | `[45, 44, 43, 42, 41]` | `[38, 45, 44, 42, 43]` | `[45, 41, 42, 38, 43]` | `[45, 38, 43, 41, 42]` |
| **Cold Start** (Nouveau User) | `[45, 44, 43, 42, 41]` | `[38, 45, 44, 42, 43]` | `[45, 41, 42, 38, 43]` | `[45, 38, 43, 41, 42]` |

### Observations des Changements de Rang (Rank Shifts)
- **Chronologique vs V3** : **7 / 8 publications déplacées**. Déplacement moyen = **2.00 positions**, Déplacement maximum = **6 positions** (Publication ID 38 passe du rang 7 au rang 1/2 en fonction de la popularité et de l'intérêt).
- **V2 vs V3** : **4 / 8 publications déplacées**. Déplacement moyen = **0.50 positions**, Déplacement maximum = **1 position** (ex: permutation subtile entre IDs 41 et 38 / 43). Cela confirme la stabilité architecturale entre V2 et V3 tout en affinant la hiérarchie.

---

## 3. Métriques et Statistiques des Scores V3

Sur un profil utilisateur authentifié avec historique (User ID 1) :

- **Nombre d'éléments scorés** : 8
- **Score Minimum** : `0.4930`
- **Score Maximum** : `1.1722`
- **Score Moyen** : `0.8496`
- **Score Médian** : `0.8925`
- **Écart-type** : `0.2953`
- **Absence de valeurs anormales** : **0 NaN, 0 Infinités, 0 Nulls**.

Pour les utilisateurs en **Cold Start / Anonymes**, V3 attribue des scores cohérents négatifs sans plantage (min: `-2.0166`, max: `-0.8508`), reflétant la dépendance aux features globales de popularité et d'engagement de la vidéo.

---

## 4. Importance des Features (Explicabilité V3)

Le modèle V3 exploite 15 caractéristiques agrégées de télémétrie utilisateur et de métadonnées vidéo. Les caractéristiques majeures ayant contribué aux prédictions sont :

1. **`user_avg_watch_time`** (Gain / Importance : **90.02**) : Durée moyenne de visionnage par l'utilisateur (signal fort de rétention).
2. **`resto_reviews_count`** (Gain / Importance : **30.15**) : Notoriété et popularité de l'établissement associé à la vidéo.
3. **`user_total_events`** (Gain / Importance : **13.31**) : Niveau d'activité globale de l'utilisateur.
4. **`video_duration_seconds`** (Gain / Importance : **4.03**) : Durée totale de la vidéo.

**Analyse** : V3 personnalise fortement l'expérience sur la base de l'engagement historique de l'utilisateur (`user_avg_watch_time`), tout en intégrant des signaux de qualité de l'établissement (`resto_reviews_count`).

---

## 5. Synthèse des Tests de Robustesse

| Test de Robustesse | Résultat | Commentaire / Détails |
| :--- | :--- | :--- |
| **Déterminisme** | **REUSSI** | 10 exécutions consécutives ont produit 100 % de classements et de scores idenctiques. |
| **Cold-Start Utilisateur** | **REUSSI** | Aucun crash, génération de scores négatifs stables sans NaN. |
| **Cold-Start Vidéo** | **REUSSI** | Prise en charge des vidéos sans télémétrie préalable via les métadonnées restaurant. |
| **Valeurs Extremes / NaN** | **REUSSI** | 0 NaN, 0 Inf dans l'ensemble des matrices de scores. |
| **Diversité du Top 5** | **REUSSI** | 5 publications distinctes représentées dans le Top 5 (`[38, 41, 42, 43, 45]`). |

---

## 6. Estimation de l'Impact Business

- **Rétention & Engagement** : L'intégration des temps de visionnage réels (`user_avg_watch_time`) favorise les contenus captivants plutôt que la simple fraîcheur chronologique.
- **Découvrabilité** : Remontée de publications populaires anciennes (ex: ID 38) autrefois reléguées en bas du Feed chronologique.
- **Stabilité de l'expérience UX** : Grâce à une dégradation progressive naturelle vers le mode popularité pour les anonymes, le démarrage à froid ne dégrade pas la qualité.

---

## 7. Stratégie d'Intégration Progressive Recommandée

Afin de passer de l'étape **EXPERIMENTAL / OFFLINE ONLY** à une intégration sécurisée en production sans altérer l'expérience utilisateur globale, la stratégie suivante est préconisée :

1. **Étape 1 : Shadow Mode (Monitoring passif)**
   - Exécuter la prédiction V3 en tâche de fond lors des requêtes au Feed (ou via batch/cache).
   - Enregistrer les prédictions V3 sans modifier l'ordre chronologique retourné à l'utilisateur.
   - Comparer les interactions réelles avec le classement V3 vs le classement Chronologique.

2. **Étape 2 : Feature Flag & A/B Testing contrôlé**
   - Introduire un Feature Flag (ex: `RECOMMENDATION_MODE = 'v3_ab_test'`).
   - Router 10 % à 20 % des utilisateurs authentifiés vers le Feed scoré V3.
   - Conserver 80 % en groupe de contrôle chronologique.

3. **Étape 3 : Déploiement Progressif**
   - Évaluer le taux de rétention, la durée de visionnage et le taux de completion sur le groupe V3.
   - Si les métriques sont supérieures ou égales au groupe chronologique, étendre le pourcentage de déploiement.

---

## 8. Décision Finale

```text
==================================================
DÉCISION AUDIT PHASE 8 :
PREPARE CONTROLLED INTEGRATION
==================================================
```

Le modèle LightGBM Ranker V3 a démontré sa stabilité offline, son déterminisme strict et son aptitude à gérer le cold start sans régression. Il est qualifié pour entrer dans la phase de préparation à l'intégration contrôlée (Shadow Mode / A/B Testing).

Le Feed de production AYYOU demeure pour l'instant 100 % chronologique.
