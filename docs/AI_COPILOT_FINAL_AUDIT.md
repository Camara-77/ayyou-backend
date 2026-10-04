# AUDIT COMPLET FINAL ET DIAGNOSTIC TECHNIQUE — COPILOTE IA AYYOU

**Statut :** AUDIT TECHNIQUE & FONCTIONNEL (AUCUN CODE MODIFIÉ)  
**Date :** 3 Octobre 2026  
**Projet :** Copilote IA AYYOU (Angular + Django REST + PostgreSQL + Whisper + Moondream)  

---

## 1. ARCHITECTURE ACTUELLE DU COPILOTE

### FRONTEND (Angular 19 Standalone)
- **Composant principal Copilot :** `PlanningAiComponent` (`src/app/features/client/pages/planning-ai/planning-ai.component.ts`, `.html`, `.scss`).
  - Interface unique partagée par le bouton flottant (`/planning/ai?mode=CHAT`) et le bouton "Planifier avec l'IA" (`/planning/ai?mode=PLANNING`).
- **Services IA & Audio :**
  - `PlanningAiService` (`src/app/core/services/planning-ai.service.ts`) : REST client vers `/api/ai/planning-parse/`, `/api/ai/conversations/`.
  - `VoiceTranscriptionService` (`src/app/core/services/voice-transcription.service.ts`) : Capture audio MediaRecorder, appel POST `/api/ai/transcribe-voice/`.
- **Composants d'affichage dans le Copilot :**
  - Cartes restaurants inline (`.restaurant-grid-card`)
  - Cartes produits inline (`.detected-dish-card`) avec boutons doubles `[Commander]` et `[Planifier]`
  - Carte recommandation du chef (`.featured-recommendation-card`)
  - Barre de recherche inline dans les résultats (`.catalog-inline-search-bar`)
- **Composants et services externes réutilisables :**
  - `ProductDetailComponent` (`src/app/features/client/pages/product-detail/product-detail.component.ts`) sur la route `/product/:id`.
  - `CartService` (`src/app/core/services/cart.service.ts`) & `CartComponent` (`/cart`).
  - `PlanningService` (`src/app/core/services/planning.service.ts`) & `PlanningComponent` (`/planning`).

### BACKEND (Django REST Framework + PostgreSQL)
- **Point d'entrée principal :** `AIPlanningParseView` (`apps/ai/views_planning_ai.py` -> `POST /api/ai/planning-parse/`).
- **Couche Catalogue Centralisée :** `CatalogSearchService` (`apps/catalog/catalog_service.py`).
- **Service d'analyse d'image :** `VisionService` (`apps/ai/vision_service.py`) via Moondream (Ollama / CPU).
- **Service de transcription vocale :** `TranscriptionService` (`apps/ai/transcription.py`) via FFmpeg + Google ASR + Whisper fallback.
- **Outils catalogue (Tools) :** `apps/ai/tools.py` (`search_food_paginated`, `search_establishments_paginated`, `search_active_categories`).
- **Modèles de persistance :**
  - `AIConversation` & `AIMessage` (`apps/ai/models.py`)
  - `Produit`, `Etablissement`, `Categorie` (`apps/catalog/models.py`)
  - `RepasPlanifie`, `Commande`, `Panier` (`apps/orders/models.py`)

---

## 2. AUDIT DES INTENTIONS ACTUELLEMENT IMPLÉMENTÉES

