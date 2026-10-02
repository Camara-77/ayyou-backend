# Phase 6.5 — Audit de Validation du Système de Recommandation IA

**Projet :** AYYOU  
**Date :** 1er Octobre 2026  
**Type de document :** Rapport d'Audit Technique Indépendant (Phase 6.5)  
**Statut :** Phase d'Audit Exclusive — Aucune modification du Feed live ni du Frontend  

---

## 1. Objectif

Cet audit a pour but d'évaluer de manière **factuelle, rigoureuse et neutre** les résultats de la Phase 6 (simulation du modèle LightGBM V2) afin de déterminer si le système de recommandation présente un niveau de fiabilité technique et statistique suffisant pour envisager une intégration progressive dans le Feed réel en Phase 7.

---

## 2. État du Système et Dépendances

L'audit confirme l'isolation absolue du système de recommandation IA par rapport à la production :
- **Endpoint du Feed Live (`GET /api/catalog/feed/`) :** Strictement inchangé. Conserve un tri 100% chronologique (`order_by('-date_publication')`).
- **Application Frontend Angular :** 0 modification. L'UX (`HomeComponent`, `FoodPostComponent`, scroll-snap, autoplay, audio) est totalement préservée.
- **Service de Scoring (`RecommendationScoringService`) :** Modoule isolé lisant le modèle sans interaction avec la base de production.

---

## 3. Modèle Audité

| Attribut | Valeur Audité |
|---|---|
| **Fichier Modèle** | `models/recommender/recommender_lgbm_v2.joblib` |
| **Fichier Métadonnées** | `models/recommender/recommender_lgbm_v2.json` |
| **Type de Modèle** | `LGBMRanker` (LightGBM LambdaMART) |
| **Objectif LightGBM** | `lambdarank`, metric: `ndcg`, `eval_at: [5, 10]` |
| **Nombre de Features** | 20 colonnes |
| **Date d'Entraînement** | 2026-10-01T22:05:38Z |
| **Dataset d'Origine** | 104 événements, 12 sessions, 5 utilisateurs, 8 publications |
| **Découpage Train / Val** | Train: 73 lignes (9 sessions) / Validation: 31 lignes (3 sessions) |
| **Méthode de Chargement** | Singleton / Cache via `joblib.load()` dans `RecommendationScoringService` |
| **Inférence** | `model.predict(X_scoring)` via DataFrame pandas structuré |

---

## 4. Features Utilisées

Le tableau ci-dessous recense l'intégralité des 20 features définies dans `FEATURE_COLUMNS` (`apps/telemetry/ml/dataset.py`) :

| Feature | Source | Disponible avant exposition ? | Utilisée au scoring ? | Remarque audit |
|---|---|:---:|:---:|---|
| `is_authenticated` | Profil Utilisateur | OUI | OUI | Valeur binaire (0 ou 1) |
| `user_account_age_days` | Profil Utilisateur | OUI | OUI | Nombre de jours depuis inscription |
| `user_total_orders` | Profil Utilisateur | OUI | OUI | Commandes passées payées/livrées |
| `user_avg_order_amount` | Profil Utilisateur | OUI | OUI | Montant moyen des commandes |
| `user_total_likes` | Profil Utilisateur / Télémétrie | OUI | OUI | Cumul historique des likes |
| `user_total_events` | Télémétrie | OUI | OUI | Cumul historique des événements |
| `user_avg_watch_time` | Télémétrie | OUI | OUI | Temps moyen de visionnage |
| `user_avg_completion_rate` | Télémétrie | OUI | OUI | Taux moyen de complétion |
| `user_top_category_id` | Commandes / Catalogue | OUI | OUI | ID catégorie la plus commandée |
| `video_recency_hours` | Catalogue | OUI | OUI | Heures depuis publication |
| `video_duration_seconds` | Catalogue | OUI | OUI | Durée de la vidéo |
| `video_total_likes` | Catalogue / Télémétrie | OUI | OUI | Nombre total de likes vidéo |
| `video_total_shares` | Catalogue / Télémétrie | OUI | OUI | Nombre total de partages vidéo |
| `dish_price` | Catalogue | OUI | OUI | Prix du plat associé |
| `dish_category_id` | Catalogue | OUI | OUI | ID de la catégorie du plat |
| `resto_rating` | Catalogue / Avis | OUI | OUI | Note moyenne de l'établissement |
| `resto_reviews_count` | Catalogue / Avis | OUI | OUI | Nombre d'avis sur l'établissement |
| `feed_position` | Contexte Exposition | OUI | OUI | Rang dans le feed proposé |
| `hour_of_day` | Contexte Temporel | OUI | OUI | Heure courante (0-23) |
| `day_of_week` | Contexte Temporel | OUI | OUI | Jour de la semaine (0-6) |

