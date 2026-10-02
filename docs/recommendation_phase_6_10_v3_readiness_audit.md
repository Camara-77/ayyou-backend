# AYYOU — PHASE 6.10 : AUDIT DE PRÉPARATION PRÉ-ENTRAÎNEMENT DU MODÈLE V3 (READINESS AUDIT)

**Projet** : AYYOU  
**Phase** : 6.10 — V3 Readiness Audit  
**Statut Final** : CONTINUE DATA COLLECTION (Poursuivre la collecte de données)  
**Date** : 1er Octobre 2026  

---

## 1. OBJECTIF DE L'AUDIT

Cet audit a pour objectif unique et exclusif d'évaluer objectivement si l'état **ACTUEL** de la base de données de télémétrie réelle d'AYYOU présente le volume, la diversité et l'isolation temporelle nécessaires pour justifier le lancement du premier entraînement réel d'un modèle LightGBM LambdaMART V3.

> **RÈGLES STRICTES DE PROTECTION EN VIGUEUR** :
> - **Modèle V3** : N'a **PAS** été entraîné.
> - **Modèle V2** : Le modèle V2 (`recommender_lgbm_v2.joblib`) et ses métadonnées sont conservés intacts.
> - **Feed de Production** : `GET /api/catalog/feed/` demeure 100 % chronologique (`-date_publication`).
> - **Frontend Angular** : Aucun composant ni service (`HomeComponent`, `FoodPostComponent`, `VideoTelemetryService`, etc.) n'a été modified.
> - **Données Synthétiques** : Aucune donnée artificielle ou générée n'a été injectée.

---

## 2. ÉTAT ACTUEL DES DONNÉES RÉELLES EN BASE DE DONNÉES

| Métrique | Valeur Actuelle | Seuil Indicatif V3 | Progression (%) |
|---|---|---|---|
| **Événements Totaux (`VideoEventLog`)** | **104** | 1,000 | **10.4 %** |
| **Sessions Totales (`session_id`)** | **12** | 100 | **12.0 %** |
| **Sessions Authentifiées** | 6 | - | - |
| **Sessions Anonymes** | 6 | - | - |
| **Utilisateurs Authentifiés Distincts** | **5** | 20 | **25.0 %** |
| **Publications Observées** | **8** | 15 | **53.3 %** (8 sur 8 du catalogue) |
| **Événements Valides / Exploitables** | **104 / 104 (100 %)** | 100 % | **100.0 %** |
| **Fuites Temporelles Détectées** | **0** | 0 | **100.0 %** |

---

## 3. ANALYSE DÉTAILLÉE DU VOLUME

Le volume global accumulé en base de données s'élève à **104 événements** répartis sur **12 sessions**.
- **Progression Événements** : 10.4 % de l'objectif minimal indicatif de 1 000 événements.
- **Progression Sessions** : 12.0 % de l'objectif minimal indicatif de 100 sessions.

---

## 4. DIVERSITÉ UTILISATEURS & SESSIONS

### Répartition par Utilisateur Authentifié (5 utilisateurs au total) :
- Utilisateurs avec $\ge$ 1 événement : **5**
- Utilisateurs avec $\ge$ 5 événements : **5**
- Utilisateurs avec $\ge$ 10 événements : **3**
- Utilisateurs avec $\ge$ 20 événements : **0**
- **Concentration Top 1 Utilisateur** : 14 événements sur 55 événements authentifiés (**25.5 %**). Aucun utilisateur ne monopolise abusivement les interactions.

### Répartition par Session (12 sessions au total) :
- Sessions avec $\ge$ 3 événements : **12**
- Sessions avec $\ge$ 5 événements : **11**
- Sessions avec $\ge$ 10 événements : **5**
- Sessions avec $\ge$ 20 événements : **0**
- **Concentration Top 1 Session** : 14 événements sur 104 événements totaux (**13.5 %**).

---

## 5. DIVERSITÉ DES PUBLICATIONS

