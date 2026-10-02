#!/bin/sh
set -e

echo "=================================================="
echo "   DEMARRAGE DU BACKEND AYYOU (DOCKER CONTAINER)"
echo "=================================================="

# Attente de PostgreSQL
if [ "$DB_HOST" != "" ]; then
  echo "Attente de la base de données PostgreSQL à $DB_HOST:$DB_PORT..."
  while ! nc -z $DB_HOST $DB_PORT; do
    sleep 1
  done
  echo "=> Base de données PostgreSQL disponible et prête !"
fi

echo "Application des migrations Django..."
python manage.py migrate --noinput

echo "Collecte des fichiers statiques Django (collectstatic)..."
python manage.py collectstatic --noinput --clear || true

echo "Démarrage du serveur WSGI Gunicorn sur 0.0.0.0:8000..."
exec gunicorn config.wsgi:application \
  --bind 0.0.0.0:8000 \
  --workers 3 \
  --timeout 120 \
  --access-logfile - \
  --error-logfile -
