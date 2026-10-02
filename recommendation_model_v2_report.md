# AYYOU — RAPPORT DU MODÈLE DE RECOMMANDATION V2 (PHASE 4.5)

## 1. Dataset

- **Nombre d'événements bruts enregistrés dans `VideoEventLog`** : 104 (contre 32 en V1, soit +225%)
- **Lignes de données nettoyées (`DatasetBuilder`)** : 104
- **Nombre de sessions distinctes (groupes de ranking)** : 12 (contre 5 en V1)
- **Nombre d'utilisateurs authentifiés distincts** : 5 (ID `#185`, `#184`, `#183`, `#182`, `#181`)
- **Nombre de sessions anonymes distinctes** : 7
- **Nombre de publications / vidéos représentées** : 8 (ID `#38` à `#45`)

---

## 2. Utilisateurs

La diversité des utilisateurs a été considérablement augmentée :
- **Utilisateurs authentifiés (5)** :
  - User `#185` (Modou Diop - Livreur Test)
  - User `#184` (Gérant Marché des Fruits)
  - User `#183` (Gérant Le Panier Tropical)
  - User `#182` (Gérant Fruits Frais Dakar)
  - User `#181` (Gérant Street Food Awa)
- **Visiteurs anonymes (7 sessions)** : `feed_session_anon_secA_101`, `feed_session_anon_secD_404`, `feed_session_anon_secE_505`, `feed_session_anon_secI_909`, `feed_session_anon_secJ_1010`, `feed_session_anon_secK_1111`.

---

## 3. Sessions

- **Total des sessions** : 12 sessions de navigation distinctes.
- **Isolisme par groupe** : Chaque événement appartient strictement à une session unique identifiée par `query_session_id`.

---

## 4. Vidéos

Répartition équilibrée de l'exposition et des interactions sur l'ensemble du catalogue vidéo actif (Publications `#38` à `#45`). Les vidéos ont accumulé à la fois des vues, des complétions, des zappes, des clics sur plats et des ajouts au panier.

---

## 5. Distribution des Targets

Le score de pertinence cible $Y$ sur le dataset V2 se répartit ainsi :

| Target Level | Interaction / Comportement | Nombre d'Événements | Pourcentage | Évolution vs V1 |
| :--- | :--- | :---: | :---: | :---: |
| **Target 0** | `SKIP` / Visionnage < 3s | 13 | 12,5% | +9 événements |
| **Target 1** | Vue partielle ($15\% \le \text{completion} < 90\%$) | 60 | 57,7% | +38 événements |
| **Target 2** | `COMPLETED` / Visionnage $\ge 90\%$ | 14 | 13,5% | +12 événements |
| **Target 3** | `LIKE` / `SHARE` (Social) | 8 | 7,7% | +6 événements |
| **Target 4** | `DISH_CLICK` / `CART_ADD` (Conversion) | 9 | 8,7% | +7 événements |
| **TOTAL** | | **104** | **100,0%** | **+72 événements** |

---

## 6. Features

Les 20 caractéristiques de la Whitelist sont maintenues sans fuite de données :
- `is_authenticated`, `user_account_age_days`, `user_total_orders`, `user_avg_order_amount`, `user_total_likes`, `user_total_events`, `user_avg_watch_time`, `user_avg_completion_rate`, `user_top_category_id`.
- `video_recency_hours`, `video_duration_seconds`, `video_total_likes`, `video_total_shares`, `dish_price`, `dish_category_id`, `resto_rating`, `resto_reviews_count`.
- `feed_position`, `hour_of_day`, `day_of_week`.

---

## 7. Data Leakage (Audit de Contrôle)

- **Variables explicatives $X$** : Les métriques directes post-interaction (`event_type`, `watch_time_seconds`, `completion_rate`, `is_skip`, `is_completed`) demeurent **exclues**.
- **Variables d'historique** : Les métriques de profil (`user_total_events`, `video_total_shares`, `dish_price`) reflètent les états historiques antérieurs et ne contiennent pas de fuite temporelle.

---

## 8. Train / Validation Split

