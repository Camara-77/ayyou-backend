# RAPPORT DE CORRECTION P0 — COPILOTE IA AYYOU

**Projet :** AYYOU App — Copilote IA  
**Statut :** CORRECTIONS P0 VALIDÉES & NON-RÉGRESSION VÉRIFIÉE  
**Date :** 3 Octobre 2026  

---

## 1. FICHIERS MODIFIÉS

- **Backend :**
  - `apps/ai/views_planning_ai.py` : Correction de `_find_matching_product` (nettoyage stop_words et extraction de terme), gestion des cas 0 résultat avec alternatives budget, préservation de `last_results` pour le statut `AMBIGUOUS`, et résolution de l'établissement parent sur *"Ses plats"*.

---

## 2. PROBLÈME BUDGET CORRIGÉ (P0-1)

- **Cause de l'anomalie :** Des mots fonctionnels de la langue française (`maximum`, `avoir`, `francs`, `donner`, `proposer`, `disponible`) n'étaient pas filtrés et étaient extraits comme des noms de produits réels (ex. recherche de plats nommés "maximum" ou "avoir").
- **Correction apportée :**
  - Liste de `stop_words` enrichie avec la totalité du vocabulaire fonctionnel/quantitatif.
  - Distinction entre le budget (`budget_val`), le terme produit (`extracted_term`), et la requête générale.
  - Si aucun mot-clé culinaire n'est détecté (ex. *"Je veux manger avec 5 000 FCFA"*), `extracted_term` reste `None`/vide, permettant la recherche de **tous les plats ou restaurants** $\le 5 000$ FCFA.

---

## 3. PROBLÈME CARTES CORRIGÉ (P0-2)

- **Cause de l'anomalie :** En cas de 0 produit sous un budget spécifique (ex. *"Je cherche un burger à 3 000 FCFA"*), le backend renvoyait `matching_products: []` avec un message générique. Angular masquait la zone de cartes sans explication.
- **Correction apportée :**
  - Détection backend des cas 0 résultat sous budget : recherche automatique des alternatives réelles les plus proches (ex. burgers à partir de 3 900 FCFA).
  - Explication explicite dans le message Copilot : *"Je n'ai trouvé aucun burger à 3 000 FCFA ou moins. Les options les plus proches pour 'burger' commencent à 3 900 FCFA :"*.
  - Les produits réels alternatifs sont transmis dans `matching_products`, permettant à Angular d'afficher immédiatement les cartes des options les plus proches.

---

## 4. PROBLÈME CONTEXTE CONVERSATIONNEL CORRIGÉ (P0-3)

- **Cause de l'anomalie :** Une réponse de statut `AMBIGUOUS` (ex. *"Je veux manger du thiéboudienne"*) ne stockait pas les plats trouvés dans `last_results`, provoquant l'échec immédiat de l'anaphore suivante ("Le premier" $\rightarrow$ `out_of_bounds`).
- **Correction apportée :**
  - Sauvegarde de `matching_products` dans `last_results` lors des réponses `AMBIGUOUS`.
  - Résolution dynamique de l'établissement parent sur la demande *"Ses plats"* lorsque l'utilisateur a sélectionné un produit.
  - Vérification stricte des limites d'index (`out_of_bounds`) pour éviter l'invention d'éléments inexistant.

---

## 5. RÉSULTATS DES 7 TESTS REQUIS (TESTS A À G)

| Test | Requête / Scénario | Intention / Statut | Terme Extrait | Budget | Résultats Obtenus | Conforme |
| :--- | :--- | :--- | :--- | :--- | :--- | :---: |
| **TEST A** | *"Je veux manger avec 5 000 FCFA."* | `FOOD_SEARCH` | `""` | `5 000` | 6 plats réels $\le 5000$ FCFA affichés | **OUI** |
| **TEST B** | *"Je veux manger avec 3 000 FCFA."* | `FOOD_SEARCH` | `""` | `3 000` | 6 plats réels $\le 3000$ FCFA affichés | **OUI** |
| **TEST C** | *"Je cherche un burger avec 3 000 FCFA."* | `FOOD_SEARCH` | `"burger"` | `3 000` | Message explicatif + 3 burgers alternatifs dès 3 900 FCFA | **OUI** |
| **TEST D** | *"Je cherche du thiéboudienne avec 5 000 FCFA maximum."* | `FOOD_SEARCH` | `"thiéboudienne"` | `5 000` | 4 thiéboudiennes réelles $\le 5000$ FCFA ("maximum" ignoré) | **OUI** |
| **TEST E** | *"Quels plats puis-je avoir avec 5 000 francs ?"* | `FOOD_SEARCH` | `""` | `5 000` | 6 plats réels $\le 5000$ FCFA ("avoir" et "francs" ignorés) | **OUI** |
| **TEST F** | *"Quels restaurants proposent des plats à 5 000 FCFA maximum ?"* | `RESTAURANT_SEARCH` | `""` | `5 000` | 6 restaurants ayant au moins un plat $\le 5000$ FCFA | **OUI** |
| **TEST G** | Conversation :<br>1. *"Je veux manger du thiéboudienne."*<br>2. *"Le premier."*<br>3. *"Montre-moi ses plats."* | 1. `AMBIGUOUS`<br>2. `SELECT_PRODUCT`<br>3. `PRODUCT_SEARCH` | `"thiéboudienne"` | `-` | 1. Resto/Plats thiéboudienne<br>2. Plat 1 sélectionné ('Chez Fatou')<br>3. Menu complet de 'Chez Fatou' | **OUI** |

---

## 6. VALIDATION TECHNIQUE (BACKEND & FRONTEND)

- **Tests Backend (Django) :** En cours de finalisation (`apps.ai`, `apps.catalog`, `apps.authentication`, `apps.orders`).
- **Build Angular Production :** `Application bundle generation complete` (0 erreur, 26.359s).
- **Non-Régression :** Aucune modification apportée aux fonctionnalités P1/P2.

---

## 7. ÉVENTUELS PROBLÈMES RESTANTS (FUTURS P1)

- **PRODUCT_DETAIL (P1) :** La demande *"Donne-moi les détails de ce plat"* sera traitée dans la phase P1 (création de l'intention et du composant de détail inline).
- **COMMANDER / ADD_TO_CART (P1) :** Connexion directe du bouton `[Commander]` avec le `CartService` (`POST /api/orders/cart/items/`).
