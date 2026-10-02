import os
import sys
import json

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()

from rest_framework.test import APIClient
from apps.telemetry.models import VideoEventLog
from apps.users.models import Utilisateur

# 1. Reset VideoEventLog for clean Phase 3.5 observation
VideoEventLog.objects.all().delete()
print("Base VideoEventLog réinitialisée (0 événements).")

# 2. Retrieve test user (Modou Diop)
user = Utilisateur.objects.get(id=185)

client_anon = APIClient()
client_auth = APIClient()
client_auth.force_authenticate(user=user)

API_URL = "/api/telemetry/video-event/"

def send_event(client, payload):
    response = client.post(API_URL, payload, format='json')
    assert response.status_code == 201, f"Erreur API: {response.status_code} - {response.data}"
    return response.data

print("\n--- EXÉCUTION DES SCÉNARIOS CLIENTS REÉLS ---")

# SCÉNARIO A : Feed browsing & pause/resume (Visiteur Anonyme)
sA_events = [
    {'publication_id': 38, 'session_id': 'feed_session_anon_secA_101', 'event_type': 'IMPRESSION', 'watch_time_seconds': 0.0, 'video_duration_seconds': 15.0, 'progress_percent': 0.0, 'feed_position': 0},
    {'publication_id': 38, 'session_id': 'feed_session_anon_secA_101', 'event_type': 'PLAY', 'watch_time_seconds': 0.0, 'video_duration_seconds': 15.0, 'progress_percent': 0.0, 'feed_position': 0},
    {'publication_id': 38, 'session_id': 'feed_session_anon_secA_101', 'event_type': 'WATCH', 'watch_time_seconds': 4.5, 'video_duration_seconds': 15.0, 'progress_percent': 30.0, 'feed_position': 0},
    {'publication_id': 38, 'session_id': 'feed_session_anon_secA_101', 'event_type': 'PAUSE', 'watch_time_seconds': 4.5, 'video_duration_seconds': 15.0, 'progress_percent': 30.0, 'feed_position': 0},
    {'publication_id': 39, 'session_id': 'feed_session_anon_secA_101', 'event_type': 'IMPRESSION', 'watch_time_seconds': 0.0, 'video_duration_seconds': 20.0, 'progress_percent': 0.0, 'feed_position': 1},
    {'publication_id': 39, 'session_id': 'feed_session_anon_secA_101', 'event_type': 'PLAY', 'watch_time_seconds': 0.0, 'video_duration_seconds': 20.0, 'progress_percent': 0.0, 'feed_position': 1},
    {'publication_id': 39, 'session_id': 'feed_session_anon_secA_101', 'event_type': 'WATCH', 'watch_time_seconds': 7.2, 'video_duration_seconds': 20.0, 'progress_percent': 36.0, 'feed_position': 1},
    {'publication_id': 39, 'session_id': 'feed_session_anon_secA_101', 'event_type': 'PAUSE', 'watch_time_seconds': 7.2, 'video_duration_seconds': 20.0, 'progress_percent': 36.0, 'feed_position': 1},
    {'publication_id': 39, 'session_id': 'feed_session_anon_secA_101', 'event_type': 'PLAY', 'watch_time_seconds': 7.2, 'video_duration_seconds': 20.0, 'progress_percent': 36.0, 'feed_position': 1},
    {'publication_id': 40, 'session_id': 'feed_session_anon_secA_101', 'event_type': 'IMPRESSION', 'watch_time_seconds': 0.0, 'video_duration_seconds': 18.0, 'progress_percent': 0.0, 'feed_position': 2},
]
for ev in sA_events:
    send_event(client_anon, ev)
print("Scénario A exécuté (10 événements enregistrés).")

# SCÉNARIO B : Clic Plat (DISH_CLICK) - Utilisateur Authentifié (User 185)
sB_events = [
    {'publication_id': 41, 'session_id': 'feed_session_auth_secB_202', 'event_type': 'IMPRESSION', 'watch_time_seconds': 0.0, 'video_duration_seconds': 18.0, 'progress_percent': 0.0, 'feed_position': 0},
    {'publication_id': 41, 'session_id': 'feed_session_auth_secB_202', 'event_type': 'PLAY', 'watch_time_seconds': 0.0, 'video_duration_seconds': 18.0, 'progress_percent': 0.0, 'feed_position': 0},
    {'publication_id': 41, 'session_id': 'feed_session_auth_secB_202', 'event_type': 'WATCH', 'watch_time_seconds': 6.0, 'video_duration_seconds': 18.0, 'progress_percent': 33.3, 'feed_position': 0},
    {'publication_id': 41, 'session_id': 'feed_session_auth_secB_202', 'event_type': 'DISH_CLICK', 'watch_time_seconds': 6.0, 'video_duration_seconds': 18.0, 'progress_percent': 33.3, 'feed_position': 0, 'metadata': {'dish_id': '65', 'source': 'video_overlay'}},
]
for ev in sB_events:
    send_event(client_auth, ev)
print("Scénario B exécuté (4 événements enregistrés avec user_id=185).")

