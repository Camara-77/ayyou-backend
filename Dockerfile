# Image Python officielle basée sur Linux Debian Slim
FROM python:3.12-slim

# Définition du répertoire de travail
WORKDIR /app

# Empêche Python d'écrire des fichiers .pyc et active le mode unbuffered
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Installation des dépendances système nécessaires
RUN apt-get update && apt-get install -y --no-install-recommends \
    netcat-openbsd \
    curl \
    libpq-dev \
    gcc \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copie et installation des dépendances Python
COPY requirements.txt /app/
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copie du code source du backend
COPY . /app/

# Rendre l'entrypoint exécutable
RUN chmod +x /app/entrypoint.sh

# Exposition du port 8000
EXPOSE 8000

# Point d'entrée
ENTRYPOINT ["/app/entrypoint.sh"]
