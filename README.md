# 🚀 AYYOU BACKEND (Django REST Framework / PostgreSQL)

Backend REST API pour la plateforme de commande et livraison de repas et produits **AYYOU**.
Service d'Authentification & Gestion des Identités.

---

## 📋 PRÉREQUIS

- **Python** : `3.12+`
- **PostgreSQL** : `15+` (ou SQLite en fallback de développement local)
- **Système d'Exploitation** : Windows (ou Linux/macOS)
- **Docker & Docker Compose** (Optionnel pour lancement containerisé)

---

## 🐳 LANCEMENT RAPIDE AVEC DOCKER & DOCKER COMPOSE

Pour lancer l'intégralité de la suite AYYOU (Frontend Angular 19 PWA + Backend Django 5 + PostgreSQL 16) en une seule commande :

```bash
# 1. Copier le fichier de configuration
copy .env.example .env

# 2. Construire et lancer tous les conteneurs
docker compose build
docker compose up -d
```

- **Frontend Angular 19 PWA** : [http://localhost](http://localhost)
- **Backend Django API** : [http://localhost:8000/api/](http://localhost:8000/api/)
- **Documentation Docker** : Référez-vous à [docs/dockerisation.md](docs/dockerisation.md).

---

## ⚙️ INSTALLATION & CONFIGURATION LOCAL (WINDOWS)

### 1. Création de l'Environnement Virtuel
```powershell
python -m venv .venv
```

### 2. Activation de l'Environnement Virtuel
- **PowerShell (Windows)** :
  ```powershell
  .\.venv\Scripts\Activate.ps1
  ```
- **Command Prompt (cmd.exe)** :
  ```cmd
  .\.venv\Scripts\activate.bat
  ```

### 3. Installation des Dépendances
```powershell
pip install -r requirements.txt
```

### 4. Configuration des Variables d'Environnement (`.env`)
Copiez le fichier exemple `.env.example` vers `.env` et adaptez les paramètres :
```powershell
Copy-Item .env.example .env
```

Contenu type de `.env` :
```env
SECRET_KEY=django-insecure-ayyou-dev-secret-key-change-in-production-2025
DEBUG=True
ALLOWED_HOSTS=127.0.0.1,localhost

DB_ENGINE=django.db.backends.postgresql
DB_NAME=ayyou_db
DB_USER=postgres
DB_PASSWORD=postgres
DB_HOST=127.0.0.1
DB_PORT=5432

# Option de repli pour dev local sans PostgreSQL sur port 5432
USE_SQLITE_DEV=True

# OTP & Authentification
OTP_EXPIRATION_MINUTES=10
OTP_MAX_ATTEMPTS=3
DEFAULT_COUNTRY_CODE=SN

CORS_ALLOWED_ORIGINS=http://localhost:4200,http://127.0.0.1:4200
```

---

## 🗄️ BASE DE DONNÉES & MIGRATIONS

Exécuter les migrations initiales :
```powershell
python manage.py migrate
```

Lancer les tests unitaires (36 tests) :
```powershell
python manage.py test
```

---

## 🚀 API D'INSCRIPTION CLIENT (`POST /api/auth/register/`)

### 1. En-têtes HTTP
- `Content-Type`: `application/json`

### 2. Payload de Requête (Body JSON)
```json
{
  "prenom": "Moussa",
  "nom": "Diop",
  "email": "moussa.diop@ayyou.sn",
  "numero_telephone": "+221771234567",
  "password": "SuperPassword@2025",
  "password_confirmation": "SuperPassword@2025"
}
```

### 3. Règles de Validation Backend
- `prenom` : Obligatoire, min 2 caractères.
- `nom` : Obligatoire, min 2 caractères.
- `email` : Obligatoire, format email valide, normalisé en minuscules, unicité stricte en base.
- `numero_telephone` : Obligatoire, parsé et validé via la bibliothèque `phonenumbers`, normalisé au format international E.164 (`+221...`), unicité stricte en base.
- `password` : Obligatoire, min 8 caractères, au moins 1 lettre, 1 chiffre et 1 symbole. Hachage sécurisé Django PBKDF2/Argon2.
- `password_confirmation` : Obligatoire, égalité exacte avec `password`.

### 4. Réponse de Succès (`HTTP 201 Created`)
```json
{
  "message": "Inscription réussie. Un code de vérification a été envoyé par SMS.",
  "verification_required": true,
  "verification_type": "VERIFICATION_TELEPHONE"
}
```

### 5. Codes d'Erreur & Réponses
- `HTTP 400 Bad Request` : Erreurs de validation de format ou champs manquants.
- `HTTP 409 Conflict` : Adresse email ou numéro de téléphone déjà enregistré.
- `HTTP 429 Too Many Requests` : Rate limiting sur les demandes d'envoi d'OTP SMS.

---

## 📱 API DE VÉRIFICATION OTP SMS (`POST /api/auth/verify-otp/`)

### 1. En-têtes HTTP
- `Content-Type`: `application/json`

### 2. Payload de Requête (Body JSON)
```json
{
  "numero_telephone": "+221771234567",
  "code": "123456"
}
```

### 3. Règles de Validation Backend & Sécurité
- `numero_telephone` : Obligatoire, normalisé au format E.164 (`+221...`) via `phonenumbers`.
- `code` : Obligatoire, exactement 6 chiffres numériques.
- **Expiration** : OTP valide pendant 10 minutes maximum (rejet si expiré).
- **Nombre de tentatives** : Limité à 3 essais max par code (invalidation automatique après 3 échecs).
- **Activation** : Marque `Utilisateur.est_verifie = True` et `VerificationOTP.est_utilise = True` dans une transaction atomique.
- **Invalidation** : Invalide tous les OTP non utilisés précédents du même type pour l'utilisateur.

### 4. Réponse de Succès (`HTTP 200 OK`)
```json
{
  "message": "Numéro de téléphone vérifié avec succès.",
  "verified": true
}
```

### 5. Codes d'Erreur & Réponses
- `HTTP 400 Bad Request` : Code invalide, expiré, déjà utilisé, ou nombre maximal de tentatives dépassé.

---

## 🔑 API DE CONNEXION CLIENT & JWT (`POST /api/auth/login/`)

### 1. En-têtes HTTP
- `Content-Type`: `application/json`

### 2. Payload de Requête (Body JSON)
```json
{
  "identifier": "moussa.diop@ayyou.sn",
  "password": "SuperPassword@2025"
}
```
*Remarque* : `identifier` accepte une adresse **Email** (minuscules/majuscules) OU un **Numéro de téléphone** (format local `77 123 45 67` ou international E.164 `+221771234567`).

### 3. Règles de Validation & Sécurité
- **Normalisation** : Conversion automatique des emails en minuscules et des numéros de téléphone au format E.164.
- **Mot de passe** : Vérification sécurisée avec `check_password` (PBKDF2/Argon2).
- **Statut Compte Actif** : Rejet si `est_actif = False`.
- **Statut Téléphone Vérifié** : Rejet HTTP 403 Forbidden avec `verification_required: true` si `est_verifie = False`.
- **Dernière connexion** : Mise à jour automatique du champ `Utilisateur.derniere_connexion`.
- **Tokens JWT** : Génération de l'Access Token (durée 24h) et Refresh Token (durée 7j) via SimpleJWT.
- **Anti-Énumération & Protection** : Pas d'exposition de password, hash ou OTP dans les réponses API.

### 4. Réponse de Succès (`HTTP 200 OK`)
```json
{
  "message": "Connexion réussie.",
  "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "utilisateur": {
    "id": 1,
    "prenom": "Moussa",
    "nom": "Diop",
    "email": "moussa.diop@ayyou.sn",
    "numero_telephone": "+221771234567",
    "est_verifie": true
  }
}
```

### 5. Codes d'Erreur & Réponses
- `HTTP 400 Bad Request` : Identifiants invalides (email/téléphone ou mot de passe incorrect), ou compte inactif.
- `HTTP 403 Forbidden` : Compte non vérifié (`verification_required: true`, `verification_type: "VERIFICATION_TELEPHONE"`).

---

## 🍽️ API REST CATALOGUE AYYOU (`/api/catalog/`)

Les API du catalogue permettent aux clients de parcourir les catégories, établissements, plats, publications sociales du Feed, et d'enregistrer leurs coups de cœur (Likes).

### 1. En-têtes HTTP
- `Content-Type`: `application/json`
- `Authorization`: `Bearer <token_jwt>` *(requis uniquement pour les actions de Like)*

---

### 2. Endpoints de Consultation Publique (`AllowAny`)

#### 📁 GET `/api/catalog/categories/`
* **Description** : Retourne la liste des catégories de plats actives (`est_active = true`), ordonnées selon leur rang d'affichage.
* **Réponse de succès (`HTTP 200 OK`)** :
  ```json
  [
    {
      "id": 1,
      "slug": "burgers-teranga",
      "nom": "Burgers Teranga",
      "icone": "burger",
      "image_url": "https://ayyou.sn/images/categories/burger.jpg",
      "est_active": true,
      "ordre": 1
    }
  ]
  ```

#### 🏪 GET `/api/catalog/establishments/`
* **Description** : Liste les Restaurants et Vendeurs à domicile avec pagination (`10 items/page`) et filtres.
* **Paramètres de requête (Query params)** :
  * `type_etablissement` : `RESTAURANT` ou `VENDEUR`
  * `statut` : `open` ou `closed`
  * `specialite` : Recherche par spécialité culinaire
  * `search` / `q` / `nom` : Recherche textuelle par nom d'établissement
* **Réponse de succès (`HTTP 200 OK`)** :
  ```json
  {
    "count": 1,
    "next": null,
    "previous": null,
    "results": [
      {
        "id": 1,
        "nom": "Chez Loutcha Plateau",
        "type_etablissement": "RESTAURANT",
        "proprietaire": 2,
        "proprietaire_nom": "Ibrahima Diallo",
        "logo_url": "https://ayyou.sn/logos/loutcha.png",
        "couverture_url": "https://ayyou.sn/covers/loutcha.jpg",
        "slogan": "Le vrai goût du Sénégal",
        "description": "Restaurant traditionnel au cœur du Plateau",
        "adresse": "Rue Félix Faure, Dakar",
        "latitude": "14.6698000",
        "longitude": "-17.4381000",
        "note_moyenne": "4.80",
        "nombre_avis": 120,
        "statut": "open",
        "heure_fermeture": "23h30",
        "telephone": "+221338210000",
        "specialite": "Cuisine Sénégalaise",
        "nombre_videos": 5,
        "est_verifie": true
      }
    ]
  }
  ```

#### 🏪 GET `/api/catalog/establishments/{id}/`
* **Description** : Détail public d'un Restaurant ou Vendeur par son identifiant ID.
* **Sécurité** : Les informations sensibles du propriétaire (mot de passe, hash, données de connexion) ne sont jamais exposées.

#### 🍕 GET `/api/catalog/products/`
* **Description** : Liste paginée des plats et produits du catalogue AYYOU.
* **Paramètres de requête (Query params)** :
  * `categorie` : Filtre par ID numérique ou slug (ex: `burgers-teranga`)
  * `etablissement` : Filtre par ID de l'établissement
  * `est_disponible` : `true` ou `false`
  * `search` / `q` / `nom` : Recherche par nom ou description
* **Sécurité & Masquage** : Les champs internes vendeur `stock_disponible` et `stock_ayyou_reserve` sont **strictement masqués**.

#### 🍕 GET `/api/catalog/products/{id}/`
* **Description** : Fiche complète d'un produit destinée à l'écran de détail ([product/:id](file:///c:/Users/HP/Desktop/Ayyou-frontend/src/app/features/client/product-detail)).
* **Réponse de succès (`HTTP 200 OK`)** :
  ```json
  {
    "id": 1,
    "nom": "Thiéboudienne Rouge Penda Mbaye",
    "description": "Riz au poisson Tiof avec légumes de saison",
    "prix_base": "4500.00",
    "image_url": "https://ayyou.sn/images/thieb.jpg",
    "images_galerie": [],
    "est_disponible": true,
    "temps_preparation": "20 min",
    "nombre_likes": 12,
    "tags": ["National", "Poisson"],
    "categorie": { "id": 2, "nom": "Plats Nationaux" },
    "etablissement": { "id": 1, "nom": "Chez Loutcha Plateau" },
    "variantes": [
      { "id": 1, "titre": "Grand Format Tiof XL", "surcout_prix": "1500.00", "est_requis": false }
    ],
    "sauces": [
      { "id": 1, "type_option": "SAUCE", "titre": "Sauce Beugueul", "surcout_prix": "0.00", "est_inclus": true }
    ],
    "supplements": [
      { "id": 2, "type_option": "SUPPLEMENT", "titre": "Supplément Xoogn", "surcout_prix": "500.00", "est_inclus": false }
    ]
  }
  ```

#### 🎥 GET `/api/catalog/feed/`
* **Description** : Liste paginée des vidéos et photos du Feed social TikTok-style AYYOU.
* **Champ dynamique `is_liked`** : Si l'utilisateur envoie un token JWT valide, `is_liked` indique s'il a aimé ce post (`true`/`false`).

---

### 3. Endpoints de Gestion des Likes (`IsAuthenticated`)

#### ❤️ POST `/api/catalog/likes/`
* **En-tête** : `Authorization: Bearer <token_jwt>`
* **Body JSON** : Cible un Produit **ou** une Publication Feed.
  ```json
  {
    "produit": 1
  }
  ```
  *ou*
  ```json
  {
    "publication": 2
  }
  ```
* **Réponse de succès (`HTTP 201 Created`)** : Incrémente atomiquement le compteur `nombre_likes`.
* **Erreur (`HTTP 400 Bad Request`)** : Si l'utilisateur a déjà aimé cet élément (doublon rejeté).

#### 💔 DELETE `/api/catalog/likes/` ou `/api/catalog/likes/{id}/`
* **En-tête** : `Authorization: Bearer <token_jwt>`
* **Description** : Retire un Like enregistré. Décrément de `nombre_likes`.
* **Réponse de succès (`HTTP 204 No Content`)**.
* **Erreur (`HTTP 403 Forbidden`)** : Tentative de suppression du Like d'un autre utilisateur.

---

## 📁 STRUCTURE DU PROJET BACKEND

```
AYYOU-BACKEND/
│
├── .venv/                   # Environnement virtuel Python
├── manage.py                # Manager de commandes Django
│
├── config/                  # Configuration du projet Django
│   ├── settings/            # Architecture de configuration modulaire
│   │   ├── base.py          # DRF, CORS, Database, Logging, Security, OTP
│   │   ├── dev.py           # Configuration dev local
│   │   └── prod.py          # En-têtes et sécurité de production
│   ├── urls.py              # Registre d'URLs central (/api/auth/, /api/users/, /api/catalog/)
│   ├── asgi.py              # Entrée ASGI
│   └── wsgi.py              # Entrée WSGI
│
├── apps/                    # Modules applicatifs AYYOU
│   ├── authentication/      # Service d'Authentification (/api/auth/)
│   ├── users/               # Service Utilisateurs & Profils (/api/users/)
│   └── catalog/             # Service Catalogue AYYOU (/api/catalog/)
│       ├── admin.py         # Interface Admin Django pour le catalogue
│       ├── apps.py
│       ├── models.py        # Categorie, Etablissement, Produit, Variante, Option, PublicationFeed, LikeProduit
│       ├── serializers.py   # Serializers et masquage sécurité
│       ├── views.py         # Vues REST Categorie, Etablissement, Produit, Feed, Likes
│       ├── urls.py          # /api/catalog/categories/, establishments/, products/, feed/, likes/
│       └── tests/           # Suite de tests automatisés (50 tests unitaires)
│           ├── test_models.py
│           ├── test_serializers.py
│           └── test_views.py
│
├── requirements.txt         # Dépendances (Django, DRF, CorsHeaders, Psycopg2, Phonenumbers, SimpleJWT)
├── .env                     # Variables d'environnement locales (ignoré par Git)
├── .env.example             # Exemple de configuration d'environnement
├── .gitignore               # Exclusions Git
└── README.md                # Documentation de l'API REST
```