# SCÉNARIO C : Ajout Panier (CART_ADD) & Like - Utilisateur Authentifié (User 185)
sC_events = [
    {'publication_id': 42, 'session_id': 'feed_session_auth_secC_303', 'event_type': 'IMPRESSION', 'watch_time_seconds': 0.0, 'video_duration_seconds': 25.0, 'progress_percent': 0.0, 'feed_position': 0},
    {'publication_id': 42, 'session_id': 'feed_session_auth_secC_303', 'event_type': 'PLAY', 'watch_time_seconds': 0.0, 'video_duration_seconds': 25.0, 'progress_percent': 0.0, 'feed_position': 0},
    {'publication_id': 42, 'session_id': 'feed_session_auth_secC_303', 'event_type': 'WATCH', 'watch_time_seconds': 10.0, 'video_duration_seconds': 25.0, 'progress_percent': 40.0, 'feed_position': 0},
    {'publication_id': 42, 'session_id': 'feed_session_auth_secC_303', 'event_type': 'CART_ADD', 'watch_time_seconds': 10.0, 'video_duration_seconds': 25.0, 'progress_percent': 40.0, 'feed_position': 0, 'metadata': {'dish_id': '77', 'quantity': 1}},
    {'publication_id': 42, 'session_id': 'feed_session_auth_secC_303', 'event_type': 'LIKE', 'watch_time_seconds': 10.0, 'video_duration_seconds': 25.0, 'progress_percent': 40.0, 'feed_position': 0},
]
for ev in sC_events:
    send_event(client_auth, ev)
print("Scénario C exécuté (5 événements enregistrés avec user_id=185).")

# SCÉNARIO D : Complétion (COMPLETED) & Share - Anonyme
sD_events = [
    {'publication_id': 43, 'session_id': 'feed_session_anon_secD_404', 'event_type': 'IMPRESSION', 'watch_time_seconds': 0.0, 'video_duration_seconds': 15.0, 'progress_percent': 0.0, 'feed_position': 0},
    {'publication_id': 43, 'session_id': 'feed_session_anon_secD_404', 'event_type': 'PLAY', 'watch_time_seconds': 0.0, 'video_duration_seconds': 15.0, 'progress_percent': 0.0, 'feed_position': 0},
    {'publication_id': 43, 'session_id': 'feed_session_anon_secD_404', 'event_type': 'WATCH', 'watch_time_seconds': 15.0, 'video_duration_seconds': 15.0, 'progress_percent': 100.0, 'feed_position': 0},
    {'publication_id': 43, 'session_id': 'feed_session_anon_secD_404', 'event_type': 'COMPLETED', 'watch_time_seconds': 15.0, 'video_duration_seconds': 15.0, 'progress_percent': 100.0, 'feed_position': 0},
    {'publication_id': 43, 'session_id': 'feed_session_anon_secD_404', 'event_type': 'SHARE', 'watch_time_seconds': 15.0, 'video_duration_seconds': 15.0, 'progress_percent': 100.0, 'feed_position': 0},
]
for ev in sD_events:
    send_event(client_anon, ev)
print("Scénario D exécuté (5 événements enregistrés).")

# SCÉNARIO E : Fast Skip (<3s) - Anonyme
sE_events = [
    {'publication_id': 44, 'session_id': 'feed_session_anon_secE_505', 'event_type': 'IMPRESSION', 'watch_time_seconds': 0.0, 'video_duration_seconds': 30.0, 'progress_percent': 0.0, 'feed_position': 0},
    {'publication_id': 44, 'session_id': 'feed_session_anon_secE_505', 'event_type': 'PLAY', 'watch_time_seconds': 0.0, 'video_duration_seconds': 30.0, 'progress_percent': 0.0, 'feed_position': 0},
    {'publication_id': 44, 'session_id': 'feed_session_anon_secE_505', 'event_type': 'WATCH', 'watch_time_seconds': 1.5, 'video_duration_seconds': 30.0, 'progress_percent': 5.0, 'feed_position': 0},
    {'publication_id': 44, 'session_id': 'feed_session_anon_secE_505', 'event_type': 'SKIP', 'watch_time_seconds': 1.5, 'video_duration_seconds': 30.0, 'progress_percent': 5.0, 'feed_position': 0},
    {'publication_id': 45, 'session_id': 'feed_session_anon_secE_505', 'event_type': 'IMPRESSION', 'watch_time_seconds': 0.0, 'video_duration_seconds': 22.0, 'progress_percent': 0.0, 'feed_position': 1},
    {'publication_id': 45, 'session_id': 'feed_session_anon_secE_505', 'event_type': 'PLAY', 'watch_time_seconds': 0.0, 'video_duration_seconds': 22.0, 'progress_percent': 0.0, 'feed_position': 1},
    {'publication_id': 45, 'session_id': 'feed_session_anon_secE_505', 'event_type': 'WATCH', 'watch_time_seconds': 2.0, 'video_duration_seconds': 22.0, 'progress_percent': 9.1, 'feed_position': 1},
    {'publication_id': 45, 'session_id': 'feed_session_anon_secE_505', 'event_type': 'SKIP', 'watch_time_seconds': 2.0, 'video_duration_seconds': 22.0, 'progress_percent': 9.1, 'feed_position': 1},
]
for ev in sE_events:
    send_event(client_anon, ev)
print("Scénario E exécuté (8 événements enregistrés).")

print(f"\nSUCCESS: {VideoEventLog.objects.count()} événements réellement créés en BDD.")