---

## 5. Audit Data Leakage (Fuite de Données)

### A. Strict Exclusion des variables post-exposition (Target Leakage)
- Les variables d'interaction directe (`event_type`, `watch_time_seconds`, `completion_rate`, `is_skip`, `is_completed`) sont **strictement exclues** de `FEATURE_COLUMNS`. Elles servent exclusivement à construire la cible `target_relevance` (0 à 4).

### B. Fuite Temporelle Indirecte Identifiée (Temporal Look-Ahead Leakage)
- **Localisation :** `apps/telemetry/data_preparation.py` dans `FeatureExtractor.extract_user_features()` et `extract_video_features()`.
- **Anomalie :** Lors de la construction du dataset d'apprentissage pour un événement `event_i` ayant eu lieu à la date $t_i$, la méthode `VideoEventLog.objects.filter(utilisateur=user)` agrège tous les événements de l'utilisateur **sans filtre sur `created_at <= t_i`**.
- **Impact :** L'historique d'un utilisateur à l'instant $t_i$ inclut ses interactions futures ($t > t_i$). Cela introduit un biais temporel lors de l'apprentissage et Surestime artificiellement la corrélation train/validation.
- **Correction requise pour le futur :** Ajouter le filtre temporel `created_at__lt=event.created_at` dans `DatasetBuilder`.

---

## 6. Audit de la Simulation Phase 6 (`simulate_feed.py`)

- **Candidats :** 8 publications réelles issues de la base SQLite (`PublicationFeed.objects.all()`).
- **IDs candidats :** `#38` à `#45`. Aucun candidat fictif.
- **Source des scores :** Inférence déterministe via `recommender_lgbm_v2.joblib`.
- **Tri :** Alignement décroissant exact (`results.sort(key=lambda x: x['predicted_score'], reverse=True)`).
- **Référence Chronologique :** Exactement conforme à la requête du Feed live (`-date_publication`).

---

## 7. Audit des Explications du Rapport Phase 6

Les explications formulées dans le rapport de simulation Phase 6 ont été auditées selon leur niveau de preuve :

| Affirmation de la Phase 6 | Données disponibles | Niveau de preuve | Justifiée ? | Analyse de l'Audit |
|---|---|:---:|:---:|---|
| *"Forte affinité démontrée pour la Cuisine Sénégalaise"* | `user_top_category_id` (basé sur commandes) | B (Déduite) | **NON** | Sur-interprétation. Le modèle attribue un score numérique global et ne fournit pas d'explication textuelle par catégorie. |
| *"Remontée suite aux ajouts au panier et partages"* | `user_total_events`, `video_total_shares` | C (Hypothétique) | **NON** | Inférence causale non démontrée. `user_total_events` contribue au score (gain 0.6029), mais la cause exacte par type d'action n'est pas isolée. |
| *"Rétrogradé car l'utilisateur a peu interagi avec la sous-catégorie poissons"* | Aucune feature de sous-catégorie poisson | D (Non justifiée) | **NON** | Affirmation sans fondement. Aucune feature "poisson" n'existe dans les 20 colonnes du modèle. |

> [!WARNING]
> Un score LightGBM est le résultat d'une somme de valeurs aux feuilles d'arbres de décision. Il ne constitue pas une justification causale. Toutes les formulations anthropomorphes doivent être éliminées.

---

## 8. Audit de l'Importance des Features