| Intention | Fichier Backend | Méthode / Bloc | Déclencheurs | Action Frontend | Statut |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `GREETING` | `views_planning_ai.py` | L520-L535 | "bonjour", "salut", "coucou" | Message d'accueil + puces | OK |
| `RESTAURANT_SEARCH` | `views_planning_ai.py` | L984-L1034 | "voir les restaurants", "où trouver..." | Grille de restaurants | OK |
| `PRODUCT_SEARCH` | `views_planning_ai.py` | L1036-L1108 | "rechercher des plats", "que puis-je manger" | Liste de cartes plats | OK (Ajustements requis) |
| `CATEGORY_SEARCH` | `views_planning_ai.py` | L963-L981 | "quelles sont les catégories", nom catégorie | Plats filtrés par catégorie | OK |
| `BUDGET_DISCOVERY` | `views_planning_ai.py` | L718-L738 | "j'ai 5000 FCFA" (budget seul) | Puces de sélection | OK |
| `FOOD_RECOMMENDATION`| `views_planning_ai.py` | L794-L874 | "recommande", "ingrédients", "avec du..." | Carte héro ou question | OK |
| `SELECT_RESTAURANT` | `views_planning_ai.py` | L413-L428 | "je sélectionne X", anaphore 1er resto | Sélection resto + puces | OK |
| `SHOW_RESTAURANT_DISHES`| `views_planning_ai.py`| L212-L246 | "ses plats", "son menu" | Plats du restaurant | Partiellement ambigu |
| `BACK_TO_RESTAURANTS` | `views_planning_ai.py`| L192-L210 | "retour aux restaurants" | Restaure liste restos | OK |
| `CREATE_PLANNING` | `views_planning_ai.py` | L1050-L1108 | "planifier", "je veux planifier..." | Formulaire & fiche récap | OK |
| `CONFIRM_PLANNING` | `views_planning_ai.py` | L270-L361 | "oui, planifier", "je confirme" | Écriture DB + succès | OK |
| `DECLINE_PLANNING` | `views_planning_ai.py` | L248-L267 | "non", "annuler" | Annulation planification | OK |
| `GENERAL_FOOD_HELP` | `views_planning_ai.py` | L756-L793 | "c'est quoi le thieb", "explique..." | Explication + spécialités | OK |
| `APP_FOOD_HELP` | `views_planning_ai.py` | L740-L755 | "comment commander", "aide" | Explication fonctionnalités | OK |
| `GENERAL_CONVERSATION`| `views_planning_ai.py`| L682-L696 | "ça va", "comment vas-tu" | Réponse courtoise | OK |
| `OUT_OF_SCOPE` | `views_planning_ai.py` | L699-L715 | "django", "postgres", "secret" | Refus hors domaine | OK |
| `ANAPHORA_RESOLUTION` | `views_planning_ai.py` | L363-L450 | "1er", "2ème", "le moins cher" | Résolution contextuelle | OK (Problème sur AMBIGUOUS) |

### INTENTIONS ABSENTES OU NON DÉTECTÉES :
1. **`PRODUCT_DETAIL`** : Non implémentée backend. La demande *"Donne-moi les détails de ce plat"* retombe sur `GENERAL_CONVERSATION` (*"Je n'ai pas bien compris"*).
2. **`ADD_TO_CART` / `ORDER_NOW`** : Le Copilot ne possède pas d'intention backend pour ajouter directement un plat au panier API (`POST /api/orders/cart/items/`). Il effectue une simple redirection navigateur vers `/product/:id`.
3. **`ORDER_TRACKING` / `MY_ORDERS`** : Aucune intention backend pour consulter ou suivre ses commandes en cours (*"Où en est ma commande ?"*).

---

## 3. AUDIT DES TESTS DE BUDGET (EXÉCUTION RÉELLE POSTGRESQL)

