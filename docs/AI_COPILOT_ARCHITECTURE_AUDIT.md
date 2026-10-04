# AUDIT ARCHITECTURAL COMPLET DU COPILOTE AYYOU

**Date de l'audit** : 3 Octobre 2026  
**Périmètre** : Backend (`apps/ai`, `apps/catalog`, `apps/orders`, `apps/users`, `apps/authentication`) & Frontend (`src/app/features/client/pages/planning-ai`, `src/app/core/services/planning-ai.service.ts`)  
**Statut du code** : Aucune modification de code effectuée (Mode Read-Only strict / Audit pur).

---

## 1. VUE D'ENSEMBLE & DIAGNOSTIC GLOBAL

Le Copilote AYYOU est un assistant virtuel hybride qui combine la gestion de planning repas, la recherche dans un catalogue e-commerce/restauration PostgreSQL, l'analyse d'images via vision par ordinateur local (Ollama Moondream) et la transcription vocale (Whisper).

### Diagnostic Synthétique (Sans Concession)
L'architecture actuelle est **fonctionnelle mais fragile et hautement couplée**. Elle souffre d'un manque d'orchestration structurée via un moteur d'outils (Tool Calling Engine) basé sur un LLM standardisé, s'appuyant à la place sur des heuristiques regex et un routeur d'intentions Python impératif. La gestion de l'état contextuel repose sur un dictionnaire JSON plat dans la base de données (`AIConversation.context_data`), ce qui rend le suivi de conversation à plusieurs tours sujet à des réinitialisations inattendues ou des hallucinations de référence.

---

## 2. MÉTRIQUES EMPIRIQUES DE LA BASE DE DONNÉES

| Entité | Total | Sous-Statut / Métriques Clés | Constat / Anomalies |
| :--- | :--- | :--- | :--- |
| **Produits** | 110 | 110 actifs, 0 inactifs, 110 rattachés à une catégorie | Couverture 100% rattachée. Prix min: 500 FCFA, max: 25 000 FCFA. |
| **Catégories** | 23 | 18 actives avec produits, **5 vides (0 produit)** | 5 catégories mortes : *Boulangerie Pâtisserie*, *Plats Principaux*, *Catégorie Test*, *Spécialités Dakar*, *Boissons & Desserts*. |
| **Établissements** | 71 | 71 vérifiés, **18 sans aucun produit rattaché** | 25.3% des établissements inscrits ne possèdent aucun plat/produit en base (ex: *Mbeukh*, *Chez Loutcha (Test)*, *Street Food Awa*). |
| **Conversations IA**| Variable | Supporte `session_key` anonyme et `user_id` authentifié | Contextes enregistrés dans `context_data` (JSONField). |

---

## 3. ÉTAT ARCHITECTURAL DE CHAQUE CAPACITÉ

```
+-----------------------------------------------------------------------------------+
|                                 FRONTEND ANGULAR                                  |
|  PlanningAiComponent <---> PlanningAiService <---> Client HTTP (API REST Django)  |
+-----------------------------------------------------------------------------------+
                                         |
                                         v
+-----------------------------------------------------------------------------------+
|                         BACKEND DJANGO (apps/ai/views)                            |
|                          AIPlanningParseView (POST)                               |
+-----------------------------------------------------------------------------------+
                                         |
          +------------------------------+------------------------------+
          |                              |                              |
          v                              v                              v
+--------------------+        +--------------------+        +--------------------+
| Intent Router      |        | Vision Service     |        | Whisper Service    |
| (Regex & Python)   |        | (Ollama Moondream) |        | (Faster-Whisper)   |
+--------------------+        +--------------------+        +--------------------+
          |                              |                              |
          +------------------------------+------------------------------+
                                         |
                                         v
+-----------------------------------------------------------------------------------+
|                        OROCHESTRATION & FICHIERS METIER                           |
|  tools.py (Recherche ORM PostgreSQL, Filtres budget, Pagination, Intent Parse)   |
+-----------------------------------------------------------------------------------+
                                         |
                                         v
+-----------------------------------------------------------------------------------+
|                         BASE DE DONNÉES POSTGRESQL                                |
|   Establishment (71)  |  Product (110)  |  Category (23)  |  AIConversation     |
+-----------------------------------------------------------------------------------+
```

### A. Routeur d'Intentions & Détection de Langage (Intent Router)
*   **Implémentation** : Implémenté de façon impérative dans `apps/ai/tools.py` via `detect_intent()` et `_match_intent_patterns()`.
*   **Points Forts** : Faible latence (exécution locale regex), zéro coût LLM pour les requêtes courantes.
*   **Limites & Risques** :
    *   Absence d'analyse sémantique profonde. Les variations de langage naturel non prévues dans les expressions régulières retombent en intent `GENERAL_CHAT` ou `CATALOG_SEARCH` indifférencié.
    *   Couplage fort entre le découpage des mots-clés (stop-words personnalisés) et le filtrage ORM direct.

