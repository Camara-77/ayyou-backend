# AYYOU — Phase 10 : Rapport d'Expérimentation Contrôlée du Recommender V3

**Projet** : AYYOU  
**Phase** : 10 — Expérimentation Contrôlée (A/B Testing V3 vs Chronologique)  
**Statut du Modèle V3** : EXPERIMENTAL / A/B TESTING READY  
**Comportement par Défaut** : 100 % Chronologique (`RECOMMENDATION_MODE = 'chronological'`)  
**Décision Finale** : **READY FOR CONTROLLED EXPERIMENT**

---

## 1. Objectif

La Phase 10 déploie l'infrastructure d'**Expérimentation Contrôlée (A/B Testing)** pour comparer de manière rigoureuse, isolée et mesurable en conditions réelles :
- **Groupe CONTROL (85 %)** : Feed vidéo chronologique par défaut (`-date_publication`).
- **Groupe EXPERIMENT (15 %)** : Feed vidéo personnalisé scoré et réordonné par LightGBM V3.

L'objectif est d'observer les divergences d'engagement (watch time, completion rate, skip rate, interactions) sans jamais altérer le fonctionnement principal du Feed ni imposer de régression UX.

---

## 2. Architecture de l'Expérimentation

```text
Utilisateur / Frontend Angular (GET /api/catalog/feed/)
                        │
                        ▼
            PublicationFeedListView (Django)
                        │
        ┌───────────────┴───────────────┐
        ▼                               ▼
RecommendationExperimentService   RecommendationShadowService
        │ (A/B Routing)                 │ (Monitoring Ombre)
        ├───────────────────────┐       └──────────────┬───────────┘
        ▼                       ▼                      ▼
 Groupe CONTROL         Groupe EXPERIMENT      RecommendationShadowLog
  (Chronologique)         (LightGBM V3)
        │                       │
        │             (En cas d'erreur V3)
        │                       │
        │             Fallback Chronologique
        │                       │
        └───────────┬───────────┘
                    ▼
       RecommendationExperimentLog
                    │
                    ▼
     Réponse HTTP 200 OK (Compatibilité 100% Angular)
```

---

## 3. Configuration & Feature Flags

La configuration est gérée au niveau serveur dans `config/settings/base.py` via variables d'environnement :

| Feature Flag | Valeur par Défaut | Description |
| :--- | :--- | :--- |
| `RECOMMENDATION_MODE` | `'chronological'` | Mode actif du Feed (`'chronological'`, `'experiment'`, `'shadow'`) |
| `RECOMMENDATION_EXPERIMENT_ENABLED` | `False` | Activation globale de l'A/B testing (`True` / `False`) |
| `RECOMMENDATION_EXPERIMENT_PERCENTAGE` | `15` | Pourcentage de trafic orienté vers le groupe EXPERIMENT (0-100 %) |

> [!IMPORTANT]
> Si `RECOMMENDATION_MODE != 'experiment'` ou `RECOMMENDATION_EXPERIMENT_ENABLED = False`, **100 % des utilisateurs reçoivent le Feed chronologique**.

---

## 4. Méthode de Répartition Déterministe

Pour garantir la continuité de l'expérience utilisateur sans effet de saut d'un rechargement à l'autre :
- **Utilisateur Authentifié** : Identifiant stable `user_{user.id}`.
- **Utilisateur Anonyme** : Identifiant stable `session_{session_id}`.
- **Formule de Hachage** :
  $$\text{hash\_val} = \text{int}\left(\text{hashlib.md5}(\text{identifier.encode()}).\text{hexdigest}(), 16\right) \pmod{100}$$
- **Affectation** :
  - `hash_val < RECOMMENDATION_EXPERIMENT_PERCENTAGE` $\rightarrow$ **Groupe EXPERIMENT (V3)**
  - `hash_val >= RECOMMENDATION_EXPERIMENT_PERCENTAGE` $\rightarrow$ **Groupe CONTROL (Chronologique)**

---

## 5. Mécanisme de Fallback Chronologique Automatique

En vertu du principe de sécurité absolue du Feed, si le scoring V3 rencontre une anomalie (modèle indisponible, exception Python, score NaN/Inf, incohérence de candidats) :
1. L'erreur est capturée et journalisée (`logger.warning`).
2. Le système bascule automatiquement vers le classement chronologique d'origine.
3. L'événement est enregistré avec `fallback_used = True` dans `RecommendationExperimentLog`.
4. La requête HTTP client réussit sans latence ni crash.

