# 🛡️ AUDIT DE FUITE DE DONNÉES (DATA LEAKAGE AUDIT) — RECOMMANDATION IA AYYOU

**Date :** Octobre 2026  
**Module :** `apps/telemetry/ml/`  
**Objectif :** Identifier, classifier et éliminer toutes les variables risquant de provoquer une fuite de données (*Data Leakage*) lors de l'apprentissage du modèle **LightGBM LambdaMART Ranker**.

---

## 1. 🔍 DÉFINITION ET RISQUES DE FUITE EN RECOMMANDATION

La fuite de données (*Data Leakage*) se produit lorsque des informations futures, postérieures à l'interaction ou dérivées directement du label cible ($Target$), sont transmises au modèle sous forme de caractéristiques ($X$). Le modèle apprend alors à "tricher" en lisant la réponse dans la feature au lieu d'apprendre la pertinence réelle.

---

## 2. 📋 TABLEAU D'AUDIT SYSTÉMATIQUE DES FEATURES

| Feature Candidat | Risque de Fuite Identifié | Statut & Décision | Justification Technique |
| :--- | :--- | :---: | :--- |
| **`target_relevance`** | Variable cible directe | 🔴 **EXCLU DE X** | C'est le Label $Y \in [0, 4]$ à prédire. Ne doit JAMAIS être dans $X$. |
| **`event_type`** | Événement courant de la ligne | 🔴 **EXCLU DE X** | La nature de l'événement (`LIKE`, `SKIP`, `COMPLETED`) est utilisée pour construire $Y$. |
| **`watch_time_seconds`** | Temps de visionnage de la session | 🔴 **EXCLU DE X** | Le temps de visionnage découle de l'interaction en cours ; sa présence permet de prédire $Y=2$ à 100%. |
| **`completion_rate`** | Taux de complétion courant | 🔴 **EXCLU DE X** | Directement corrélé à `target_relevance`. |
| **`is_skip` / `is_completed`** | Drapeaux d'événements | 🔴 **EXCLU DE X** | Fuite directe de la variable cible. |
| **`video_total_likes`** | Compteur global de likes | 🟢 **CONSERVÉ (Historisé)** | Représente la popularité passée globale de la vidéo avant l'interaction. |
| **`video_total_shares`** | Compteur global de partages | 🟢 **CONSERVÉ (Historisé)** | Popularité passée de la vidéo. |
| **`user_account_age_days`** | Ancienneté du compte | 🟢 **CONSERVÉ** | Caractéristique statique de l'utilisateur. |
| **`user_total_orders`** | Nombre de commandes passées | 🟢 **CONSERVÉ** | Historique d'achat passé du client. |
| **`user_avg_order_amount`** | Panier moyen | 🟢 **CONSERVÉ** | Historique financier passé. |
| **`user_top_category_id`** | Catégorie la plus achetée | 🟢 **CONSERVÉ** | Affinité culinaire passée. |
| **`dish_price`** | Prix du plat | 🟢 **CONSERVÉ** | Caractéristique statique du catalogue. |
| **`dish_category_id`** | Catégorie du plat | 🟢 **CONSERVÉ** | Caractéristique statique du catalogue. |
| **`resto_rating`** | Note moyenne du restaurant | 🟢 **CONSERVÉ** | Caractéristique statique du marchand. |
| **`resto_reviews_count`** | Nombre d'avis du restaurant | 🟢 **CONSERVÉ** | Caractéristique statique du marchand. |
| **`video_recency_hours`** | Fraîcheur de la vidéo | 🟢 **CONSERVÉ** | Horodatage de la vidéo. |
| **`feed_position`** | Position dans le scroll | 🟢 **CONSERVÉ** | Contexte de présentation de la vidéo. |
| **`hour_of_day` / `day_of_week`** | Contexte temporel | 🟢 **CONSERVÉ** | Contexte de la requête. |

---

## 3. 🛡️ GARANTIES DU MODULE `apps/telemetry/ml/dataset.py`

Le module de préparation du dataset applique une sélection stricte des colonnes transmises à LightGBM :

```python
# Liste explicite et verrouillée des features d'entrée X
FEATURE_COLUMNS = [
    'is_authenticated',
    'user_account_age_days',
    'user_total_orders',
    'user_avg_order_amount',
    'user_total_likes',
    'user_total_events',
    'user_avg_watch_time',
    'user_avg_completion_rate',
    'user_top_category_id',
    'video_recency_hours',
    'video_duration_seconds',
    'video_total_likes',
    'video_total_shares',
    'dish_price',
    'dish_category_id',
    'resto_rating',
    'resto_reviews_count',
    'feed_position',
    'hour_of_day',
    'day_of_week'
]
```

Toutes les colonnes de résultat (`target_relevance`, `event_type`, `watch_time_seconds`, `completion_rate`, `is_skip`, `is_completed`) sont **exclues à 100% de la matrice $X$**.
