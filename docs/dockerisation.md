# Guide de Containerisation Docker — Application AYYOU

Ce document détaille l'architecture Docker et la procédure complète pour construire, déployer, exécuter et maintenir l'application AYYOU (Frontend Angular 19 PWA + Backend Django 5.0 + PostgreSQL 16).

---

## 1. Architecture Docker

L'application est découpée en 3 conteneurs principaux connectés via un réseau virtuel interne Docker (`ayyou_network`) :

```
                  INTERNET
                      |
           [ Port 80 ] / [ Port 8000 ]
                      |
        ┌─────────────┴─────────────┐
        |                           |
  ayyou_frontend              ayyou_backend
 (Angular 19 + Nginx)      (Django 5.0 + Gunicorn)
        |                           |
        │ (Reverse Proxy /api)      │
        └───────────────────────────┼──────────────┐
                                    |              |
                              ayyou_postgres   [ Volumes ]
                              (PostgreSQL 16)  - postgres_data
                                               - media_data
                                               - static_data
```

### Services Docker :
1. **`frontend`** (`ayyou_frontend`) : Serveur Nginx exposant l'application Angular 19 PWA sur le port `80`. Nginx assure également le Reverse Proxy vers Django pour les endpoints `/api/` et les fichiers médias `/media/`.
2. **`backend`** (`ayyou_backend`) : Application Django 5.0 servie par le serveur WSGI Gunicorn (3 workers sur le port `8000`). Gère l'exécution des migrations automatiques (`python manage.py migrate`) et la collecte des fichiers statiques (`collectstatic`).
3. **`db`** (`ayyou_postgres`) : Base de données relationnelle PostgreSQL 16 avec healthcheck et persistance complète des données via volume nommé Docker.

---

## 2. Prérequis
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (avec Docker Compose v2.0+)
- Git

---

## 3. Configuration des Variables d'Environnement

Avant le premier lancement, créez le fichier `.env` à la racine de `Ayyou-backend` :

```bash
cp .env.example .env
```

Vérifiez/Adaptez les variables clés dans `.env` :

```env
# Django
SECRET_KEY=django-insecure-ayyou-dev-secret-key-change-in-production-2025
DEBUG=False
ALLOWED_HOSTS=127.0.0.1,localhost,backend,frontend

# PostgreSQL
DB_ENGINE=django.db.backends.postgresql
DB_NAME=ayyou_db
DB_USER=postgres
DB_PASSWORD=postgres
DB_HOST=db
DB_PORT=5432
USE_SQLITE_DEV=False

# Security & CORS
CORS_ALLOWED_ORIGINS=http://localhost:4200,http://127.0.0.1:4200,http://localhost
CSRF_TRUSTED_ORIGINS=http://localhost:4200,http://127.0.0.1:4200,http://localhost
```

---

## 4. Commandes d'Utilisation

### Build et Lancement des Conteneurs
Pour construire les images et démarrer tous les services en tâche de fond :

```bash
docker compose build
docker compose up -d
```

### Vérification du Statut des Services
```bash
docker compose ps
```

### Visualisation des Logs
```bash
# Tous les services
docker compose logs -f

# Log du backend uniquement
docker compose logs -f backend

# Log du frontend uniquement
docker compose logs -f frontend
```

### Arrêt des Services (Sans perte de données)
```bash
docker compose down
```

### Re-construction Sans Cache (Mise à jour du code)
```bash
docker compose build --no-cache
docker compose up -d
```

---

## 5. Accès aux Services

- **Frontend Angular PWA** : `http://localhost/`
- **API Backend Django** : `http://localhost:8000/api/` (ou via Nginx sur `http://localhost/api/`)
- **Django Admin** : `http://localhost:8000/admin/`

---

## 6. Persistance des Données et Fichiers Médias

Les volumes Docker suivants garantissent qu'aucune donnée, image ou vidéo du Feed AYYOU n'est perdue lors du redémarrage ou de la mise à jour des conteneurs :

- **`postgres_data`** : Base de données PostgreSQL (`/var/lib/postgresql/data`).
- **`media_data`** : Stockage des vidéos du Feed, photos de profil, logos des établissements (`/app/media`).
- **`static_data`** : Fichiers statiques générés par `collectstatic` (`/app/staticfiles`).

> ⚠️ **ATTENTION** : N'exécutez jamais `docker compose down -v` en production, car cela supprimerait les volumes de données persistants.

---

## 7. Commandes Utiles de Maintenance

### Exécuter une migration Django manuellement
```bash
docker compose exec backend python manage.py migrate
```

### Créer un Superutilisateur Django Admin
```bash
docker compose exec backend python manage.py createsuperuser
```

### Charger les Données de Test (Restaurants, Plats & Feed)
```bash
docker compose exec backend python manage.py seed_ayyou_database
```
