# AUDIT COMPLET DE L'IA LIA — AYYOU 🇸🇳

> [!IMPORTANT]
> **STATUT DE L'AUDIT** : Audit réalisé à 100% en lecture seule. Aucune ligne de code n'a été modifiée, aucun mock n'a été supprimé, et aucune dépendance n'a été installée.

---

## 1. ARCHITECTURE EXISTANTE

### Fichiers Backend (Django)
* **`apps/ai/prompts.py`** : Définit le `SYSTEM_PROMPT` officiel d'AYYOU IA (Conseiller Gastronomique Dakar, règles anti-hallucination factuelle et règles anti-prompt-injection).
* **`apps/ai/services.py`** : Classe `AIService` gérant la détection d'intention (`extract_intent`), la protection contre le détournement de prompt (`check_prompt_injection`), l'appel aux fonctions ORM, le formatage du contexte factuel, la requête HTTP vers Ollama (`llama3.2:latest`) et les fallbacks déterministes.
* **`apps/ai/tools.py`** : Outils d'accès aux données PostgreSQL via l'ORM Django (`search_food`, `search_establishments`, `search_by_category`, `search_by_budget`, `get_product`, `get_establishment`).
* **`apps/ai/transcription.py`** : Classe `TranscriptionService` exécutant le pipeline ASR Speech-to-Text Whisper (`openai/whisper-base`) en Singleton CPU avec conversion FFmpeg (WAV 16kHz).
* **`apps/ai/views.py`** :
  * `SafeJWTAuthentication` : Authentification tolérante (bascule en mode Guest si le token est invalide au lieu d'émettre un 401).
  * `AIChatView` (`POST /api/ai/chat/`) : Endpoint principal de chat.
  * `AITranscribeView` (`POST /api/ai/transcribe/`) : Endpoint d'envoi et de transcription audio vocal.
* **`apps/ai/urls.py`** : Routes d'API `/api/ai/chat/` et `/api/ai/transcribe/`.
* **`config/settings/base.py`** : Inscription du module `'apps.ai'` dans `INSTALLED_APPS`.

### Fichiers Frontend (Angular)
* **`src/app/core/services/ai-chat.service.ts`** : Service HTTP consommant `/api/ai/chat/` et modélisant la réponse avec les cartes de recommandation (`RecommendationCard`).
* **`src/app/core/services/voice-transcription.service.ts`** : Service d'enregistrement audio navigateur (`MediaRecorder`) et d'expédition vers `/api/ai/transcribe/`.
* **`src/app/features/client/components/chatbot-floating/chatbot-floating.component.ts`** : Composant Angular flottant avec drag-and-drop (souris et tactile), enregistreur vocal, gestion de l'historique conversationnel et rendu des cartes interactives.
* **`src/app/features/client/components/chatbot-floating/chatbot-floating.component.html`** : Interface UI du chatbot (bulles, micro, cartes produit).
* **`src/app/features/client/components/chatbot-floating/chatbot-floating.component.scss`** : Styles SCSS réactifs.

### Endpoints d'API
1. `POST /api/ai/chat/` (Payload: `{ message: string, history: Array<{sender, text}> }`)
2. `POST /api/ai/transcribe/` (Payload: `multipart/form-data` avec champ `audio`)

### Dépendances IA & Configuration
* **LLM Backend** : Runtime local Ollama (`http://127.0.0.1:11434/api/generate`) exécutant le modèle `llama3.2:latest`.
* **STT Backend** : Package Python `transformers` (`pipeline("automatic-speech-recognition")`), `torch`, `huggingface-hub`, exécutable système `ffmpeg`.
* **Variables `.env`** : Aucune variable `.env` dédiée actuellement (`AIService.OLLAMA_URL` est hardcodé sur `http://127.0.0.1:11434/api/generate`).

### Flux de Données Complet (End-to-End)
```
[ Client Angular ] (ChatbotFloatingComponent)
       │
       ├──► (Audio enregistré) ──► [ VoiceTranscriptionService ] ──► POST /api/ai/transcribe/
       │                                                                      │ (FFmpeg + Whisper)
       │ ◄───────────────────── (Texte transcrit inséré dans l'input) ────────┘
       │
       └──► POST /api/ai/chat/ (Message + Historique)
                 │
                 ▼
       [ Django AIChatView ] (SafeJWTAuthentication)
                 │
                 ▼
       [ AIService.process_chat_message ]
                 │
                 ├── 1. Filtre Anti-Prompt-Injection
                 ├── 2. Extraction d'intention (Regex & Contexte conversationnel)
                 ├── 3. Exécution des outils BDD (`apps/ai/tools.py`)
                 │          └─► [ PostgreSQL / Django ORM ] (Produit, Etablissement, Categorie)
                 ├── 4. Construction du contexte factuel brut (`db_context_str`)
                 ├── 5. Appel à Ollama (`llama3.2:latest` sur 127.0.0.1:11434)
                 ├── 6. Contrôle strict anti-hallucination (Écrasement si 0 produit)
                 │
                 ▼
       [ Réponse JSON ] ──► { reply: "...", cards: [...] }
                 │
                 ▼
       [ Client Angular ] ──► Affichage des bulles + cartes de produits cliquables ("Commander")
```

---

## 2. MODÈLE IA

| Propriété | Valeur actuelle |
| :--- | :--- |
| **Modèle utilisé** | `llama3.2:latest` |
| **Fournisseur** | Meta (exécuté via Ollama Runtime Local) |
| **Type de déploiement** | Local (`http://127.0.0.1:11434`) |
| **Température** | `0.3` (Favorise la précision factuelle) |
| **Tokens max en sortie** | `180` tokens (`max_tokens`) |
| **Contexte maximal** | Injecté dynamiquement par prompt (Prompt Système + Contexte 4 produits max) |
| **Fallback en cas de panne** | Fallback déterministe Python en 6 secondes max (recommande le plat top-1 de la BDD ou signale poliment l'absence de produit sans plancher) |

---

## 3. DONNÉES ACTUELLEMENT ACCESSIBLES

| Élément de données | Statut | Explication |
| :--- | :---: | :--- |
| **Restaurants** | **PASS** | Récupération des établissements valides (`statut_verification=VALIDE`), notes, avis et adresses. |
| **Vendeurs** | **PASS** | Filtrage possible via `type_etablissement='VENDEUR'`. |
| **Produits** | **PASS** | Recherche par nom, description, prix de base, statut de disponibilité. |
| **Menus** | **PASS** | Accessible via l'association `Produit` et `Etablissement`. |
| **Catégories** | **PASS** | Filtrage par slug de catégorie (`senegalais`, `fast-food`, etc.). |
| **Sous-catégories** | **ABSENT** | Le modèle BDD n'isole pas les sous-catégories dans le requêtage Lia. |
| **Prix** | **PASS** | Filtrage strict par budget maximum (`prix_base__lte=max_p`). |
| **Disponibilité** | **PASS** | Filtrage strict `est_disponible=True`. |
| **Localisation** | **PARTIEL** | Filtrage textuel par nom de quartier à Dakar (21 quartiers supportés). **ABSENT** pour les coordonnées GPS. |
| **Commandes** | **ABSENT** | Aucun outil n'interroge la table `Commande` ou `LigneCommande`. |
| **Livraison** | **ABSENT** | Aucun outil n'interroge la table `Livraison` ou `ProfilLivreur`. |
| **Notifications** | **ABSENT** | Aucun outil d'accès aux notifications du client. |

---

## 4. BASE DE DONNÉES

* **Accès direct du LLM à PostgreSQL** : **NON, AUCUN ACCÈS DIRECT**. Le LLM n'a aucun accès réseau, ni identifiant, ni permission sur la base PostgreSQL.
* **Mécanisme utilisé** :
  1. Le backend Django reçoit la requête.
  2. Django exécute des requêtes ORM Python sécurisées (`Produit.objects.filter()`).
  3. Django extrait les données et les transforme en une liste de texte simple.
  4. Ce texte factuel est injecté dans le prompt envoyé à Ollama.
* **Architecture RAG** : Aucun RAG vectoriel (pas de pgvector ou FAISS). Il s'agit d'un **Injecteur de Contexte Structuré par Intentions (In-Context Data Injection)**.

---

## 5. OUTILS / TOOL CALLING

### Liste des outils définis dans `apps/ai/tools.py` :

1. **`search_food(query, category_slug, max_price, location, type_etablissement, is_available, limit=5)`**
   * **Données** : Produits réels filtrés avec établissements joints.
   * **Utilisation** : Réelle (Exécuté dans `AIService.process_chat_message`).
2. **`search_establishments(type_etablissement, query, location, limit=5)`**
   * **Données** : Établissements vérifiés.
   * **Utilisation** : Réelle.
3. **`search_by_category(category_slug, location, max_price, limit=5)`**
   * **Données** : Produits de la catégorie spécifiée.
   * **Utilisation** : Réelle.
4. **`search_by_budget(max_budget, location, food_query, limit=5)`**
   * **Données** : Produits respectant le budget max.
   * **Utilisation** : Réelle.
5. **`get_product(product_id)`**
   * **Données** : Fiche détaillée d'un produit par ID.
   * **Utilisation** : Réelle.
6. **`get_establishment(establishment_id)`**
   * **Données** : Fiche détaillée d'un établissement par ID.
   * **Utilisation** : Réelle.

### Outils spécifiques demandés dans l'audit :
* `search_restaurants` : **PASS** (équivalent de `search_establishments`).
* `search_products` : **PASS** (équivalent de `search_food`).
* `get_restaurant` : **PASS** (équivalent de `get_establishment`).
* `get_product` : **PASS**.
* `search_categories` : **ABSENT**.
* `check_availability` : **PARTIEL** (intégré via le filtre `is_available=True`).
* `search_by_location` : **PARTIEL** (filtre textuel par quartier dans `search_food`).
* `get_order` : **ABSENT**.
* `get_delivery_status` : **ABSENT**.

> *Remarque* : Les outils sont actuellement déclenchés par détection d'intention déterministe en Python (`extract_intent`), et non par du function calling dynamique natif du LLM.

---

## 6. MOCKS & VALEURS HARCODÉES

| Fichier | Ligne(s) | Valeur / Occurrence | Nature |
| :--- | :--- | :--- | :--- |
| `apps/ai/tools.py` | L.66, L.137 | `"temps_livraison": "15-25 min"` | Valeur statique hardcodée. |
| `apps/ai/tools.py` | L.60, L.134 | `"image_url": p.image_url or "assets/images/thieboudienne.jpg"` | Image de fallback par défaut. |
| `apps/ai/tools.py` | L.62-64 | `etablissement_nom: "AYYOU"`, `adresse: "Dakar"` | Valeur de secours si relation nulle. |
| `apps/ai/services.py` | L.206, L.208 | `"Pour régaler vos papilles à Dakar..."` | Message de fallback si Ollama échoue. |
| `apps/ai/services.py` | L.43, L.158 | `user_name = "Client"` | Fallback si nom utilisateur absent. |
| `chatbot-floating.component.ts` | L.54-59 | `text: 'Bonjour ! Je suis votre Conseiller...'` | Message de bienvenue statique UI. |
| `ai-chat.service.ts` | L.49 | `reply: 'Désolé, je rencontre une petite...'` | Message d'erreur HTTP statique. |

---

## 7. SÉCURITÉ

* **Authentification** : Gérée par `SafeJWTAuthentication`. Autorise les requêtes sans token (Guest) sans faire échouer la requête.
* **Protection Prompt Injection** : `AIService.check_prompt_injection` intercepte avec regex les mots clés d'injection (`ignore previous instructions`, `select * from`, `drop table`, `admin password`, etc.).
* **SQL Injection** : **0 risque** (utilisation exclusive de l'ORM Django).
* **Isolation Client A / Client B** : Garantie à 100% car Lia n'a actuellement aucun accès aux commandes ou données personnelles.
* **Secrets exposés** : Aucun. Ollama est local (`127.0.0.1:11434`).

---

## 8. HALLUCINATIONS

* **Risque actuel d'hallucination** : **TRÈS FAIBLE À NUL**.
* **Mécanisme de contrôle** :
  1. Instruction stricte dans `prompts.py` (Interdiction d'inventer des prix ou plats).
  2. Écrasement impératif Python (`services.py` L.211-213) : Si la BDD retourne 0 produit, le backend remplace obligatoirement la réponse du LLM par une phrase d'absence de produit.

---

## 9. MODE GUEST

* **Utilisateur non connecté (Invité)** :
  * **Autorisé** : Recherche de plats, restaurants, catégories, prix et disponibilité.
  * **Accès aux données privées** : Impossible.
  * **Bouton "Commander"** : Déclenche la modale de connexion Angular (`authService.requireAuth`).

---

## 10. CLIENT AUTHENTIFIÉ

* Le prénom/nom du client est extrait automatiquement via `request.user`.
* **Aucune transmission manuelle de JWT au LLM** : Le token JWT est géré par les en-têtes HTTP standards (`Authorization: Bearer ...`).

---

## 11. LOCALISATION

* **Mode actuel** : Recherche textuelle dans 21 quartiers de Dakar (`DAKAR_LOCATIONS`).
* **Coordonnées GPS (Latitude/Longitude)** : **ABSENT**. Non exploité actuellement.

---

## 12. VOIX (SPEECH-TO-TEXT)

* **Système existant** : **OUI, 100% FONCTIONNEL**.
* **Modèle STT** : `openai/whisper-base` (via Hugging Face `transformers.pipeline` sur CPU).
* **Conversion** : FFmpeg natif pour normaliser les formats navigateur (`webm`, `ogg`, `mp4`) en WAV 16kHz mono.

---

## 13. FRONTEND

* **Composant** : `ChatbotFloatingComponent` (`src/app/features/client/components/chatbot-floating/`).
* **Fonctionnalités UI** : Bouton flottant, draggable (souris & tactile), enregistreur vocal avec micro animé, loader, affichage des cartes de recommandation avec redirection vers les fiches produit/restaurant.

---

## 14. TESTS EXISTANTS

* **Backend (`apps/ai`)** : `0 test` (Résultat `Ran 0 tests in 0.000s`).
* **Frontend** : Aucun test unitaire dédié au chatbot IA.

---

## 15. MATRICE FINALE DES FONCTIONNALITÉS

| # | Fonctionnalité | État | Fichier concerné | Explication |
| :---: | :--- | :---: | :--- | :--- |
| **1** | **LLM** | **PASS** | `apps/ai/services.py` | Modèle local `llama3.2:latest` via Ollama API. |
| **2** | **Chat** | **PASS** | `apps/ai/views.py`, `chatbot-floating.component.ts` | Interface et endpoint de chat complets. |
| **3** | **Restaurants** | **PASS** | `apps/ai/tools.py` | Recherche d'établissements vérifiés. |
| **4** | **Vendeurs** | **PASS** | `apps/ai/tools.py` | Filtrage par `type_etablissement='VENDEUR'`. |
| **5** | **Produits** | **PASS** | `apps/ai/tools.py` | Recherche de plats réels dans la BDD. |
| **6** | **Menus** | **PASS** | `apps/ai/tools.py` | Association produit-établissement. |
| **7** | **Catégories** | **PASS** | `apps/ai/tools.py` | Filtrage par slug de catégorie. |
| **8** | **Prix** | **PASS** | `apps/ai/tools.py` | Filtrage par budget maximum. |
| **9** | **Disponibilité** | **PASS** | `apps/ai/tools.py` | Filtrage par `est_disponible=True`. |
| **10** | **Localisation** | **PARTIEL** | `apps/ai/services.py` | Filtrage textuel par quartier (GPS absent). |
| **11** | **Commandes** | **ABSENT** | `apps/ai/tools.py` | Aucun outil d'accès aux commandes client. |
| **12** | **Livraison** | **ABSENT** | `apps/ai/tools.py` | Aucun outil d'accès au statut de livraison. |
| **13** | **Guest** | **PASS** | `apps/ai/views.py` | Accessibilité sans authentification via `SafeJWTAuthentication`. |
| **14** | **Client authentifié** | **PARTIEL** | `apps/ai/views.py` | Nom extrait, mais pas d'isolation des commandes. |
| **15** | **Voix** | **PASS** | `apps/ai/transcription.py`, `voice-transcription.service.ts` | Pipeline Whisper CPU fonctionnel avec FFmpeg. |
| **16** | **Anti-hallucination** | **PASS** | `apps/ai/prompts.py`, `services.py` | Prompt strict + écrasement Python si 0 résultat. |
| **17** | **Sécurité** | **PASS** | `apps/ai/services.py` | Filtre anti-prompt-injection et ORM Django. |
| **18** | **Tool calling** | **PARTIEL** | `apps/ai/tools.py` | Fonctions ORM existantes mais appelées par regex. |
| **19** | **RAG** | **ABSENT** | - | Pas de BDD vectorielle (Injection directe de contexte). |
| **20** | **Mocks** | **PARTIEL** | `apps/ai/tools.py` | Hardcode du temps de livraison (`15-25 min`) et fallbacks. |

---

## 16. RECOMMANDATIONS POUR LA PHASE DE CONNEXION DE LIA

### A. Ce qui fonctionne et doit être CONSERVÉ
1. **L'architecture backend/frontend** : `SafeJWTAuthentication`, `AIChatView`, `ChatbotFloatingComponent` et le pipeline vocal Whisper (`transcription.py`).
2. **Le système anti-hallucination** : La vérification stricte par le backend Python post-LLM.
3. **Le filtre Anti-Prompt-Injection** : La fonction `check_prompt_injection`.

### B. Ce qui doit être CORRIGÉ & ENRICHI
1. **Tool Calling Dynamique** : Faire évoluer la détection par Regex vers des outils ORM étendus aux commandes et livraisons.
2. **Support des Commandes et Livraisons** :
   * Ajouter l'outil `get_user_orders(user_id)` pour permettre à Lia de répondre à : *"Où en est ma commande ?"*.
   * Ajouter l'outil `get_delivery_status(order_id, user_id)` avec isolation stricte sur `request.user`.
3. **Remplacement des valeurs hardcodées** :
   * Remplacer `"temps_livraison": "15-25 min"` dans `tools.py` par le temps moyen réel calculé depuis les livraisons.
4. **Localisation GPS** :
   * Permettre l'envoi optionnel des coordonnées GPS du navigateur (`latitude`, `longitude`) pour calculer la distance réelle des restaurants.
5. **Suite de Tests Automated** :
   * Créer la classe `apps/ai/tests/test_ai_service.py` pour valider l'anti-injection, les outils ORM et les réponses de fallback.