L'importance des features dans le modèle V2 (`recommender_lgbm_v2.json`) est mesurée par le **Gain total** (amélioration de la fonction de perte) :
1. `dish_price` : **5.2317** (71.1% du gain total)
2. `resto_reviews_count` : **4.9667** (67.5% du gain total)
3. `video_total_shares` : **1.4263** (19.4% du gain total)
4. `dish_category_id` : **0.8334** (11.3% du gain total)
5. `user_total_events` : **0.6029** (8.2% du gain total)
6. **15 autres features : 0.0000** (Gain nul)

### Constat d'Audit :
Seules 5 features sur 20 contribuent au modèle. Les features de profil utilisateur (`is_authenticated`, `user_total_orders`, `user_avg_watch_time`, `user_top_category_id`) ont toutes un **gain strictement nul (0.0)**.

---

## 9. Audit du Cold Start et Robustesse

### A. Comportement Cold Start (Visiteur Anonyme / Nouvel Utilisateur)
- **Stabilité :** 0 exception, 0 `NaN`, 0 `Inf`.
- **Fonctionnement du Fallback :** Pour un utilisateur anonyme ou nouveau, les features utilisateur valent 0/NULL. Les scores sont déterminés exclusivement par `dish_price`, `resto_reviews_count` et `video_total_shares`.

### B. Traitement des Nouveaux Contenus (Cold Start Produit/Restaurant)
- Une vidéo récente publiée par un nouveau restaurant (`resto_reviews_count=0`, `video_total_shares=0`) reçoit un score artificiellement bas.
- **Risque d'Audit :** Présence d'un **biais de popularité fort (Popularity Bias)** qui pénalise systématiquement les nouveautés du catalogue.

---

## 10. Audit de la Personnalisation (Expérience Contrôlée)