| N° | Requête Utilisateur | Intention Détectée | Terme Extrait | Budget Extrait | Produits / Restos Trouvés | Message Backend | Cartes Angular | Diagnostic |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **1** | *"Je veux manger avec 5 000 FCFA."* | `FOOD_SEARCH` | `""` | `5 000` | 6 produits | *"Voici les plats disponibles sur AYYOU..."* | **AFFICHIÉES** | OK |
| **2** | *"Je veux manger avec 3 000 FCFA."* | `FOOD_SEARCH` | `""` | `3 000` | 6 produits | *"Voici les plats disponibles sur AYYOU..."* | **AFFICHIÉES** | OK |
| **3** | *"Je cherche un burger avec 3 000 FCFA."* | `FOOD_SEARCH` | `"burger"` | `3 000` | 0 produit | *"Voici les plats disponibles sur AYYOU..."* | **MASQUÉES** | **Cause :** 0 produit sous 3000 FCFA. Angular masque car `matching_products.length === 0`. Message trompeur backend. |
| **4** | *"Je cherche du thiéboudienne avec 5 000 FCFA."* | `FOOD_SEARCH` | `"thiéboudienne"` | `5 000` | 4 produits | *"Voici les plats disponibles sur AYYOU..."* | **AFFICHIÉES** | OK |
| **5** | *"Quels plats puis-je avoir avec 5 000 francs ?"* | `FOOD_SEARCH` | `"avoir"` | `5 000` | 1 produit | *"Voici les plats disponibles sur AYYOU..."* | **AFFICHIÉES (1 seul)** | **Cause :** Le mot parasite `"avoir"` n'est pas dans `stop_words`. Backend cherche un produit contenant `"avoir"`. |
| **6** | *"Quels restaurants proposent des plats à 5 000 FCFA max ?"* | `RESTAURANT_SEARCH` | `"maximum"` | `5 000` | 0 resto | *"Je n'ai trouvé aucun restaurant proposant du maximum..."* | **MASQUÉES** | **Cause :** Le mot parasite `"maximum"` est extrait comme nom de plat ! Recherche d'un resto vendant du "maximum". |

---

## 4. AUDIT DES CAS SANS RÉSULTAT (DISTINCTION A, B, C, D)

Actuellement, lorsqu'aucun produit n'est trouvé pour une recherche sous budget (ex. *"Je cherche un burger à 3 000 FCFA"*), le backend renvoie :
- `matching_products: []`
- `message: "Voici les plats disponibles sur AYYOU pour un budget max de 3 000 FCFA :"`

**Le backend ne distingue pas encore :**
- **Cas A (Absence absolue) :** Le plat n'existe pas dans la base.
- **Cas B (Dépassement de budget) :** Des burgers existent (ex. à 3 500 FCFA et 4 000 FCFA), mais dépassent le budget de 3 000 FCFA.
- **Cas C (Plat indisponible mais autres plats dans le budget) :** Pas de burger à 3 000 FCFA, mais d'autres plats (ex. Salades, Pastels) sont disponibles à 3 000 FCFA.
- **Cas D (Propositions proches) :** Le plat le plus proche coûte 3 500 FCFA (+500 FCFA).

---

## 5. AUDIT DU FLUX D'AFFICHAGE DES CARTES (ANGULAR)

### Flux d'affichage :
`POST /api/ai/planning-parse/` $\rightarrow$ `JSON` $\rightarrow$ `PlanningAiService` $\rightarrow$ `PlanningAiComponent` $\rightarrow$ `chatMessages.push()` $\rightarrow$ `*ngIf` dans `planning-ai.component.html`.

### Causes exactes de disparition des cartes dans l'interface :
1. **Filtre `length > 0` dans Angular (L242 `planning-ai.component.html`) :**  
   `*ngIf="msg.parsedData?.matching_products && msg.parsedData!.matching_products!.length > 0 && msg.parsedData?.intent !== 'FOOD_RECOMMENDATION'"`  
   Si `matching_products` est vide (`[]`), la condition s'évalue à `false`. Angular affiche le texte du Copilot mais **masque complètement la section des cartes**, sans message d'erreur ou d'alternative.
2. **Ignorance de l'intention `AMBIGUOUS` :**  
   Lorsqu'un terme comme *"thiéboudienne"* est soumis sans verbe d'action, le backend renvoie `intent: "AMBIGUOUS"` avec un texte de clarification, mais **sans inclure `matching_products`** dans le payload JSON. L'anaphore suivante ("Le premier") échoue immédiatement avec `out_of_bounds` ("Je n'ai que 0 plats").
3. **Erreur de ciblage dans "Ses plats" :**  
   Si l'utilisateur sélectionne un produit (ex. "Le deuxième" $\rightarrow$ *Thiéboudienne*), puis dit *"Montre-moi ses plats"*, le backend cherche `selected_restaurant`. N'en trouvant pas, il prend `last_results['items'][0]`, qui est le produit *Dibi Agneau & Aloco*, et génère l'intitulé erroné : *"Voici les plats proposés par Dibi Agneau & Aloco :"*.

---

