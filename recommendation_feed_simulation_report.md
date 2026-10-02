# Rapport de Simulation de Feed Personnalisé par IA — Phase 6
**Projet :** AYYOU  
**Date :** 1er Octobre 2026  
**Modèle Évalué :** LightGBM LambdaMART V2 (`recommender_lgbm_v2.joblib`)  
**Statut :** Simulation Hors-Feed Terminée — Isolation 100% Confirmée  

---

## 1. Résumé Exécutif

La **Phase 6** a permis de simuler et comparer le classement des vidéos du Feed AYYOU généré par le modèle **LightGBM LambdaMART V2** par rapport au classement **Chronologique strict** actuellement en production (`/api/catalog/feed/`).

### Constats Majeurs :
1. **Isolation Totale du Feed de Production :** Le feed principal de production et l'application frontend Angular n'ont été soumis à **aucune modification**. La simulation s'est déroulée via un moteur offline dédié (`apps.telemetry.ml.simulate_feed`) et la commande CLI `python manage.py simulate_recommendation_feed`.
2. **Réordonnancement Effectif :** Pour un utilisateur avec un historique riche (Utilisateur #185 Modou Diop), le modèle IA a réordonné **7 vidéos sur 8 (87.5%)**, avec un déplacement moyen de **2.0 positions**.
3. **Corrélation de Rang (IA vs Chronologique) :** Pour l'utilisateur #185, le coefficient de Spearman $\rho = 0.4286$ et Kendall $\tau = 0.2857$ démontrent une modification significative du classement sans être un renversement chaotique.
4. **Gestion Parfaite du Cold Start :** Pour les utilisateurs anonymes ou nouveaux, le système retombe de manière transparente sur un scoring basé sur la popularité globale (likes/partages) sans produire de valeurs `NaN` ni d'erreurs d'inférence.
5. **Validation par les Tests Automated :** 37 tests unitaires Django couvrant la télémétrie, la préparation de données, le pipeline ML, le service de scoring et le moteur de simulation de feed passent tous avec succès.

---

## 2. Méthodologie et Scénarios de Simulation

Le pool de candidat simulé comprend l'ensemble des 8 publications actives du catalogue AYYOU (IDs `#38` à `#45`).

### Scénarios simulés :
- **Scénario A — Utilisateur Authentifié avec Historique Riche (`user_id=185` - Modou Diop) :** Utilisateur ayant effectué plusieurs sessions de visionnage complets, likes et ajouts au panier (ex: Thiéboudienne, Dibi Agneau).
- **Scénario B — Utilisateur Authentifié avec Faible Historique :** Utilisateur ayant 1 ou 2 événements enregistrés.
- **Scénario C — Utilisateur Anonyme (`session_id="anon_sim_session_999"`) :** Aucun historique utilisateur en base (Cold Start).
- **Scénario D — Analyse Globale Multi-Profils :** Exécution comparée sur l'ensemble des profils.

---

## 3. Résultats Détaillés de la Simulation (Scénario A - Modou Diop #185)

### Tableau Comparatif des Rangs (Chronologique vs LightGBM V2)

| ID Pub | Titre / Produit | Rang Chrono | Rang IA (V2) | Score IA V2 | Déplacement | Interprétation IA |
|---|---|:---:|:---:|:---:|:---:|---|
| **#41** | Thiéboudienne Rouge Penda Mbaye | 5ème | **2ème** | +0.4851 | **+3 positions** | Élevée en raison des affinités passées sur la catégorie Cuisine Sénégalaise et du taux de complétion élevé. |
| **#38** | Dibi Agneau Haoussa | 8ème | **4ème** | +0.2104 | **+4 positions** | Remontée forte grâce à l'historique d'ajouts au panier et de partages sur les grillades. |
| **#44** | Mérou Thiof Entier Grillé | 2ème | **6ème** | -0.1542 | **-4 positions** | Déclassée pour cet utilisateur qui n'a pas montré d'intérêt récent pour les poissons. |
| **#42** | Yassa Poulet Yoff | 4ème | **3ème** | +0.3120 | **+1 position** | Progression modérée alignée sur la popularité et les récents visionnages. |
| **#45** | Mafé Viande de Bœuf | 1er | **1er** | +0.8920 | **0 position** | Maintenue en tête grâce au score maximal combinant popularité globale et affinité utilisateur. |
| **#43** | Pastels au Poisson | 3ème | **5ème** | +0.0520 | **-2 positions** | Déplacement mineur vers le bas. |
| **#40** | Juice Bouye / Pain de Singe | 6ème | **7ème** | -0.3210 | **-1 position** | Boisson rétrogradée en fin de feed pour favoriser les plats principaux. |
| **#39** | Thiakry Dessert | 7ème | **8ème** | -0.4510 | **-1 position** | Maintenue en position basse. |

---

## 4. Métriques Perturbation & Rangs

- **Nombre total de vidéos évaluées :** 8
- **Nombre de vidéos déplacées :** 7 / 8 (87.5%)
- **Déplacement moyen absolu :** 2.0 positions
- **Déplacement maximal :** +4 positions (`#38` Dibi Agneau) / -4 positions (`#44` Mérou Thiof)
- **Coefficient de Corrélation de Spearman ($\rho$) :** `0.4286`
- **Coefficient de Corrélation de Kendall ($\tau$) :** `0.2857`

### Analyse :
Le modèle LightGBM V2 apporte une **personnalisation active et cohérente** sans déstructurer complètement l'ordre initial. Les plats à forte affinité démontrée par le comportement de Modou Diop (grillades et Thiéboudienne) sont remontés dans le Feed, tandis que les catégories moins consultées sont reléguées.

---

## 5. Garanties de Sécurité et de Non-Régression

1. **Aucune Modification de l'Endpoint du Feed Live (`/api/catalog/feed/`) :** L'API continue de retourner les publications triées par date de création décroissante (`-date_creation`).
2. **Isolation du Frontend :** Aucun composant Angular (`HomeComponent`, `FoodPostComponent`, etc.) n'a été touché. Le scroll-snap, l'autoplay, le son et la lecture vidéo restent intacts.
3. **Absence de NaNs dans le Scoring :** Tous les scores prédits sont des flottants valides.
4. **Conservation des Modèles V1 et V2 :** Les deux fichiers `recommender_lgbm_v1.joblib` et `recommender_lgbm_v2.joblib` sont archivés dans `models/recommender/` avec leurs fichiers de métadonnées JSON respectifs.

---

## 6. Propositions Techniques pour la Phase 7 (À valider par l'équipe)

Si l'équipe valide le passage à la Phase 7 (Déploiement progressif du Feed IA), nous recommandons l'architecture suivante :

1. **Création d'un Endpoint Dédié ou Flag d'Activation :**
   - Option A : Créer `/api/catalog/feed/recommendations/` pour tester le feed IA sur des utilisateurs bêta.
   - Option B : Ajouter un paramètre query `?personalized=true` sur `/api/catalog/feed/` contrôlé par un feature flag backend.
2. **Stratégie A/B Testing / Fallback Hybride (Heuristic Blend) :**
   - Mix par défaut : 80% du score basé sur LightGBM V2 + 20% de récence chronologique pour éviter de bloquer le feed sur de vieux contenus.
3. **Protection Cold Start Inconditionnelle :**
   - Si `user_id` est anonyme ou a moins de 3 événements, le système retombe automatiquement sur le feed chronologique ou populaire sans appeler le modèle de scoring lourd.
