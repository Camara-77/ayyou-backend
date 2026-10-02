# Documentation Technique — Correction de la Fuite Temporelle (Phase 6.6)

**Projet :** AYYOU  
**Date :** 1er Octobre 2026  
**Composants affectés :** `apps/telemetry/data_preparation.py` (`FeatureExtractor`, `DatasetBuilder`)  

---

## 1. Problème Initial

Lors de l'audit de la Phase 6.5, une **fuite temporelle prospective (Temporal Look-Ahead Leakage)** a été identifiée. 
Dans l'ancienne mise en œuvre, la construction des caractéristiques de l'utilisateur (`FeatureExtractor.extract_user_features`) agrégeait l'ensemble des événements de l'utilisateur enregistrés dans la base de données, **sans restriction sur la date d'exposition de l'événement cible**.

---

## 2. Exemple Concret du Dysfonctionnement

Soit une session utilisateur composée de 3 événements successifs :
- **Événement A** (10:00) : Première vue d'une vidéo
- **Événement B** (10:05) : Deuxième vue d'une vidéo
- **Événement C** (10:10) : Ajout au panier (conversion)

### Comportement AVANT Correction :
Lorsque le pipeline générait la ligne du dataset d'apprentissage pour l'**Événement A (10:00)**, la requête exécutait `VideoEventLog.objects.filter(utilisateur=user)`. Elle comptabilisait donc les événements B (10:05) et C (10:10). 
Les caractéristiques de A indiquaient `user_total_events = 3`, incluant des interactions qui n'avaient **pas encore eu lieu au moment A**.

---

## 3. Cause Technique

La méthode `extract_user_features(user_id, session_id)` n'acceptait aucun paramètre temporel de référence (`at_datetime`). Elle exécutait directement les requêtes Django ORM sans clause de filtrage temporel `date_creation__lt` ou `created_at__lt`.

---

## 4. Schéma Comparatif AVANT / APRÈS

```
AVANT (Fuite Temporelle Prospective) :

Event A (10:00) ────────┐
Event B (10:05) ────────┼──> Features de A : user_total_events = 3 ❌ (Inclut le futur B & C)
Event C (10:10) ────────┘


APRÈS (Isolation Temporelle Stricte created_at < T) :

Event A (10:00) ────────> Features de A : user_total_events = 0 (Aucun passé)

Event B (10:05)
  ↑
  └── Event A uniquement ──> Features de B : user_total_events = 1 (A visible, C invisible)

Event C (10:10)
  ↑
  └── Event A + Event B ───> Features de C : user_total_events = 2 (A et B visibles)
```

---

## 5. Correction Effectuée dans le Code

1. **Prise en compte de `at_datetime` dans `FeatureExtractor` :**
   Les méthodes `extract_user_features` et `extract_video_features` acceptent un argument facultatif `at_datetime: Optional[datetime] = None` (qui prend la valeur `timezone.now()` par défaut lors du scoring temps réel).
2. **Filtrage Strict `created_at__lt` (Strictement inférieur) :**
   Toutes les agrégations ORM filtrent désormais avec la clause `created_at__lt=ref_time` (ou `date_creation__lt=ref_time` pour les commandes et likes).
3. **Propagation depuis `DatasetBuilder` :**
   Lors de l'itération sur le jeu de données historique dans `DatasetBuilder.build_dataset_row(event)`, l'horodatage `event_dt = event.created_at` est extrait et transmis à `extract_user_features` et `extract_video_features`.

---

## 6. Traitement des Utilisateurs Authentifiés

Pour un utilisateur connecté `user_id` à la date $T = \text{event.created\_at}$ :
- `user_account_age_days` = $\max(0, T - \text{user.date\_creation})$
- `user_total_orders` = Nombre de commandes payées/livrées à `date_creation < T`
- `user_total_likes` = Nombre de likes enregistrés à `date_creation < T`
- `user_total_events` = Nombre d'événements `VideoEventLog` enregistrés à `created_at < T`
- `user_avg_watch_time` = Temps moyen de visionnage sur les événements à `created_at < T`

---

## 7. Traitement des Utilisateurs Anonymes

Pour une session anonyme (`utilisateur=None`, `session_id`) à la date $T = \text{event.created\_at}$ :
- `user_total_events` = Nombre d'événements `VideoEventLog` partageant le même `session_id` enregistrés à `created_at < T`
- `user_avg_watch_time` = Temps moyen de visionnage dans la session à `created_at < T`

---

## 8. Tests d'Intégrité Anti-Leakage Ajoutés

Fichier : `apps/telemetry/tests/test_temporal_leakage.py`
- `test_01_authenticated_user_temporal_isolation` : Valide la progression $0 \to 1 \to 2$ d'événements visibles pour 3 interactions successives d'un utilisateur connecté.
- `test_02_future_event_addition_does_not_alter_past_features` : Valide qu'insérer un événement futur à $T+15\text{min}$ ne modifie en rien la ligne générée pour $T+5\text{min}$.
- `test_03_anonymous_user_session_temporal_isolation` : Valide la progression stricte de session anonyme.
- `test_04_strict_created_at_less_than_comparison` : Valide la comparaison stricte ($created\_at < T$), garantissant qu'un événement n'est pas inclus dans son propre historique.

---

## 9. Impact et Périmètre

- **Impact sur le dataset d'apprentissage :** Les caractéristiques d'activité des premières sessions utilisateurs reflètent désormais fidèlement la réalité froide au moment du visionnage.
- **Impact sur le Feed Live et le Frontend Angular :** **Strictement AUCUN**. Le Feed live reste 100% chronologique et le Frontend Angular n'a pas été touché.
- **Impact sur le Modèle V2 :** Le modèle V2 (`recommender_lgbm_v2.joblib`) conservé dans `models/recommender/` repose sur l'ancienne méthode. Il reste disponible pour la simulation Phase 6 mais ne doit pas être ré-entraîné immédiatement.

---

## 10. Limites

Cette correction élimine les fuites temporelles sur la base de données locale. Si de nouveaux types de features relatives aux comportements agrégés (ex: graphes d'affinité utilisateurs) sont introduits dans le futur, le paramètre `at_datetime` devra être systématiquement propagé dans les requêtes d'extraction associées.