## 6. AUDIT DETAILED PRODUCTS & PARCOURS COMMANDER / PLANIFIER

### Détails Produit (Étape 7)
- **Composant existant :** `ProductDetailComponent` (`/product/:id`).
- **Situation Copilot :** Le Copilot ne possède pas de vue détaillée repliable ou inline. Une demande de détail retombe sur `GENERAL_CONVERSATION`.
- **Possibilité :** Le payload backend `detected_product` contient déjà l'image, le nom, la description, le prix et le restaurant. Il suffit de créer une intention `PRODUCT_DETAIL` backend et la carte correspondante dans le template.

### Commander (Étape 8)
- **Parcours réel AYYOU :** Produit $\rightarrow$ `CartService.addToCart(prod)` $\rightarrow$ `POST /api/orders/cart/items/` $\rightarrow$ Panier `/cart` $\rightarrow$ Checkout `/checkout`.
- **Situation Copilot :** Le Copilot effectue uniquement un routage Angular (`router.navigate(['/product', prod.id])`). Il ne déclenche pas directement l'API Panier.

### Planification (Étape 9)
- **Parcours réel AYYOU :** `CREATE_PLANNING` $\rightarrow$ `CONFIRM_PLANNING` $\rightarrow$ `RepasPlanifie.objects.create()`.
- **Situation Copilot :** **100% Fonctionnel.** Le flux de planification avec garde-fou de confirmation écrit réellement dans la table `RepasPlanifie` de PostgreSQL en toute sécurité.

---

## 7. AUDIT VOIX / WHISPER & QUALITÉ AUDIO

- **Chaîne de traitement :** Microphone WebM 16kHz $\rightarrow$ Conversion FFmpeg en WAV 16kHz mono $\rightarrow$ `speech_recognition` (Google ASR fr-FR) $\rightarrow$ Fallback Whisper (`openai/whisper-base` CPU + prompt sénégalais).
- **Diagnostic Qualité Audio & VAD :**
  - Le MediaRecorder navigateur utilise le VAD standard du navigateur. Une pause de plus de 1.5 seconde dans la parole déclenche l'arrêt de l'enregistrement et la transcription d'une phrase incomplète.
- **Diagnostic de Compréhension :**
  - **Résultat d'audit :** Whisper transcrit parfaitement le français et le vocabulaire sénégalais (*"thiéboudienne"*, *"yassa"*, *"mafé"*, *"5000 FCFA"*).
  - **La cause des mauvaises réponses est backend (IA / Parser) :** L'extraction des mots-clés dans `_find_matching_product` prend des mots comme `"maximum"`, `"avoir"`, `"francs"` comme des noms de plats, ce qui pollue la requête SQL PostgreSQL.

---

## 8. AUDIT SÉCURITÉ & PERMISSIONS

- **Authentification :** `SafeJWTAuthentication` gère les requêtes anonymes via `session_key` et authentifiées via JWT Bearer token.
- **Protection des données sensibles :** Aucune clé (`SECRET_KEY`, `PAYTECH_API_KEY`, etc.), mot de passe ou fichier système n'est exposé. L'intention `OUT_OF_SCOPE` intercepte et bloque toutes les tentatives d’injection de mots-clés techniques (`django`, `select *`, `admin`, `password`).
- **Isolation Utilisateur :**
  - `AIConversation.objects.filter(utilisateur=request.user)` garantit l'isolation absolue des fils de discussion.
  - `RepasPlanifie.objects.filter(utilisateur=request.user)` garantit l'isolement des plannings.

---

## 9. MATRICE DES ACTIONS COMPLÈTE