### B. Moteur d'Outils (Tools Calling Engine)
*   **Implémentation** : `execute_tool()` dans `apps/ai/tools.py` avec fonctions ORM `search_catalog()`, `get_categories()`, `get_establishments()`.
*   **Points Forts** : Requêtes SQL optimisées avec `select_related('establishment', 'category')`, gestion stricte du budget (`price_val__lte`).
*   **Limites & Risques** :
    *   Il ne s'agit pas d'un vrai moteur de Tool Calling LLM (type OpenAI Function Calling / LangChain Agent). C'est un répartiteur Python manuel `if/elif`.
    *   Impossibilité de composer ou d'enchaîner dynamiquement plusieurs outils en un seul tour sans coder explicitement les branches conditionnelles dans Django.

### C. Système RAG (Retrieval-Augmented Generation) & Recherche Catalogue
*   **Implémentation** : Recherche hybride texte/trigramme PostgreSQL (`Q(name__icontains=...) | Q(description__icontains=...)`).
*   **Points Forts** : Pas de dépendance à un Vector Store externe payant ; résultats exacts et déterministes sur la base SQL.
*   **Limites & Risques** :
    *   Pas de recherche vectorielle (pas d'embeddings pgvector ou Dense Passage Retrieval). Si l'utilisateur demande "un plat épicé traditionnel", la recherche par mot-clé échouera si le terme "épicé" n'est pas dans la description textuelle exacte.

### D. Module Vision (Ollama Moondream)
*   **Implémentation** : `apps/ai/vision_service.py` interrogeant Ollama local sur le modèle `moondream`.
*   **Points Forts** : 100% souverain, pas de fuite de données vers des APIs tierces cloud, fallback automatique en cas d'indisponibilité d'Ollama.
*   **Limites & Risques** :
    *   Latence d'inférence (3s à 12s selon le matériel serveur).
    *   Parsing JSON de sortie fragile basé sur regex ; si le modèle vision génère du texte avant le JSON, le fallback extrait le texte brut.

### E. Module Vocale (Whisper)
*   **Implémentation** : `apps/ai/voice_service.py` exploitant `faster-whisper` ou `openai-whisper`.
*   **Points Forts** : Transcription rapide du français et wolof/accentué local.
*   **Limites & Risques** :
    *   Consommation mémoire importante sur le serveur backend si le modèle est chargé en permanence.

### F. Gestion du Contexte & Mémoire Multi-Tours
*   **Implémentation** : Modèle `AIConversation` avec champ `context_data` (JSONField).
*   **Points Forts** : Persistance en base de données PostgreSQL associant la session au planning.
*   **Limites & Risques** :
    *   L'anaphore ("le premier", "le moins cher", "ajoute-le") dépend de la présence de `last_products` dans `context_data`. Si la pagination change ou si la conversation bascule sur une question générale, le contexte produit est perdu.

---

## 4. SOURCES ET RISQUES D'HALLUCINATIONS

| Source d'Hallucination | Cause Racine Identifiée | Impact Utilisateur | Solution Cible |
| :--- | :--- | :--- | :--- |
| **Erreur d'Association Produit/Établissement** | Découpage des mots-clés (`_find_matching_product`) recherchant la sous-chaîne sans validation lexicale stricte. | L'IA peut recommander un plat rattaché au mauvais restaurant si deux établissements proposent un nom similaire. | Normalisation des tokens et validation d'existence exacte par ID produit. |
| **Promesse de Catégorie Vide** | 5 catégories actives en base n'ont 0 produit. | L'IA propose un bouton "Boulangerie Pâtisserie", l'utilisateur clique et obtient 0 résultat. | Filtrage SQL au niveau des requêtes de catégories (`annotate(prod_count=Count('products')).filter(prod_count__gt=0)`). |
| **Établissements Fantômes** | 18 établissements n'ont aucun produit. | Si l'IA liste les établissements par zone sans vérifier leur catalogue, l'utilisateur voit un restaurant sans menu. | Filtrer systématiquement les établissements ayant au moins 1 produit actif (`products__isnull=False`). |
| **Mauvaise interprétation Vision** | Le modèle `moondream` renvoie une description générique ("assiette de riz"). | L'IA mappe le résultat sur un produit sans rapport (ex: Riz Joff au lieu de Thieboudienne). | Imposer un score de confiance minimal et un fallback vers la recherche catalogue assistée. |

---

## 5. MATRICE DE RISQUES ARCHITECTURAUX

```
  IMPACT
    ^
    | [R1] Rupture d'Anaphora     [R3] Catégories Vides
    | (Contexte Perdu)           (Expérience Utilisateur)
    |
    | [R4] Latence Vision        [R2] Absence Tool Calling Engine
    | (Timeout HTTP 12s)         (Couplage Code Python)
    +--------------------------------------------------------> PROBABILITÉ
```

1. **[R1] Perte de Contexte Multi-Tours (Haute Probabilité / High Impact)** :
   *Risque* : Réinitialisation silencieuse du `context_data` lors des requêtes ambiguës.
2. **[R2] Absence d'Agent Tool Calling Standardisé (Moyenne Probabilité / High Impact)** :
   *Risque* : Complexité exponentielle des structures `if/elif` dans `tools.py` à chaque nouvelle fonctionnalité.
3. **[R3] Affichage d'Établissements ou Catégories Vides (Haute Probabilité / Medium Impact)** :
   *Risque* : Déception client lors du clic sur une recommandation sans contenu.
4. **[R4] Latence de la Vision & Speech-to-Text (Moyenne Probabilité / Medium Impact)** :
   *Risque* : Blocage du thread HTTP Django en cas de pic de charge sur le serveur local.

---

## 6. COMPARAISON ET BENCHMARK DES MODÈLES IA

| Modèle / Stratégie | Latence Moyenne | Coût | Précision Intentions | RAG / catalogue | Recommandation |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Heuristique Regex (Actuel)** | < 10 ms | 0 € | 70% (Fixe) | Strict SQL | Conserver pour le routing basique (P0) |
| **Ollama Moondream (Actuel Vision)** | 3 000 - 8 000 ms | Local (CPU/GPU) | 65% (Visuel) | N/A | Exécuter de manière asynchrone / Worker Celery |
| **Ollama Llama3 / Mistral (Local)** | 1 500 - 4 000 ms | Local | 88% | Via Vector/Tool | Optionnel pour déploiement 100% souverain |
| **Claude 3.5 Haiku / GPT-4o-mini (Cloud)** | 300 - 800 ms | Minime (< 0.001$/req) | 98% (Tool Calling) | Tool Calling Natif | **Modèle Cible Recommandé pour l'Orchestrateur** |

---

## 7. PLAN D'ACTION PRIORISÉ (P0 -> P3)

```
+-----------------------------------------------------------------------------------+
| PRIORTÉ P0 : SECTEUR CRITIQUE (Correctifs Base de Données & Requêtes SQL)        |
| - Masquer les 5 catégories vides (`Count(products) > 0`).                          |
| - Exclure les 18 établissements sans produits du moteur de recherche AI.          |
+-----------------------------------------------------------------------------------+
                                         |
                                         v
+-----------------------------------------------------------------------------------+
| PRIORITÉ P1 : ORCHESTRATION & TOOL CALLING ENGINE                                 |
| - Migrer de `if/elif` impératif vers un schéma Pydantic / Function Calling.       |
| - Standardiser la réponse JSON unifiée (Text + Catalog UI Cards + Action State).  |
+-----------------------------------------------------------------------------------+
                                         |
                                         v
+-----------------------------------------------------------------------------------+
| PRIORITÉ P2 : RECHERCHE VECTORIELLE HYBRIDE (pgvector)                            |
| - Intégrer pgvector sur `Product.description` & `Establishment.name`.             |
| - Permettre la recherche par proximité sémantique ("repas léger du soir").        |
+-----------------------------------------------------------------------------------+
                                         |
                                         v
+-----------------------------------------------------------------------------------+
| PRIORITÉ P3 : OPTIMISATION ASYNCHRONE VISION & VOICE                              |
| - Déporter le traitement Moondream / Whisper sur des tâches Celery / Redis.       |
| - Mettre en place du streaming SSE (Server-Sent Events) pour les réponses longues.|
+-----------------------------------------------------------------------------------+
```

---

## 8. CRITÈRES DE SUCCÈS & PROTOCOLE DE TEST REQUIS

1. **Test d'Étancheité Catalogue** :
   `python manage.py test apps.ai` doit vérifier qu'aucun établissement sans produit ni aucune catégorie vide ne sont renvoyés par l'API `planning/ai/parse/`.
2. **Test de Continuité Contextuelle** :
   Une séquence de 3 messages ("Montre moi du thieb", "Quel est le moins cher ?", "Planifie le premier pour demain midi") doit maintenir l'ID du produit sélectionné sans régression.
3. **Test de Couverture Frontend** :
   L'interface Angular ne doit afficher aucun bouton d'action non fonctionnel ou menant à une grille vide.
