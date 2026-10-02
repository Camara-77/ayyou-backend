# DOCUMENTATION TECHNIQUE — ENTRAÎNEMENT ET ÉVALUATION DU MODÈLE DE RECOMMANDATION (PHASE 3)

## 1. VUE D'ENSEMBLE

La Phase 3 implémente l'infrastructure d'entraînement et d'évaluation hors-ligne du modèle de recommandation pour les vidéos AYYOU.
Cette implémentation repose sur le modèle de Ranking Learning-to-Rank **LightGBM (LambdaMART / `objective='lambdarank'`)**.

> **IMPORTANT :**
> - La Phase 3 est **100% isolée** du système de production.
> - **Aucune modification** n'a été apportée au Feed vidéo en direct, à `HomeComponent`, `FoodPostComponent`, la lecture vidéo, le scroll ou la gestion du son.
> - Le modèle n'est **pas connecté au Feed client** et n'influence **aucune décision en direct**.
> - En l'absence d'événements de télémétrie réels en base de données, **aucun faux modèle n'a été pré-entraîné artificiellement**.

---

## 2. ARCHITECTURE ET MODULES ML

L'ensemble de la logique d'entraînement et d'évaluation réside dans le package Python de backend `apps/telemetry/ml/` :

```
apps/telemetry/ml/
├── __init__.py
├── dataset.py                # Extraction, filtrage des features (Whitelist), gestion des fuites & splitting par session
├── train_recommender.py      # Entraînement LightGBM LambdaMART & sérialisation Joblib
└── evaluate_recommender.py   # Évaluation hors-ligne (NDCG@5, NDCG@10, MRR) & comparaison baseline de popularité
```

Une commande de gestion Django dédiée a également été créée :
```bash
python manage.py train_recommender [--save] [--model-path PATH] [--test-size FLOAT]
```

---

## 3. CALCUL DE LA PERTINENCE CIBLE ($Y$) ET LISTE BLANCHE DE FEATURES ($X$)

### 3.1 Score de pertinence cible (Target Relevance $Y$)
Le score de pertinence d'une interaction vidéo est calculé à partir des événements comportementaux observés au cours de la session :

$$\text{Relevance} = (\text{watch\_time\_seconds} \times 0.1) + (\text{completion\_rate} \times 2.0) + (1.0 \text{ si LIKE}) + (2.0 \text{ si DISH\_CLICK}) + (4.0 \text{ si CART\_ADD}) + (3.0 \text{ si SHARE}) - (1.5 \text{ si SKIP})$$

*Remarque :* Le score final est tronqué à 0.0 au minimum.

### 3.2 Feature Whitelist ($X$) et Prévention des Fuites de Données
Pour garantir l'absence totale de fuite de données (*data leakage*), les colonnes servant à déduire le score $Y$ (ou générées postérieurement à l'interaction) sont strictement exclues de l'ensemble de caractéristiques $X$ :

| Statut | Nom de la Feature / Colonne | Description / Justification |
| :--- | :--- | :--- |
| **Exclus ($Y$ / Leak)** | `event_type`, `watch_time_seconds`, `completion_rate`, `is_skip`, `is_completed` | Utilises pour calculer la variable cible $Y$. Inconnu au moment de recommander. |
| **Exclus (IDs non-généralisables)** | `id`, `session_id`, `created_at`, `user`, `publication`, `query_session_id` | Métadonnées de session / identifiants uniques. (`query_session_id` est uniquement utilisé pour grouper la répartition en folds). |
| **Autorisé ($X$ Whitelist)** | `publication_likes_count` | Popularité historique de la vidéo |
| **Autorisé ($X$ Whitelist)** | `publication_views_count` | Impressions historiques de la vidéo |
| **Autorisé ($X$ Whitelist)** | `publication_shares_count` | Partages historiques de la vidéo |
| **Autorisé ($X$ Whitelist)** | `publication_age_days` | Ancienneté de la vidéo (fraîcheur du contenu) |
| **Autorisé ($X$ Whitelist)** | `publication_price` | Prix du plat associé |
| **Autorisé ($X$ Whitelist)** | `publication_has_discount` | Présence d'une réduction |
| **Autorisé ($X$ Whitelist)** | `publication_discount_percent` | Pourcentage de réduction |
| **Autorisé ($X$ Whitelist)** | `user_total_events` | Niveau d'activité global de l'utilisateur |
| **Autorisé ($X$ Whitelist)** | `user_like_rate` | Taux d'appétence aux likes de l'utilisateur |
| **Autorisé ($X$ Whitelist)** | `user_avg_watch_time` | Temps de visionnage moyen historique du profil |
| **Autorisé ($X$ Whitelist)** | `user_cart_add_rate` | Taux de conversion panier historique du profil |
| **Autorisé ($X$ Whitelist)** | `session_event_index` | Rang / position de la recommandation dans la session courante |
| **Autorisé ($X$ Whitelist)** | `session_elapsed_seconds` | Temps écoulé depuis le début de la session |
| **Autorisé ($X$ Whitelist)** | `user_interacted_with_establishment` | Historique d'interaction utilisateur - établissement |
| **Autorisé ($X$ Whitelist)** | `user_interacted_with_category` | Historique d'interaction utilisateur - catégorie |