---

## 6. Tableaux de Bord de Monitoring (`recommendation_experiment_stats`)

La commande Django `python manage.py recommendation_experiment_stats` permet de visualiser en direct l'état de l'expérimentation et d'en comparer les métriques :

```text
==================================================
RECOMMENDATION EXPERIMENT DASHBOARD
==================================================

STATUS
-------
enabled: false (ou true lors de l'activation)
percentage: 15%
mode: chronological (ou experiment)

GROUPS
------
CONTROL:
  sessions: X
  users: X
  impressions: X

EXPERIMENT V3:
  sessions: X
  users: X
  impressions: X

ENGAGEMENT
----------
CONTROL:
  avg_watch_time: X.XXs
  completion_rate: X.XX%
  skip_rate: X.XX%
  dish_click_rate: X.XX%
  cart_add_rate: X.XX%

EXPERIMENT V3:
  avg_watch_time: X.XXs
  completion_rate: X.XX%
  skip_rate: X.XX%
  dish_click_rate: X.XX%
  cart_add_rate: X.XX%

PERFORMANCE
-----------
  V3 avg scoring: X.XX ms
  V3 P95: X.XX ms
  fallback rate: X.XX%
```

---

## 7. Résultats des Tests et Validation Manuelle

### A. Couverture des Tests Django (100 % RÉUSSI)
- **`apps.telemetry`** : **92 tests sur 92 réussis** (`Ran 92 tests OK`).
- **`apps.catalog`** : **67 tests sur 67 réussis** (`Ran 67 tests OK`).

### B. Validation des 7 Scénarios Manuels (Cas A à G)
- **CAS A** (`RECOMMENDATION_MODE='chronological'`) : **RÉUSSI** (Feed 100% chronologique).
- **CAS B** (`RECOMMENDATION_EXPERIMENT_ENABLED=False`) : **RÉUSSI** (Feed 100% chronologique).
- **CAS C** (`experiment` + CONTROL 0%) : **RÉUSSI** (Feed 100% chronologique).
- **CAS D** (`experiment` + EXPERIMENT 100%) : **RÉUSSI** (Feed re-classé par V3 : `[45, 38, 41, 43, 42, 44, 40, 39]`).
- **CAS E** (V3 Exception) : **RÉUSSI** (Fallback chronologique automatique).
- **CAS F** (Stabilité utilisateur 2x reload) : **RÉUSSI** (Groupe identique conservé).
- **CAS G** (Stabilité session anonyme 2x reload) : **RÉUSSI** (Groupe identique conservé).

---

## 8. Fichiers Modifiés & Créés

1. `config/settings/base.py` : Déclaration des feature flags `RECOMMENDATION_EXPERIMENT_ENABLED` et `PERCENTAGE`.
2. `apps/telemetry/models.py` : Ajout du modèle ORM `RecommendationExperimentLog`.
3. `apps/telemetry/migrations/0003_recommendationexperimentlog.py` : Migration Django appliquée avec succès.
4. `apps/telemetry/ml/experiment_service.py` : Service de routage A/B testing déterministe et fallback.
5. `apps/catalog/views.py` : Raccordement du service dans `PublicationFeedListView.get()`.
6. `apps/telemetry/management/commands/recommendation_experiment_stats.py` : Commande de monitoring A/B testing.
7. `apps/telemetry/tests/test_experiment_mode.py` : Suite de 24 tests dédiés à la Phase 10.
8. `docs/recommendation_phase_10_controlled_experiment.md` : Rapport officiel d'expérimentation contrôlée.

---

## 9. Décision Finale

```text
==================================================
DÉCISION AUDIT PHASE 10 :
READY FOR CONTROLLED EXPERIMENT
==================================================
```

L'ensemble de l'infrastructure d'Expérimentation Contrôlée (A/B Testing) pour le Recommender LightGBM V3 est opérationnelle, déterministe, sécurisée et couverte à 100 % par les tests automatisés et manuels. Le basculement vers l'expérimentation est prêt à être activé sur le serveur via les variables d'environnement.
