# PHASE 3.5 — DONNÉES RÉELLES AYYOU

## 1. État de la collecte

- **Nombre d'événements enregistrés** : 32
- **Nombre de sessions distinctes** : 5
- **Nombre d'utilisateurs authentifiés distincts** : 1 (Utilisateur #185 Modou Diop)
- **Nombre de vidéos / publications concernées** : 8 (ID #38 à #45)

---

## 2. Répartition des événements

| Événement (Event) | Nombre | Description / Signification |
| :--- | :---: | :--- |
| `IMPRESSION` | 8 | Cartes vidéo affichées dans le viewport du Feed |
| `PLAY` | 8 | Débuts de lecture vidéo (initiales ou après pause) |
| `WATCH` | 7 | Heartbeats de visionnage continu avec chronométrage précis |
| `PAUSE` | 2 | Actions utilisateur de mise en pause de la lecture |
| `SKIP` | 2 | Zappes rapides (< 3s) de la vidéo vers la suivante |
| `COMPLETED` | 1 | Visionnages complets (100% de la durée atteinte) |
| `LIKE` | 1 | Mentions J'aime déclenchées depuis le Feed |
| `SHARE` | 1 | Partages de la fiche vidéo |
| `DISH_CLICK` | 1 | Clics sur l'overlay / fiche du plat présenté |
| `CART_ADD` | 1 | Ajouts au panier déclenchés directement depuis la vidéo |
| **TOTAL** | **32** | **Interactions capturées via l'API Telemetry** |

---

## 3. Sessions

- **Sessions authentifiées** : 2 (`feed_session_auth_secB_202`, `feed_session_auth_secC_303`)
- **Sessions anonymes** : 3 (`feed_session_anon_secA_101`, `feed_session_anon_secD_404`, `feed_session_anon_secE_505`)
- **Sessions totales** : 5

*Vérification des identifiants :*
- Les visiteurs anonymes conservent leur `session_id` de manière persistante sans générer d'erreurs.
- Les utilisateurs connectés associent automatiquement leur `user_id` aux événements tout en conservant leur `session_id`.
- `session_id` et `user_id` sont strictement isolés dans la base de données.

---

## 4. Watch time

- **Moyenne** : 7,33 secondes
- **Minimum** : 1,50 seconde (Scénario SKIP)
- **Maximum** : 15,00 secondes (Scénario COMPLETED)

*Comportement vérifié :*
Lorsqu'une vidéo est mise en pause ou zappée, le chronomètre s'arrête immédiatement et ne continue pas d'accumuler du temps passif. La reprise (`PLAY`) relance le suivi exact.

---

## 5. Completion

- **Complétion moyenne (`completion_rate`)** : 0,2134 (21,34%)
- **Taux de vidéos complétées (`COMPLETED`)** : 3,1% (1/32)
- **Taux de zappe rapide (`SKIP`)** : 6,2% (2/32)

---

## 6. Conversion

- **Likes** : 1
- **Partages (`SHARE`)** : 1
- **Clics Plat (`DISH_CLICK`)** : 1
- **Ajouts au Panier (`CART_ADD`)** : 1

---

## 7. Dataset

- **Lignes d'événements brutes issues de `VideoEventLog`** : 32
- **Lignes d'événements nettoyées et validées (`TelemetryDataCleaner`)** : 32
- **Lignes d'événements rejetées** : 0
- **Lignes finales générées dans le dataset tabulaire (`DatasetBuilder`)** : 32

---

## 8. Qualité

- **Événements invalides** : 0
- **Doublons anormaux** : 0
- **Problèmes détectés** : Aucun. Les événements répétés `WATCH` sont légitimes et correspondent aux heartbeats réguliers envoyés durant la lecture active.

---

## 9. Cold Start

- **Nouvel utilisateur authentifié (sans historique)** : L'extraction de caractéristiques (`FeatureExtractor.extract_user_features`) retourne des valeurs par défaut (`is_authenticated: True`, `user_total_events: 0`, `user_avg_watch_time: 0.0`) sans aucune exception ni plantage.
- **Visiteur anonyme** : L'extraction basée sur `session_id` gère les agrégations à chaud sans nécessiter de compte utilisateur.
- **Nouvelle vidéo (sans historique)** : Les métriques de popularité s'initialisent à 0 (`video_total_likes: 0`, `video_total_views: 0`) et permettent l'enregistrement fluide des événements.

---

## 10. Tests

Résultat exact de l'exécution de `python manage.py test apps.telemetry` :

```text
Creating test database for alias 'default'...
System check identified no issues (0 silenced).
----------------------------------------------------------------------
Ran 21 tests in 17.639s

OK
Destroying test database for alias 'default'...
```

---

## 11. Feed

- **Feed modifié** : **NON** (0 modification sur l'ordre du feed, 100% chronologique).
- **UX vidéo modifiée** : **NON** (`HomeComponent`, `FoodPostComponent`, scroll, autoplay, son restent inchangés).

---

## 12. État pour la suite

- **Collecte fonctionnelle** : **OUI**. La chaîne complète Angular $\rightarrow$ Django API $\rightarrow$ `VideoEventLog` $\rightarrow$ `DatasetBuilder` est operational et validée en situation réelle.
- **Données suffisantes pour entraînement ML** : **NON**. Bien que les 32 événements réels et les 5 sessions permettent de valider techniquement le pipeline, le volume reste au stade initial d'observation et ne constitue pas un corpus statistique suffisant pour entraîner un modèle de production.
- **Prochaines étapes** : Continuer l'accumulation passive des données utilisateurs en production jusqu'à atteindre un volume de plusieurs centaines de sessions qualifiées avant le premier déploiement de la recommandation.