- **Méthode de découpage** : `GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=42)`
- **Train Set** : **73 lignes** réparties sur **9 sessions distinctes**.
- **Validation Set** : **31 lignes** réparties sur **3 sessions distinctes** (`feed_session_auth_secC_303`, `feed_session_auth_secG_707`, `feed_session_auth_secH_808`).

> *Amélioration majeure vs V1 :* Le jeu de validation s'évalue désormais sur **3 sessions réelles distinctes** (31 d'items à classer) contre 1 seule session en V1.

---

## 9. LightGBM V2

- **Fichier du Modèle** : [`models/recommender/recommender_lgbm_v2.joblib`](file:///c:/Users/HP/Desktop/Ayyou-backend/models/recommender/recommender_lgbm_v2.joblib)
- **Fichier de Métadonnées** : [`models/recommender/recommender_lgbm_v2.json`](file:///c:/Users/HP/Desktop/Ayyou-backend/models/recommender/recommender_lgbm_v2.json)
- *Note :* La version V1 (`recommender_lgbm_v1.joblib`) a été **strictement conservée** à des fins de traçabilité.

---

## 10. Popularity Baseline

Évaluée sur les mêmes 3 sessions de validation (31 lignes) avec le tri par `video_total_likes`.

---

## 11 à 13. Résultats des Métriques (NDCG@5, NDCG@10, MRR)

| Modèle / Stratégie | NDCG@5 | NDCG@10 | MRR | Sessions de Test Evaluées |
| :--- | :---: | :---: | :---: | :---: |
| **Modèle V1 (Expérimental)** | 0,8730 | 0,8730 | 0,3333 | 1 |
| **Modèle LightGBM V2** | **0,7408** | **0,7659** | **0,2917** | **3** |
| **Popularity Baseline (sur V2 Val)** | 0,6721 | 0,7440 | 0,6667 | 3 |

*Analyse comparative :*
- Sur le critère de ranking des premiers résultats (**NDCG@5**), **LightGBM V2 (0,7408) surpasse la Popularity Baseline (0,6721)** de +6,87 points.
- Sur le critère **NDCG@10**, **LightGBM V2 (0,7659) surpasse également la Popularity Baseline (0,7440)**.
- Sur le critère **MRR**, la Popularity Baseline obtient 0,6667 contre 0,2917 pour V2.

---

## 14. Feature Importance (Gain)

L'enrichissement des données a permis à LightGBM V2 de commencer à apprendre de véritables poids de décision non-nuls :

| Caractéristique (Feature) | Importance (Gain) | Interprétation |
| :--- | :---: | :--- |
| `dish_price` | **5,2317** | Sensibilité au prix du plat présenté |
| `resto_reviews_count` | **4,9667** | Notoriété / Preuve sociale de l'établissement |
| `video_total_shares` | **1,4263** | Viralité et potentiel de partage du contenu |
| `dish_category_id` | **0,8334** | Appétence par catégorie culinaire |
| `user_total_events` | **0,6029** | Niveau d'engagement global du profil |

---

## 15. Comparaison V1 vs V2

- **Volume d'échantillon** : Passage de 32 événements (5 sessions) à **104 événements (12 sessions)**.
- **Diversité Utilisateurs** : Passage de 1 utilisateur authentifié à **5 utilisateurs authentifiés + 7 sessions anonymes**.
- **Apprentissage des caractéristiques** : V1 avait des poids à 0.0 ; V2 apprend désormais des signaux discriminants sur le prix, la catégorie et la notoriété des restaurants.

---

## 16. Limites Identifiées

- Échantillon de 12 sessions (3 sessions en validation).
- Catalogue restreint à 8 publications actives.
- Le modèle reste à un stade expérimental hors-ligne.

---

## 17. Tests Automatisés

```text
Ran 21 tests in 18.213s
OK
```
Toutes les suites de tests backend restent vertes.

---

## 18. État de Préparation pour la Suite (Conclusion Explicite)

Conformément à la grille de décision définie en Phase 4.5 :

> **ÉTAT B : "Les données permettent une première évaluation plus robuste, mais le modèle reste expérimental."**

- Le modèle V2 a été sérialisé et versionné.
- Le Feed de production demeure **100% CHRONOLOGIQUE ET INCHANGÉ**.
- Aucune intégration directe au Feed n'est effectuée à ce stade.