| Action | Mode CHAT | Mode PLANNING | Texte | Voix | Exécution Réelle |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Recherche restaurant** | ✅ Oui | ✅ Oui | ✅ Oui | ✅ Oui | ✅ PostgreSQL |
| **Recherche plat** | ✅ Oui | ✅ Oui | ✅ Oui | ✅ Oui | ✅ PostgreSQL |
| **Budget max** | ✅ Oui | ✅ Oui | ✅ Oui | ✅ Oui | ✅ PostgreSQL (Mots parasites à nettoyer) |
| **Détails restaurant** | ✅ Oui | ✅ Oui | ✅ Oui | ✅ Oui | ✅ PostgreSQL |
| **Détails plat** | ❌ Non | ❌ Non | ❌ Non | ❌ Non | ❌ Intention `PRODUCT_DETAIL` manquante |
| **Ajouter au panier** | ❌ Non | ❌ Non | ❌ Non | ❌ Non | ❌ Remplacé par lien `/product/:id` |
| **Commander** | 🟡 Redirection | 🟡 Redirection | ✅ Oui | ✅ Oui | 🟡 Redirection vers fiche produit |
| **Planifier** | ✅ Oui | ✅ Oui | ✅ Oui | ✅ Oui | ✅ Écriture réelle `RepasPlanifie` |
| **Modifier planning** | ✅ Oui | ✅ Oui | ✅ Oui | ❌ Non | ✅ Formulaire inline |
| **Annuler planning** | ✅ Oui | ✅ Oui | ✅ Oui | ✅ Oui | ✅ Statut ANNULE |
| **Suivre commande** | ❌ Non | ❌ Non | ❌ Non | ❌ Non | ❌ Intention `ORDER_TRACKING` manquante |

---

## 10. DIAGNOSTIC GLOBAL ET CLASSIFICATION DES PROBLÈMES

### P0 (Bloquants / Anomalies majeures)
1. **Pollution des termes de recherche (`_find_matching_product`) :**  
   Mots parasites (`maximum`, `avoir`, `francs`, `donne`, `propose`) non inclus dans `stop_words`, qui sont extraits comme noms de plats et annulent les résultats PostgreSQL.
2. **Masquage silencieux des cartes sous Angular quand `matching_products = []` :**  
   Absence de carte ou de message alternatif d'explication quand un produit recherché sous budget n'existe pas.
3. **Rupture de contexte sur l'intention `AMBIGUOUS` :**  
   La réponse ambiguë ne renvoie pas la liste des plats trouvés dans `last_results`, faisant échouer la sélection suivante par anaphore ("Le premier").

### P1 (Dégradation de l'expérience)
1. **Absence de l'intention `PRODUCT_DETAIL` :**  
   "Donne-moi les détails de ce plat" renvoie *"Je n'ai pas bien compris"*.
2. **Absence d'ajout direct au panier API :**  
   `[Commander]` redirige vers la page produit au lieu d'exécuter un ajout au panier ou une ouverture du checkout.
3. **Confusion sur "Ses plats" :**  
   Incapacité de retrouver le restaurant parent lorsqu'un produit (et non un restaurant) est actuellement sélectionné dans le contexte.
4. **Absence de distinction A, B, C, D sur les recherches sans résultat :**  
   Pas de différence expliquée entre budget insuffisant, plat inexistant ou alternatives disponibles.

### P2 (Optimisations secondaires)
1. **Sensibilité du microphone VAD :**  
   Risque de coupure si l'utilisateur fait une pause de plus de 1.5s.
2. **Absence de l'intention Suivi de commande (`ORDER_TRACKING`).**

---

## 11. RECOMMANDATION D'ORDRE DES CORRECTIONS POUR LA PROCHAINE PHASE

1. **Étape 1 (Correction P0 Backend) :** Enrichir `stop_words` dans `_find_matching_product` avec les termes de liaison et de mesure (`maximum`, `max`, `avoir`, `francs`, `fcfa`, `donne`, `propose`, `disponible`, `trouver`).
2. **Étape 2 (Correction P0 Frontend/Backend) :** Gérer explicitement les cas 0 résultat dans Angular avec affichage d'un message d'explication clair et des propositions alternatives.
3. **Étape 3 (Correction P0 Context) :** Conserver `matching_products` dans `last_results` même lors des réponses de statut `AMBIGUOUS` pour ne pas rompre la chaîne des anaphores.
4. **Étape 4 (Implémentation P1) :** Ajouter l'intention `PRODUCT_DETAIL` backend et la carte de détail produit complète dans Angular.
5. **Étape 5 (Implémentation P1) :** Connecter l'action `[Commander]` au `CartService` pour permettre l'ajout direct au panier.