Une expérience contrôlée a comparé les prédictions du même pool de 8 vidéos sur 3 profils distincts :
- **Profil A (Modou Diop #185) :** Historique riche (104 événements)
- **Profil B (Marché des Fruits #184) :** Faible historique (1 événement)
- **Profil C (Anonyme #999) :** Cold Start (0 événement)

### Résultats Électriques :
- **Top 3 Profil A :** `['45', '41', '42']`
- **Top 3 Profil B :** `['45', '41', '38']`
- **Top 3 Profil C (Anonyme) :** `['45', '41', '42']`

> [!IMPORTANT]
> **Le Top 3 de l'utilisateur authentifié A (#185) et du visiteur anonyme C (#999) est 100% IDENTIQUE.**
> Cela démontre que le pouvoir de personnalisation du modèle V2 est actuellement **très faible**, car le modèle est quasi-intégralement dominé par les caractéristiques des produits/restaurants et non par le profil utilisateur.

---

## 11. Résultats Statistiques et Métriques V2

### A. Données Réelles en Base
- **Événements totaux :** 104
- **Sessions distinctes :** 12 (6 authentifiées, 6 anonymes)
- **Utilisateurs authentifiés représentés :** 5
- **Vidéos candidates :** 8

### B. Évaluation Comparative (Validation Split)

| Modèle | NDCG@5 | NDCG@10 | MRR (Mean Reciprocal Rank) | Sessions évaluées |
|---|:---:|:---:|:---:|:---:|
| **LightGBM LambdaMART V2** | **0.7408** | **0.7659** | **0.2917** | 2 |
| **Popularity Baseline** | **0.6721** | **0.7440** | **0.6667** | 2 |

### Analyse des Métriques :
- LightGBM V2 dépasse la popularité en NDCG (+0.0687 sur NDCG@5).
- **Faiblesse Majeure sur le MRR :** Le MRR de LightGBM (**`0.2917`**) est nettement **inférieur à la popularité (`0.6667`)**. La popularité place immédiatement les plats fortement convertis en position #1 ou #2, alors que LightGBM les relègue parfois en position #3 ou #4.
- **Limite Statistique Réhibitoire :** L'évaluation ne repose que sur **2 sessions de validation**. Il est statistiquement impossible d'en déduire une supériorité générale du modèle.

---

## 12. Résultats de Stabilité et Robustesse

- **Stabilité (Reproductibilité) :** 3 exécutions consécutives du scoring sur le même profil donnent des résultats **100% identiques** (`Run 1 == Run 2 == Run 3 : True`).
- **Robustesse :** Traitement correct des cas limites (ID utilisateur inexistant, liste de candidats vide) sans plantage.

---

## 13. Audit des Propositions de la Phase 7

| Proposition Phase 6 | Justification | Risque Identifié | Décision Audit |
|---|---|---|---|
| Endpoint `/api/catalog/feed/recommendations/` | Isolation API | Duplication de la sérialisation | Acceptable pour tests |
| A/B Testing en ligne | Comparaison de cohortes | Prématuré sans volume d'utilisateurs | **Refusé à ce stade** |
| Formule Hybride $0.80 \text{LGBM} + 0.20 \text{Récence}$ | Atténuer le biais popularité | **Pondération 100% arbitraire** non validée | **Refusé (Hypothèse non prouvée)** |
| Fallback < 3 événements | Protection Cold Start | Seuil arbitraire | À revoir |

---

## 14. Synthèse de Classification des Éléments du Système

Chaque composant audité est classé selon les 4 catégories officielles :

- **Catégorie A — VALIDÉ TECHNIQUEMENT :**
  - Architecture du service `RecommendationScoringService` (Singleton, cache, typage, gestion d'erreurs).
  - Isolation du Feed de production (`GET /api/catalog/feed/`) et du Frontend Angular.
  - Déterminisme et stabilité du scoring (100% reproductible).
  - Exécution des 37 tests unitaires Django (`apps.telemetry`).

- **Catégorie B — VALIDÉ MAIS EXPÉRIMENTAL :**
  - Pipeline ML LambdaMART (`train_recommender.py`, `evaluate_recommender.py`).
  - Intégration des features de catalogue (`dish_price`, `resto_reviews_count`).
  - Simulation hors-feed CLI (`simulate_recommendation_feed.py`).

- **Catégorie C — À SURVEILLER :**
  - Risque de biais de popularité (Popularity Bias) étouffant les nouvelles publications.
  - Faiblesse du score MRR (`0.2917` vs `0.6667` baseline).
  - Pondération arbitraire envisagée pour le mix récence/IA.

- **Catégorie D — À CORRIGER AVANT INTÉGRATION :**
  - **Fuite Temporelle (Temporal Look-Ahead Leakage) :** Filtrer les événements passés uniquement (`created_at__lt=event.created_at`) dans `DatasetBuilder`.
  - **Volume de Données Insuffisant :** Seulement 104 événements et 12 sessions en base.
  - **Personnalisation Insuffisante :** Les features de profil utilisateur ont un gain nul (0.0).

---

## 15. Décision Technique Concernant la Phase 7

Sur la base des éléments factuels et empiriques rassemblés pendant cet audit :

> [!IMPORTANT]
> **DÉCISION TECHNIQUE : OPTION 3**  
> **"Les données sont actuellement insuffisantes pour préparer une Phase 7 ; continuer l'accumulation de télémétrie."**

### Justification Technique de la Décision :
1. **Insuffisance du Volume de Télémétrie :** 104 événements sur 12 sessions ne permettent pas à un algorithme d'apprentissage supervisé de type LambdaMART d'apprendre les préférences des utilisateurs (15 features utilisateur sur 20 ont un gain de 0.0).
2. **Absence de Personnalisation Réelle :** L'expérience contrôlée prouve qu'un utilisateur riche en historique et un utilisateur anonyme reçoivent quasiment le même classement (Top 3 identique).
3. **MRR Inférieur à la Popularité :** Le modèle dégrade la rapidité d'accès aux contenus à très forte conversion par rapport à une simple règle de popularité.
4. **Correction Préalable du Leakage Temporel :** Le pipeline de préparation des données doit être corrigé avant de procéder au réentraînement ultérieur du modèle V3.

### Recommandations pour la Suite :
1. Poursuivre la collecte de télémétrie en production sans modifier le Feed.
2. Corriger le filtrage temporel dans `DatasetBuilder`.
3. Ré-évaluer un modèle V3 lorsque la base de télémétrie aura atteint un seuil minimal de 1 000 événements et 100 sessions distinctes.
