# AYYOU — PREMIER MODÈLE DE RECOMMANDATION (PHASE 4)

## 1. Données

- **Nombre d'événements bruts dans `VideoEventLog`** : 32
- **Lignes nettoyées du dataset (`DatasetBuilder`)** : 32
- **Nombre de sessions distinctes (groupes de ranking)** : 5
- **Nombre d'utilisateurs distincts représentés** : 1 utilisateur authentifié (`#185` Modou Diop) + 3 profils de sessions anonymes
- **Nombre de publications / vidéos représentées** : 8 (ID `#38` à `#45`)

---

## 2. Features (Liste Whitelist)

Les 20 caractéristiques ($X$) autorisées et validées pour l'entraînement :

| Catégorie | Nom de la Feature | Type / Description |
| :--- | :--- | :--- |
| **USER** | `is_authenticated` | Binaire (0 ou 1) |
| **USER** | `user_account_age_days` | Ancienneté du compte en jours |
| **USER** | `user_total_orders` | Nombre total de commandes validées |
| **USER** | `user_avg_order_amount` | Montant moyen des commandes (€) |
| **USER** | `user_total_likes` | Nombre total de likes historiques |
| **USER** | `user_total_events` | Volume d'activité télémétrique total |
| **USER** | `user_avg_watch_time` | Temps moyen de visionnage (s) |
| **USER** | `user_avg_completion_rate` | Taux de complétion moyen historique |
| **USER** | `user_top_category_id` | ID de la catégorie la plus commandée |
| **CONTENT** | `video_recency_hours` | Ancienneté de la publication (heures) |
| **CONTENT** | `video_duration_seconds` | Durée totale du fichier vidéo (s) |
| **CONTENT** | `video_total_likes` | Nombre total de likes accumulés |
| **CONTENT** | `video_total_shares` | Nombre total de partages |
| **CONTENT** | `dish_price` | Prix du plat associé (€) |
| **CONTENT** | `dish_category_id` | ID de la catégorie du plat |
| **CONTENT** | `resto_rating` | Note moyenne de l'établissement |
| **CONTENT** | `resto_reviews_count` | Nombre d'avis de l'établissement |
| **CONTEXT** | `feed_position` | Rang de la carte dans le feed (0, 1, 2...) |
| **CONTEXT** | `hour_of_day` | Heure locale de l'interaction (0-23) |
| **CONTEXT** | `day_of_week` | Jour de la semaine (0-6) |

---

## 3. Target (`target_relevance`)

La variable cible $Y$ est calculée selon l'échelle expérimentale d'interaction :

- **Target 0 (Skip / Rejet)** : `is_skip == True` ou `watch_time < 3s` (4 événements, 12,5%)
- **Target 1 (Vue partielle / Neutre)** : Visionnage partiel $15\% \le \text{completion} < 90\%$ (22 événements, 68,8%)
- **Target 2 (Complétion / Intérêt implicite)** : `COMPLETED` ou $\text{completion} \ge 90\%$ (2 événements, 6,2%)
- **Target 3 (Engagement social)** : `LIKE` ou `SHARE` (2 événements, 6,2%)
- **Target 4 (Conversion commerciale)** : `DISH_CLICK` ou `CART_ADD` (2 événements, 6,2%)

> *Note :* Ce target constitue une première approximation heuristique de la pertinence comportementale et ne constitue pas une vérité scientifique absolue.

---

## 4. Data Leakage (Audit et Décisions)

Afin d'éliminer rigoureusement toute fuite d'information future (*data leakage*) :
- **Variables strictement exclues des features $X$** : `event_type`, `watch_time_seconds`, `completion_rate`, `is_skip`, `is_completed`.
  *Justification :* Ces valeurs mesurent le comportement observés POSTÉRIEUREMENT à la présentation de la vidéo. Elles servent exclusivement à composer le target $Y$.
- **Identifiants exclus** : `id`, `session_id`, `created_at`, `user`, `publication`.
- **Isolation du split Train/Validation** : Effectuée sur `query_session_id`. Aucune session n'est partagée entre l'entraînement et la validation.

---

## 5. Train / Validation Split

- **Méthode de découpage** : `GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=42)`
- **Train Set** : 27 lignes (4 sessions distinctes : `feed_session_anon_secA_101`, `feed_session_auth_secB_202`, `feed_session_anon_secD_404`, `feed_session_anon_secE_505`)
- **Validation Set** : 5 lignes (1 session distincte : `feed_session_auth_secC_303`)

---

## 6. Configuration du Modèle LightGBM

- **Algorithme** : `lightgbm.LGBMRanker`
- **Objectif (Objective)** : `lambdarank`
- **Métrique d'évaluation (Metric)** : `ndcg` (`eval_at=[5, 10]`)
- **Nombre d'arbres (`n_estimators`)** : 100
- **Taux d'apprentissage (`learning_rate`)** : 0,05
- **Feuilles par arbre (`num_leaves`)** : 31
- **Fixation de la graine aléatoire (`random_state`)** : 42

---

## 7. Résultats des Métriques d'Évaluation

Métriques mesurées sur l'ensemble de validation (1 session de test comprenant 5 interactions) :

- **NDCG@5** : **0,8730**
- **NDCG@10** : **0,8730**
- **MRR (Mean Reciprocal Rank)** : **0,3333**

---

## 8. Baseline de Popularité

Sur le même ensemble de validation, la baseline de popularité basée sur `video_total_likes` obtient :

- **NDCG@5** : **0,8730**
- **NDCG@10** : **0,8730**
- **MRR** : **0,3333**

---

## 9. Comparaison Objective

Sur cet échantillon de validation constitué d'une seule session de test (5 items), les scores du modèle LightGBM et de la Popularity Baseline sont identiques ($0,8730$ en NDCG@5 et $0,3333$ en MRR).
En raison du très faible nombre de sessions en jeu de validation ($N=1$), ces métriques reflètent la faisabilité technique de la boucle d'évaluation mais ne permettent pas d'établir une supériorité statistique du modèle.

---

## 10. Importance des Caractéristiques (Feature Importance - Gain)

En raison du nombre restreint de sessions d'entraînement ($N=4$), l'importance par gain de toutes les caractéristiques s'établit actuellement à $0,0000$. Le modèle a convergé sur des arbres de décision simplifiés.

---

## 11. Limites Identifiées

1. **Volume d'échantillon très restreint** : 32 événements répartis sur 5 sessions.
2. **Nombre réduit de vidéos** : 8 publications distinctes.
3. **Nombre réduit d'utilisateurs authentifiés** : 1 utilisateur authentifié.
4. **Validation limitée** : 1 seule session dans le fold de validation, limitant la portée statistique de NDCG.

---

## 12. Conclusion et Prochaines Étapes

- **Statut du Pipeline** : **VALIDÉ ET OPÉRATIONNEL HORS-LIGNE**. La commande `python manage.py train_recommender --save` fonctionne de bout en bout et génère un modèle sérialisé (`models/recommender/recommender_lgbm_v1.joblib`) ainsi que ses métadonnées versionnées (`models/recommender/recommender_lgbm_v1.json`).
- **Isolation du Production Feed** : **100% CONSERVÉE**. Le Feed vidéo reste 100% chronologique et inchangé.
- **Orientation future** : Continuer la collecte passive de télémétrie jusqu'à accumuler plusieurs centaines de sessions qualifiées d'utilisateurs réels avant d'envisager une première expérimentation A/B en production.
