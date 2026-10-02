# Dockerisation AYYOU — Guide Complet Architecture & Opérations

## 1. Architecture Containerisée

L'application AYYOU est entièrement containerisée avec Docker et orchestrée via Docker Compose selon l'architecture microservices suivante :

```text
Navigateur Web (Client / Pro / Livreur / Admin)
                      │
                      ▼
            Frontend (Nginx :80)
        ┌─────────────┴─────────────┐
        │                           │
        ▼                           ▼
Angular 19 SPA (PWA)         /api/ Proxy
  /usr/share/nginx/html      http://backend:8000/api/
        │                           │
        ▼                           ▼
   Fichiers Médias           Backend (Django 5.x)
   /media/ -> Volume            Gunicorn WSGI
                                    │
                                    ▼
                          PostgreSQL 16 (Port 5432)
                          Volume postgres_data
```

---

## 2. Services Docker

| Service | Image / Build | Port Exposé | Volume (Persistance) | Rôle |
|---|---|---|---|---|
| **db** | `postgres:16-alpine` | Interne (5432) | `postgres_data` | Base de données relationnelle PostgreSQL |
| **backend** | Dockerfile Python 3.12-slim | `8000:8000` | `media_data`, `static_data` | Django REST Framework + Gunicorn WSGI |
| **frontend** | Multi-stage Node 20 / Nginx | `80:80` | `media_data`, `static_data` | Serveur Web Nginx + Application Angular 19 SPA / PWA |

---

## 3. Prérequis & Fichier d'Environnement

* Docker Engine v24+ et Docker Compose v2.20+
* Copier `.env.example` vers `.env` :

```bash
cp .env.example .env
```

---

## 4. Commandes Utiles de Gestion

### Démarrage des Services
```bash
docker compose up -d
```

### Construction des Images (sans cache si nécessaire)
```bash
docker compose build --no-cache
```

### Vérification du Statut des Services
```bash
docker compose ps
```

### Consultation des Logs
```bash
docker compose logs -f
```

### Migrations Manuelles
```bash
docker compose exec backend python manage.py migrate
```

### Création du Compte Restaurant de Test
```bash
docker compose exec backend python manage.py setup_test_restaurant
```

### Arrêt de l'Application (Sans perte de données)
```bash
docker compose down
```

---

## 5. Volumes Persistants

* `postgres_data` : Conserve la base de données PostgreSQL (Utilisateurs, Établissements, Plats, Commandes, Abonnements, Événements de Télémétrie).
* `media_data` : Conserve tous les médias chargés (Photos de plats, Avatars, Documents, Vidéos du Feed AYYOU).
* `static_data` : Fichiers statiques Django collectés via `collectstatic`.