- **Publications actives au catalogue** : 8
- **Publications observées dans la télémétrie** : 8 (100 % d'inclusivité des publications)
- **Interactions par publication** : Minimum = 8, Maximum = 19, Moyenne = 13.00, Médiane = 13.5
- **Part Top 1 Publication** : 19 événements (**18.3 %**)
- **Part Top 3 Publications** : 47 événements (**45.2 %**)
- **Part Top 5 Publications** : 74 événements (**71.2 %**)

La distribution des interactions entre les publications est exceptionnellement bien équilibrée, sans sur-représentation d'une vidéo spécifique.

---

## 6. DIVERSITÉ DES ÉVÉNEMENTS (TYPES D'INTERACTION)

| Type d'Événement | Nombre | Pourcentage (%) | Catégorie |
|---|---|---|---|
| `IMPRESSION` | 24 | 23.1 % | Exposition Basique |
| `PLAY` | 24 | 23.1 % | Exposition Basique |
| `PAUSE` | 2 | 1.9 % | Exposition Basique |
| `WATCH` | 23 | 22.1 % | Exposition Basique |
| `COMPLETED` | 7 | 6.7 % | Interaction à Forte Valeur |
| `SKIP` | 7 | 6.7 % | Signal Négatif (Target 0) |
| `LIKE` | 5 | 4.8 % | Engagement Social |
| `UNLIKE` | 0 | 0.0 % | - |
| `SHARE` | 3 | 2.9 % | Engagement Social |
| `CART_ADD` | 5 | 4.8 % | Conversion Commerciale |
| `DISH_CLICK` | 4 | 3.8 % | Conversion Commerciale |

- **Exposition Basique** (`IMPRESSION`, `PLAY`, `PAUSE`, `WATCH`) : 73 événements (**70.2 %**)
- **Interactions à Forte Valeur / Conversion** (`LIKE`, `SHARE`, `CART_ADD`, `DISH_CLICK`, `COMPLETED`, `SKIP`) : 31 événements (**29.8 %**)

---

## 7. DISTRIBUTION DU TARGET DE RELEVANCE

La variable cible (Target Relevance Score entre 0 et 4) générée par le pipeline `DatasetBuilder` donne la répartition suivante sur les 104 lignes :

| Target Level | Règle / Signification | Nombre | Pourcentage (%) |
|---|---|---|---|
| **Target 0** | Skip / Inactivité (< 3s) | 13 | **12.5 %** |
| **Target 1** | Vue partielle (< 50%) | 60 | **57.7 %** |
| **Target 2** | Vue complète ($\ge$ 90%) | 14 | **13.5 %** |
| **Target 3** | Engagement Social (Like / Partage) | 8 | **7.7 %** |
| **Target 4** | Conversion Commerciale (Clic Plat / Panier) | 9 | **8.7 %** |

**Analyse** : Toutes les classes de pertinences (0 à 4) sont représentées dans le jeu de données actuel. Le Target 1 est majoritaire, reflétant un comportement naturel de survol vidéo.

---

## 8. VÉRIFICATION DE LA FUITE TEMPORELLE (ANTI-TEMPORAL LEAKAGE)

- **Isolation Historique** : La règle stricte $created\_at < T$ est implémentée au niveau de `FeatureExtractor` et `DatasetBuilder`.
- **Exclusion des Variables Post-Exposition** : Les caractéristiques de $X$ dans `FEATURE_COLUMNS` excluent scrupuleusement `event_type`, `watch_time_seconds`, `completion_rate`, `is_skip`, et `is_completed`.
- **Verdict Anti-Leakage** : **0 fuite temporelle détectée.** Les tests d'isolation temporelle passent à 100 %.

---

## 9. VÉRIFICATION DU SPLIT TRAIN / VALIDATION

- **Mécanisme de Découpage** : `GroupShuffleSplit` basé strictement sur `query_session_id`.
- **Groupes d'Entraînement (Train)** : 9 sessions (**73 lignes**)
- **Groupes de Validation (Val)** : 3 sessions (**31 lignes**)
- **Overlap de Session** : **0 session commune** (Aucune fuite inter-session entre Train et Val).
- **Limitation Identifiée** : Un ensemble de validation de 3 sessions est techniquement trop restreint pour calculer des métriques NDCG@5 et NDCG@10 statistiquement stables et représentatives.

---

## 10. EVALUATION DE LA PERSONNALISATION ET COMPARAISON AVEC V2

- Le modèle V2 avait été entraîné sur un échantillon très restreint (104 événements, 12 sessions).
- Les données actuelles montrent un signal comportemental propre mais sur un périmètre d'utilisateurs encore trop réduit (5 utilisateurs authentifiés) pour généraliser un apprentissage de préférences individuelles sans risque de sur-ajustement (overfitting).

---

## 11. GRILLE DE READINESS V3

| Critère | Évaluation / Note | Justification Rationale |
|---|---|---|
| **Volume Global** | **C (Insuffisant)** | 104 événements réels sur 1 000 visés (10.4 %). |
| **Diversité Utilisateurs** | **B (Acceptable)** | 5 utilisateurs auth, pas de sur-concentration (Top 1 = 25.5 %). |
| **Diversité Sessions** | **C (Insuffisant)** | 12 sessions totales sur 100 visées (12.0 %). |
| **Diversité Publications**| **B (Acceptable)** | 8/8 publications observées avec une distribution très homogène. |
| **Diversité Événements**  | **A (Satisfaisant)** | Bon équilibre entre exposition (70.2%) et conversion/engagement (29.8%). |
| **Qualité Données**      | **A (Satisfaisant)** | 100 % d'événements valides, 0 anomalie. |
| **Qualité Temporelle**    | **A (Satisfaisant)** | Horodatage $created\_at$ strictement préservé. |
| **Absence de Leakage**    | **A (Satisfaisant)** | Comparaison stricte $created\_at < T$, 0 fuite temporelle. |
| **Distribution Target**   | **B (Acceptable)** | Présence des 5 classes (Target 0 à 4). |
| **Train / Validation**    | **C (Insuffisant)** | Séparation propre mais seulement 3 sessions en validation. |
| **Personnalisation**     | **B (Acceptable)** | Signaux présents, mais échantillon trop faible pour généraliser. |

---

## 12. DÉCISION FINALE DE LA PHASE 6.10

> **DÉCISION SÉLECTIONNÉE** : **`CONTINUE DATA COLLECTION`** (Poursuivre la collecte de données)

### Justification Détaillée :
Bien que le pipeline de télémétrie d'AYYOU soit techniquement **irréprochable** (0 fuite temporelle, 100 % d'événements valides, séparation Train/Val par groupe sans fuite), le volume de données réelles actuelles (104 événements, 12 sessions) est insuffisant pour garantir un entraînement V3 robuste et une évaluation NDCG fiable sur la validation. L'entraînement de V3 prématurément risquerait de créer un modèle sur-ajusté aux 12 sessions actuelles.

---

## 13. RISQUES ET PROCHAINES ÉTAPES

1. **Risques de l'entraînement prématuré** : Risque fort d'overfitting et de métriques NDCG trompeuses sur 3 sessions de validation.
2. **Action requise** : Poursuivre l'accumulation de la télémétrie utilisateur réelle sur le Feed chronologique.
3. **Seuil de réévaluation** : Relancer l'audit lorsque la base aura franchi le cap des **1 000 événements** et **100 sessions** (indicateur `READY_FOR_AUDIT` via `python manage.py telemetry_quality_stats`).