---

## 4. DÉCOUPAGE TRAIN / VALIDATION PAR GROUPE DE SESSION

Pour refléter fidèlement le comportement d'un système de Ranking en production et éviter tout sur-apprentissage (*overfitting* inter-sessions) :
- Le découpage est effectué via `GroupShuffleSplit` basé sur la colonne `query_session_id`.
- 100% des interactions appartenant à une même session utilisateur tombent soit dans l'ensemble d'entraînement, soit dans l'ensemble de validation/test.
- Aucune session n'est partagée entre le Train Set et le Test Set.

---

## 5. CONFIGURATION LIGHTGBM LAMBDAMART

Le modèle est configuré via `lightgbm.LGBMRanker` avec la fonction d'optimisation spécifique aux requêtes ordonnées :
- **Objective** : `lambdarank`
- **Metric** : `ndcg`
- **NDCG Eval Cutoffs** : `eval_at=[5, 10]`
- **Boosting Type** : `gbdt`
- **N Estimators** : `100` (avec *early stopping* après 10 itérations sans amélioration sur le jeu de validation)
- **Learning Rate** : `0.05`
- **Num Leaves** : `31`

---

## 6. ÉVALUATION HORS-LIGNE & MÉTRIQUES

Le pipeline d'évaluation compare la performance de LightGBM à une baseline de popularité (*Popularity Baseline*) sur trois métriques clés :
1. **NDCG@5** (*Normalized Discounted Cumulative Gain at 5*) : Mesure la qualité globale de l'ordonnancement des 5 premières recommandations.
2. **NDCG@10** (*Normalized Discounted Cumulative Gain at 10*) : Mesure la qualité de l'ordonnancement des 10 premières recommandations.
3. **MRR** (*Mean Reciprocal Rank*) : Position moyenne de la première vidéo fortement pertinente dans les résultats.

---

## 7. TRANSPARENCE DES DONNÉES RÉELLES

En analysant la base de données de production/développement AYYOU :
- **Utilisateurs enregistrés** : 84
- **Vidéos / Publications** : 8
- **Événements Telemetry enregistrés dans `VideoEventLog`** : 0

Conséquence directe :
Lors de l'exécution de `python manage.py train_recommender`, le script détecte l'absence de logs et affiche en toute transparence :
> `[INFO] Dataset vide (0 évènements). Minimum 10 sessions requises pour l'entraînement.`

Conformément aux exigences de rigueur technique :
- Aucun faux modèle n'a été pré-entraîné artificiellement sur des données synthétiques trompeuses.
- Dès que le système de télémétrie déployé en Phase 1 & 2.5 collectera suffisamment d'interactions d'utilisateurs réels, la commande entrainera automatiquement le premier modèle opérationnel.

---

## 8. SUITE DE TESTS AUTOMATISÉS

Une suite de tests unitaire et d'intégration complète est disponible dans `apps/telemetry/tests/test_ml_pipeline.py`.

Pour exécuter les tests :
```bash
python manage.py test apps.telemetry
```

**Résultat des 21 tests (Telemetry + ML Pipeline) :**
```text
Ran 21 tests in 15.999s
OK
```
