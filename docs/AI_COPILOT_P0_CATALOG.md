# DOCUMENTATION TECHNIQUE — PHASE P0 : ASSAINISSEMENT CATALOGUE IA & SOURCE DE VÉRITÉ POSTGRESQL

**Date d'implémentation** : 3 Octobre 2026  
**Module** : Catalogue AYYOU & Interface IA Copilote (`apps/catalog`, `apps/ai`)  
**Statut** : PHASE P0 COMPLÉTÉE  
**Principe Fondamental** : **POSTGRESQL EST LA SEULE SOURCE DE VÉRITÉ MÉTIER.** L'IA n'invente AUCUN produit, restaurant, catégorie, prix ou disponibilité.

---

## 1. PROBLÈME INITIAL

Avant la Phase P0, l'audit architectural du Copilote AYYOU avait révélé :
1. **Catégories Vides Exposées** : 5 catégories actives sur 23 ne possédaient aucun produit disponible (ex: *Boulangerie Pâtisserie*). L'IA suggérait ces catégories, guidant l'utilisateur vers des grilles vides.
2. **Établissements Fantômes** : 18 établissements sur 71 enregistrés ne possédaient aucun produit rattaché en base. L'IA pouvait les recommander lors de découvertes globales de restaurants.
3. **Erreur d'Association par le Nom** : Une recherche type *"Restaurants proposant du thiéboudienne"* filtrait les établissements dont le *nom* contenait la chaîne *"thiéboudienne"* (ex: *"Thiéboudienne Express"*), même si le restaurant ne vendait aucun plat de ce type.
4. **Dispersions des Requêtes ORM** : Des requêtes SQL redondantes et non sécurisées étaient dupliquées dans plusieurs fichiers (`tools.py`, `views_planning_ai.py`).

---

## 2. ARCHITECTURE AVANT P0 VS APRÈS P0

### Architecture Avant P0
```
User Prompt -> AIPlanningParseView -> tools.py (search_food / search_establishments) -> Direct SQL ORM -> Potential Empty Categories/Ests/False Matches
```

### Architecture Après P0
```
User Prompt -> AIPlanningParseView -> tools.py -> CatalogSearchService (Single Source of Truth) -> Strict PostgreSQL Filtering -> Sanitized Result
```

`CatalogSearchService` ([apps/catalog/catalog_service.py](file:///c:/Users/HP/Desktop/Ayyou-backend/apps/catalog/catalog_service.py)) devient l'unique porte d'entrée centralisée pour toutes les consultations du catalogue par l'IA et les APIs.

---

## 3. RÈGLES DE VISIBILITÉ & SÉCURITÉ CATALOGUE

### A. Catégories Exposables
* Une catégorie n'est exposée à l'IA que si `est_active = True` **ET** qu'elle possède au moins 1 produit disponible rattaché à un établissement vérifié (`nombre_plats_dispo > 0`).
* **Résultat** : Les 5 catégories vides sont systématiquement filtrées au niveau de la requête SQL ORM.

### B. Établissements Exposables
* Un établissement n'est proposé que s'il est vérifié (`statut_verification = 'VALIDE'`) **ET** qu'il possède au moins 1 produit disponible (`produits__est_disponible = True`).
* **Résultat** : Les 18 établissements sans menu sont complètement invisibles pour le Copilote IA client.

### C. Flux Strict Produit -> Établissement (Jamais par Nom d'Établissement)
* Lors d'une recherche de restaurant par plat (*"Montre moi les restaurants proposant du thiéboudienne"*), le flux est STRICTEMENT :
  `Recherche Produit matching query` -> `Extract matching establishment_ids` -> `Filter Etablissements by these IDs`.
* Un établissement nommé *"Thiéboudienne Express"* qui ne possède pas de plat thiéboudienne en base ne sera **JAMAIS** retourné.

### D. Gestion du Budget
* La fonction `parse_budget()` normalise et sécurise les saisies utilisateur :
  - `"5000 FCFA"`, `"5 000 FCFA"`, `"5.000 FCFA"`, `"5,000 FCFA"`, `"5000f"`, `"5k"` -> `5000.0 FCFA`.
* Le filtre SQL applique `prix_base__lte = max_price` directement sur la table PostgreSQL `Produit`.

---

## 4. PERFORMANCES ET OPTIMISATION SQL (N+1)

* Utilisation de `select_related('etablissement', 'categorie')` pour récupérer en 1 seule requête SQL jointe le produit et ses métadonnées rattachées.
* Emploi de `.annotate(nombre_plats_dispo=Count(...))` pour calculer les disponibilités directement au niveau du serveur PostgreSQL sans boucle Python coûteuse.
* Pagination native `limit` / `offset` appliquée directement sur les QuerySets Django.

---

## 5. TESTS DE VALIDATION P0 (15/15 VERTS)

Les 15 tests unitaires automatiques de la Phase P0 ([apps/catalog/tests/test_p0_catalog_service.py](file:///c:/Users/HP/Desktop/Ayyou-backend/apps/catalog/tests/test_p0_catalog_service.py)) couvrent :
1. `test_01_search_products_returns_real_products_only` : OK
2. `test_02_search_establishments_by_product_returns_matching_establishments` : OK
3. `test_03_establishment_name_trap_is_not_returned` : OK
4. `test_04_active_empty_category_is_excluded` : OK
5. `test_05_empty_establishment_is_excluded` : OK
6. `test_06_unavailable_product_is_excluded` : OK
7. `test_07_budget_parsing_fcfa` : OK
8. `test_08_budget_parsing_spaced_fcfa` : OK
9. `test_09_budget_parsing_k` : OK
10. `test_10_get_establishment_products_returns_own_products_only` : OK
11. `test_11_non_existent_product_returns_none` : OK
12. `test_12_non_existent_category_returns_none` : OK
13. `test_13_no_results_invented` : OK
14. `test_14_data_privacy_isolation` : OK
15. `test_15_user_permissions_and_isolation` : OK

---

## 6. LIMITES RESTANTES & ORIENTATIONS POUR P1

* **Tool Calling Engine** : P0 sécurise la couche de données mais l'orchestration des intentions dans `views_planning_ai.py` repose encore sur le routeur d'intentions `if/elif`. La Phase P1 introduira le moteur Tool Calling structuré (Pydantic schemas).
* **Anaphores & Discourse Memory** : Le suivi de contexte multi-tours sera renforcé en P1 sur la base des IDs de produits assainis retournés par `CatalogSearchService`.
