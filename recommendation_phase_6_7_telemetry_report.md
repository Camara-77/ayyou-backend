# Phase 6.7 — Rapport de Surveillance et Accumulation de la Télémétrie

**Projet :** AYYOU  
**Date du rapport :** 1er Octobre 2026  
**Type de document :** Rapport de Surveillance & Qualité Télémétrie (Phase 6.7)  
**Statut :** Collecte Active de Données Réelles en Production — Feed 100% Inchangé  

---

## 1. Date du Rapport

- **Date d'exécution du rapport :** 1er Octobre 2026 à 22:44 UTC
- **Source des données :** Base de données SQLite réelle (`apps.telemetry.models.VideoEventLog`)

---

## 2. Volume Total

- **Événements de télémétrie bruts enregistrés :** `104`
- **Taux de croissance des données :** Accumulation en cours
- **Données artificielles / synthétiques en base de production :** `0` (Strictement 100% réel)

---

## 3. Sessions

- **Sessions totales enregistrées :** `12`
- **Sessions avec utilisateur connecté (authentifié) :** `6` (50.0%)
- **Sessions visiteurs anonymes :** `6` (50.0%)
- **Moyenne d'événements par session :** `8.67` événements/session
- **Médiane d'événements par session :** `8.50` événements/session
- **Minimum / Maximum d'événements par session :** `4` min / `14` max
- **Sessions à 1 seul événement (Rebond) :** `0` (0.0%)
- **Sessions multi-interactions (≥ 2 événements) :** `12` (100.0%)

---

## 4. Utilisateurs

- **Utilisateurs authentifiés distincts enregistrés :** `5`
- **Moyenne d'événements par utilisateur authentifié :** `20.80` événements/utilisateur
- **Traçabilité des profils :** Intégrité des identifiants `utilisateur_id` et `session_id` validée

---

## 5. Événements par Type

| Type d'Événement (`event_type`) | Volume | Pourcentage du Total |
|---|:---:|:---:|
| **IMPRESSION** (Affichage à l'écran) | 24 | 23.1% |
| **PLAY** (Début de lecture) | 24 | 23.1% |
| **WATCH** (Heartbeat de visionnage) | 23 | 22.1% |
| **COMPLETED** (Complétion 100%) | 7 | 6.7% |
| **SKIP** (Zappe rapide < 3s) | 7 | 6.7% |
| **CART_ADD** (Ajout au panier) | 5 | 4.8% |
| **LIKE** (Like activé) | 5 | 4.8% |
| **DISH_CLICK** (Clic fiche plat) | 4 | 3.8% |
| **SHARE** (Partage vidéo) | 3 | 2.9% |
| **PAUSE** (Mise en pause) | 2 | 1.9% |
| **UNLIKE** (Like retiré) | 0 | 0.0% |
| **Total** | **104** | **100.0%** |

---

## 6. Watch Time

- **Watch time moyen global :** `11.65s`
- **Watch time médian global :** `12.00s`
- **Watch time minimum / maximum :** `1.0s` min / `25.0s` max
- **Incohérences de temps (< 0s) :** `0`

---

## 7. Completion Rate

- **Completion rate moyen global :** `0.3260` (`32.6%`)
- **Completion rate médian global :** `0.0667` (`6.7%`)
- **Valeurs aberrantes (hors intervalle [0.0, 1.0]) :** `0`

---

## 8. Interactions par Publication & Biais de Popularité

- **Publications vidéo actives suivies :** 8 publications (IDs `#38` à `#45`)
- **Distribution des interactions :**
  - **Part de la publication Top 1 :** `18.3%` (19 événements concentrés sur la vidéo `#45`)
  - **Part du Top 3 publications :** `45.2%` (47 événements)
  - **Part du Top 5 publications :** `71.2%` (74 événements)
- **Publications sans aucune interaction :** `0`
- **Publications récemment créées (7 derniers jours) :** `8`

---

## 9. Qualité des Données

- **Événements valides (selon `TelemetryDataCleaner`) :** 104 / 104 (100.0%)
- **Événements invalides :** `0`
- **Événements sans `session_id` :** `0`
- **Événements sans publication :** `0`
- **Horodatages `created_at` invalides :** `0`

---

## 10. Anomalies

- **Doublons stricts identifiés :** `0`
- **Doublons potentiels à la même seconde :** `0`
- **Séquences impossibles (ex: COMPLETED sans PLAY) :** `0`

---

## 11. Répartition de l'Activité

L'activité est idéalement distribuée entre sessions authentifiées (50%) et anonymes (50%). Les sessions contiennent un nombre significatif d'interactions moyennes (`8.67` events/session), garantissant une richesse comportementale exploitable par les futurs modèles séquentiels et contextuels.

---

## 12. Progression vers 1 000 Événements

- **Seuil indicatif :** `1 000` événements
- **Événements actuels :** `104`
- **Progression :** **`10.4%`** (`104 / 1 000`)

---

## 13. Progression vers 100 Sessions

- **Seuil indicatif :** `100` sessions
- **Sessions actuelles :** `12`
- **Progression :** **`12.0%`** (`12 / 100`)

---

## 14. État de la Fuite Temporelle

- **Statut :** **Totalement Protégé (0 Fuite Temporelle)**
- **Mécanisme :** Le pipeline `DatasetBuilder.build_training_dataset()` utilise la clause stricte `created_at__lt=at_datetime`.
- **Validation :** Validé par 4 tests automatisés d'isolation temporelle dans `apps/telemetry/tests/test_temporal_leakage.py`.

---

## 15. État de Préparation du Futur Modèle V3

> [!WARNING]
> **SIGNAL SEUIL NON ENCORE ATTEINT**  
> Avec `10.4%` de progression sur les événements et `12.0%` sur les sessions, les conditions de volume pour réentraîner un modèle V3 ne sont pas encore réunies.  
> **Recommandation :** Poursuivre l'accumulation naturelle de la télémétrie en production tout en conservant le modèle V2 sur la simulation hors-feed.
