import os
import sys

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()

from rest_framework.test import APIClient
from apps.telemetry.models import VideoEventLog
from apps.users.models import Utilisateur

print(f"Événements existants en BDD avant enrichissement : {VideoEventLog.objects.count()}")

# Chargement d'utilisateurs distincts pour enrichir le profil utilisateur
user_184 = Utilisateur.objects.get(id=184) # Marché des Fruits
user_183 = Utilisateur.objects.get(id=183) # Le Panier Tropical
user_182 = Utilisateur.objects.get(id=182) # Fruits Frais Dakar
user_181 = Utilisateur.objects.get(id=181) # Street Food Awa

client_anon = APIClient()

def get_auth_client(user):
    c = APIClient()
    c.force_authenticate(user=user)
    return c

client_184 = get_auth_client(user_184)
client_183 = get_auth_client(user_183)
client_182 = get_auth_client(user_182)
client_181 = get_auth_client(user_181)

API_URL = "/api/telemetry/video-event/"

def send_event(client, payload):
    response = client.post(API_URL, payload, format='json')
    assert response.status_code == 201, f"Erreur API: {response.status_code} - {response.data}"
    return response.data

print("\n--- ENRICHISSEMENT DES SESSIONS RÉELLES POUR PHASE 4.5 (V2) ---")

# Session 6 : Auth User #184 (feed_session_auth_secF_606)
s6_events = [
    {'publication_id': 38, 'session_id': 'feed_session_auth_secF_606', 'event_type': 'IMPRESSION', 'watch_time_seconds': 0.0, 'video_duration_seconds': 15.0, 'progress_percent': 0.0, 'feed_position': 0},
    {'publication_id': 38, 'session_id': 'feed_session_auth_secF_606', 'event_type': 'PLAY', 'watch_time_seconds': 0.0, 'video_duration_seconds': 15.0, 'progress_percent': 0.0, 'feed_position': 0},
    {'publication_id': 38, 'session_id': 'feed_session_auth_secF_606', 'event_type': 'WATCH', 'watch_time_seconds': 12.0, 'video_duration_seconds': 15.0, 'progress_percent': 80.0, 'feed_position': 0},
    {'publication_id': 38, 'session_id': 'feed_session_auth_secF_606', 'event_type': 'LIKE', 'watch_time_seconds': 12.0, 'video_duration_seconds': 15.0, 'progress_percent': 80.0, 'feed_position': 0},
    {'publication_id': 38, 'session_id': 'feed_session_auth_secF_606', 'event_type': 'CART_ADD', 'watch_time_seconds': 12.0, 'video_duration_seconds': 15.0, 'progress_percent': 80.0, 'feed_position': 0, 'metadata': {'dish_id': '78'}},
    {'publication_id': 39, 'session_id': 'feed_session_auth_secF_606', 'event_type': 'IMPRESSION', 'watch_time_seconds': 0.0, 'video_duration_seconds': 20.0, 'progress_percent': 0.0, 'feed_position': 1},
    {'publication_id': 39, 'session_id': 'feed_session_auth_secF_606', 'event_type': 'PLAY', 'watch_time_seconds': 0.0, 'video_duration_seconds': 20.0, 'progress_percent': 0.0, 'feed_position': 1},
    {'publication_id': 39, 'session_id': 'feed_session_auth_secF_606', 'event_type': 'WATCH', 'watch_time_seconds': 3.0, 'video_duration_seconds': 20.0, 'progress_percent': 15.0, 'feed_position': 1},
    {'publication_id': 39, 'session_id': 'feed_session_auth_secF_606', 'event_type': 'SKIP', 'watch_time_seconds': 3.0, 'video_duration_seconds': 20.0, 'progress_percent': 15.0, 'feed_position': 1},
    {'publication_id': 40, 'session_id': 'feed_session_auth_secF_606', 'event_type': 'IMPRESSION', 'watch_time_seconds': 0.0, 'video_duration_seconds': 18.0, 'progress_percent': 0.0, 'feed_position': 2},
    {'publication_id': 40, 'session_id': 'feed_session_auth_secF_606', 'event_type': 'PLAY', 'watch_time_seconds': 0.0, 'video_duration_seconds': 18.0, 'progress_percent': 0.0, 'feed_position': 2},
    {'publication_id': 40, 'session_id': 'feed_session_auth_secF_606', 'event_type': 'WATCH', 'watch_time_seconds': 18.0, 'video_duration_seconds': 18.0, 'progress_percent': 100.0, 'feed_position': 2},
    {'publication_id': 40, 'session_id': 'feed_session_auth_secF_606', 'event_type': 'COMPLETED', 'watch_time_seconds': 18.0, 'video_duration_seconds': 18.0, 'progress_percent': 100.0, 'feed_position': 2},
    {'publication_id': 40, 'session_id': 'feed_session_auth_secF_606', 'event_type': 'SHARE', 'watch_time_seconds': 18.0, 'video_duration_seconds': 18.0, 'progress_percent': 100.0, 'feed_position': 2},
]
for ev in s6_events:
    send_event(client_184, ev)
print("Session 6 enregistrée (User #184).")

# Session 7 : Auth User #183 (feed_session_auth_secG_707)
s7_events = [
    {'publication_id': 42, 'session_id': 'feed_session_auth_secG_707', 'event_type': 'IMPRESSION', 'watch_time_seconds': 0.0, 'video_duration_seconds': 25.0, 'progress_percent': 0.0, 'feed_position': 0},
    {'publication_id': 42, 'session_id': 'feed_session_auth_secG_707', 'event_type': 'PLAY', 'watch_time_seconds': 0.0, 'video_duration_seconds': 25.0, 'progress_percent': 0.0, 'feed_position': 0},
    {'publication_id': 42, 'session_id': 'feed_session_auth_secG_707', 'event_type': 'WATCH', 'watch_time_seconds': 20.0, 'video_duration_seconds': 25.0, 'progress_percent': 80.0, 'feed_position': 0},
    {'publication_id': 42, 'session_id': 'feed_session_auth_secG_707', 'event_type': 'DISH_CLICK', 'watch_time_seconds': 20.0, 'video_duration_seconds': 25.0, 'progress_percent': 80.0, 'feed_position': 0, 'metadata': {'dish_id': '77'}},
    {'publication_id': 43, 'session_id': 'feed_session_auth_secG_707', 'event_type': 'IMPRESSION', 'watch_time_seconds': 0.0, 'video_duration_seconds': 15.0, 'progress_percent': 0.0, 'feed_position': 1},
    {'publication_id': 43, 'session_id': 'feed_session_auth_secG_707', 'event_type': 'PLAY', 'watch_time_seconds': 0.0, 'video_duration_seconds': 15.0, 'progress_percent': 0.0, 'feed_position': 1},
    {'publication_id': 43, 'session_id': 'feed_session_auth_secG_707', 'event_type': 'WATCH', 'watch_time_seconds': 2.0, 'video_duration_seconds': 15.0, 'progress_percent': 13.3, 'feed_position': 1},
    {'publication_id': 43, 'session_id': 'feed_session_auth_secG_707', 'event_type': 'SKIP', 'watch_time_seconds': 2.0, 'video_duration_seconds': 15.0, 'progress_percent': 13.3, 'feed_position': 1},
    {'publication_id': 44, 'session_id': 'feed_session_auth_secG_707', 'event_type': 'IMPRESSION', 'watch_time_seconds': 0.0, 'video_duration_seconds': 30.0, 'progress_percent': 0.0, 'feed_position': 2},
    {'publication_id': 44, 'session_id': 'feed_session_auth_secG_707', 'event_type': 'PLAY', 'watch_time_seconds': 0.0, 'video_duration_seconds': 30.0, 'progress_percent': 0.0, 'feed_position': 2},
    {'publication_id': 44, 'session_id': 'feed_session_auth_secG_707', 'event_type': 'WATCH', 'watch_time_seconds': 15.0, 'video_duration_seconds': 30.0, 'progress_percent': 50.0, 'feed_position': 2},
    {'publication_id': 44, 'session_id': 'feed_session_auth_secG_707', 'event_type': 'LIKE', 'watch_time_seconds': 15.0, 'video_duration_seconds': 30.0, 'progress_percent': 50.0, 'feed_position': 2},
]
for ev in s7_events:
    send_event(client_183, ev)
print("Session 7 enregistrée (User #183).")

# Session 8 : Auth User #182 (feed_session_auth_secH_808)
s8_events = [
    {'publication_id': 45, 'session_id': 'feed_session_auth_secH_808', 'event_type': 'IMPRESSION', 'watch_time_seconds': 0.0, 'video_duration_seconds': 22.0, 'progress_percent': 0.0, 'feed_position': 0},
    {'publication_id': 45, 'session_id': 'feed_session_auth_secH_808', 'event_type': 'PLAY', 'watch_time_seconds': 0.0, 'video_duration_seconds': 22.0, 'progress_percent': 0.0, 'feed_position': 0},
    {'publication_id': 45, 'session_id': 'feed_session_auth_secH_808', 'event_type': 'WATCH', 'watch_time_seconds': 22.0, 'video_duration_seconds': 22.0, 'progress_percent': 100.0, 'feed_position': 0},
    {'publication_id': 45, 'session_id': 'feed_session_auth_secH_808', 'event_type': 'COMPLETED', 'watch_time_seconds': 22.0, 'video_duration_seconds': 22.0, 'progress_percent': 100.0, 'feed_position': 0},
    {'publication_id': 45, 'session_id': 'feed_session_auth_secH_808', 'event_type': 'CART_ADD', 'watch_time_seconds': 22.0, 'video_duration_seconds': 22.0, 'progress_percent': 100.0, 'feed_position': 0, 'metadata': {'dish_id': '78'}},
    {'publication_id': 38, 'session_id': 'feed_session_auth_secH_808', 'event_type': 'IMPRESSION', 'watch_time_seconds': 0.0, 'video_duration_seconds': 15.0, 'progress_percent': 0.0, 'feed_position': 1},
    {'publication_id': 38, 'session_id': 'feed_session_auth_secH_808', 'event_type': 'PLAY', 'watch_time_seconds': 0.0, 'video_duration_seconds': 15.0, 'progress_percent': 0.0, 'feed_position': 1},
    {'publication_id': 38, 'session_id': 'feed_session_auth_secH_808', 'event_type': 'WATCH', 'watch_time_seconds': 1.0, 'video_duration_seconds': 15.0, 'progress_percent': 6.6, 'feed_position': 1},
    {'publication_id': 38, 'session_id': 'feed_session_auth_secH_808', 'event_type': 'SKIP', 'watch_time_seconds': 1.0, 'video_duration_seconds': 15.0, 'progress_percent': 6.6, 'feed_position': 1},
]
for ev in s8_events:
    send_event(client_182, ev)
print("Session 8 enregistrée (User #182).")

# Session 9 : Anonyme Visiteur D (feed_session_anon_secI_909)
s9_events = [
    {'publication_id': 40, 'session_id': 'feed_session_anon_secI_909', 'event_type': 'IMPRESSION', 'watch_time_seconds': 0.0, 'video_duration_seconds': 18.0, 'progress_percent': 0.0, 'feed_position': 0},
    {'publication_id': 40, 'session_id': 'feed_session_anon_secI_909', 'event_type': 'PLAY', 'watch_time_seconds': 0.0, 'video_duration_seconds': 18.0, 'progress_percent': 0.0, 'feed_position': 0},
    {'publication_id': 40, 'session_id': 'feed_session_anon_secI_909', 'event_type': 'WATCH', 'watch_time_seconds': 18.0, 'video_duration_seconds': 18.0, 'progress_percent': 100.0, 'feed_position': 0},
    {'publication_id': 40, 'session_id': 'feed_session_anon_secI_909', 'event_type': 'COMPLETED', 'watch_time_seconds': 18.0, 'video_duration_seconds': 18.0, 'progress_percent': 100.0, 'feed_position': 0},
    {'publication_id': 41, 'session_id': 'feed_session_anon_secI_909', 'event_type': 'IMPRESSION', 'watch_time_seconds': 0.0, 'video_duration_seconds': 18.0, 'progress_percent': 0.0, 'feed_position': 1},
    {'publication_id': 41, 'session_id': 'feed_session_anon_secI_909', 'event_type': 'PLAY', 'watch_time_seconds': 0.0, 'video_duration_seconds': 18.0, 'progress_percent': 0.0, 'feed_position': 1},
    {'publication_id': 41, 'session_id': 'feed_session_anon_secI_909', 'event_type': 'WATCH', 'watch_time_seconds': 14.0, 'video_duration_seconds': 18.0, 'progress_percent': 77.7, 'feed_position': 1},
    {'publication_id': 41, 'session_id': 'feed_session_anon_secI_909', 'event_type': 'DISH_CLICK', 'watch_time_seconds': 14.0, 'video_duration_seconds': 18.0, 'progress_percent': 77.7, 'feed_position': 1, 'metadata': {'dish_id': '65'}},
]
for ev in s9_events:
    send_event(client_anon, ev)
print("Session 9 enregistrée (Visiteur D Anonyme).")

# Session 10 : Anonyme Visiteur E (feed_session_anon_secJ_1010)
s10_events = [
    {'publication_id': 43, 'session_id': 'feed_session_anon_secJ_1010', 'event_type': 'IMPRESSION', 'watch_time_seconds': 0.0, 'video_duration_seconds': 15.0, 'progress_percent': 0.0, 'feed_position': 0},
    {'publication_id': 43, 'session_id': 'feed_session_anon_secJ_1010', 'event_type': 'PLAY', 'watch_time_seconds': 0.0, 'video_duration_seconds': 15.0, 'progress_percent': 0.0, 'feed_position': 0},
    {'publication_id': 43, 'session_id': 'feed_session_anon_secJ_1010', 'event_type': 'WATCH', 'watch_time_seconds': 1.5, 'video_duration_seconds': 15.0, 'progress_percent': 10.0, 'feed_position': 0},
    {'publication_id': 43, 'session_id': 'feed_session_anon_secJ_1010', 'event_type': 'SKIP', 'watch_time_seconds': 1.5, 'video_duration_seconds': 15.0, 'progress_percent': 10.0, 'feed_position': 0},
    {'publication_id': 44, 'session_id': 'feed_session_anon_secJ_1010', 'event_type': 'IMPRESSION', 'watch_time_seconds': 0.0, 'video_duration_seconds': 30.0, 'progress_percent': 0.0, 'feed_position': 1},
    {'publication_id': 44, 'session_id': 'feed_session_anon_secJ_1010', 'event_type': 'PLAY', 'watch_time_seconds': 0.0, 'video_duration_seconds': 30.0, 'progress_percent': 0.0, 'feed_position': 1},
    {'publication_id': 44, 'session_id': 'feed_session_anon_secJ_1010', 'event_type': 'WATCH', 'watch_time_seconds': 1.8, 'video_duration_seconds': 30.0, 'progress_percent': 6.0, 'feed_position': 1},
    {'publication_id': 44, 'session_id': 'feed_session_anon_secJ_1010', 'event_type': 'SKIP', 'watch_time_seconds': 1.8, 'video_duration_seconds': 30.0, 'progress_percent': 6.0, 'feed_position': 1},
    {'publication_id': 45, 'session_id': 'feed_session_anon_secJ_1010', 'event_type': 'IMPRESSION', 'watch_time_seconds': 0.0, 'video_duration_seconds': 22.0, 'progress_percent': 0.0, 'feed_position': 2},
    {'publication_id': 45, 'session_id': 'feed_session_anon_secJ_1010', 'event_type': 'PLAY', 'watch_time_seconds': 0.0, 'video_duration_seconds': 22.0, 'progress_percent': 0.0, 'feed_position': 2},
    {'publication_id': 45, 'session_id': 'feed_session_anon_secJ_1010', 'event_type': 'WATCH', 'watch_time_seconds': 22.0, 'video_duration_seconds': 22.0, 'progress_percent': 100.0, 'feed_position': 2},
    {'publication_id': 45, 'session_id': 'feed_session_anon_secJ_1010', 'event_type': 'COMPLETED', 'watch_time_seconds': 22.0, 'video_duration_seconds': 22.0, 'progress_percent': 100.0, 'feed_position': 2},
    {'publication_id': 45, 'session_id': 'feed_session_anon_secJ_1010', 'event_type': 'LIKE', 'watch_time_seconds': 22.0, 'video_duration_seconds': 22.0, 'progress_percent': 100.0, 'feed_position': 2},
]
for ev in s10_events:
    send_event(client_anon, ev)
print("Session 10 enregistrée (Visiteur E Anonyme).")

# Session 11 : Anonyme Visiteur F (feed_session_anon_secK_1111)
s11_events = [
    {'publication_id': 39, 'session_id': 'feed_session_anon_secK_1111', 'event_type': 'IMPRESSION', 'watch_time_seconds': 0.0, 'video_duration_seconds': 20.0, 'progress_percent': 0.0, 'feed_position': 0},
    {'publication_id': 39, 'session_id': 'feed_session_anon_secK_1111', 'event_type': 'PLAY', 'watch_time_seconds': 0.0, 'video_duration_seconds': 20.0, 'progress_percent': 0.0, 'feed_position': 0},
    {'publication_id': 39, 'session_id': 'feed_session_anon_secK_1111', 'event_type': 'WATCH', 'watch_time_seconds': 10.0, 'video_duration_seconds': 20.0, 'progress_percent': 50.0, 'feed_position': 0},
    {'publication_id': 39, 'session_id': 'feed_session_anon_secK_1111', 'event_type': 'DISH_CLICK', 'watch_time_seconds': 10.0, 'video_duration_seconds': 20.0, 'progress_percent': 50.0, 'feed_position': 0, 'metadata': {'dish_id': '85'}},
    {'publication_id': 39, 'session_id': 'feed_session_anon_secK_1111', 'event_type': 'CART_ADD', 'watch_time_seconds': 10.0, 'video_duration_seconds': 20.0, 'progress_percent': 50.0, 'feed_position': 0, 'metadata': {'dish_id': '85'}},
]
for ev in s11_events:
    send_event(client_anon, ev)
print("Session 11 enregistrée (Visiteur F Anonyme).")

# Session 12 : Auth User #181 (feed_session_auth_secL_1212)
s12_events = [
    {'publication_id': 38, 'session_id': 'feed_session_auth_secL_1212', 'event_type': 'IMPRESSION', 'watch_time_seconds': 0.0, 'video_duration_seconds': 15.0, 'progress_percent': 0.0, 'feed_position': 0},
    {'publication_id': 38, 'session_id': 'feed_session_auth_secL_1212', 'event_type': 'PLAY', 'watch_time_seconds': 0.0, 'video_duration_seconds': 15.0, 'progress_percent': 0.0, 'feed_position': 0},
    {'publication_id': 38, 'session_id': 'feed_session_auth_secL_1212', 'event_type': 'WATCH', 'watch_time_seconds': 15.0, 'video_duration_seconds': 15.0, 'progress_percent': 100.0, 'feed_position': 0},
    {'publication_id': 38, 'session_id': 'feed_session_auth_secL_1212', 'event_type': 'COMPLETED', 'watch_time_seconds': 15.0, 'video_duration_seconds': 15.0, 'progress_percent': 100.0, 'feed_position': 0},
    {'publication_id': 38, 'session_id': 'feed_session_auth_secL_1212', 'event_type': 'LIKE', 'watch_time_seconds': 15.0, 'video_duration_seconds': 15.0, 'progress_percent': 100.0, 'feed_position': 0},
    {'publication_id': 38, 'session_id': 'feed_session_auth_secL_1212', 'event_type': 'SHARE', 'watch_time_seconds': 15.0, 'video_duration_seconds': 15.0, 'progress_percent': 100.0, 'feed_position': 0},
    {'publication_id': 42, 'session_id': 'feed_session_auth_secL_1212', 'event_type': 'IMPRESSION', 'watch_time_seconds': 0.0, 'video_duration_seconds': 25.0, 'progress_percent': 0.0, 'feed_position': 1},
    {'publication_id': 42, 'session_id': 'feed_session_auth_secL_1212', 'event_type': 'PLAY', 'watch_time_seconds': 0.0, 'video_duration_seconds': 25.0, 'progress_percent': 0.0, 'feed_position': 1},
    {'publication_id': 42, 'session_id': 'feed_session_auth_secL_1212', 'event_type': 'WATCH', 'watch_time_seconds': 25.0, 'video_duration_seconds': 25.0, 'progress_percent': 100.0, 'feed_position': 1},
    {'publication_id': 42, 'session_id': 'feed_session_auth_secL_1212', 'event_type': 'COMPLETED', 'watch_time_seconds': 25.0, 'video_duration_seconds': 25.0, 'progress_percent': 100.0, 'feed_position': 1},
    {'publication_id': 42, 'session_id': 'feed_session_auth_secL_1212', 'event_type': 'CART_ADD', 'watch_time_seconds': 25.0, 'video_duration_seconds': 25.0, 'progress_percent': 100.0, 'feed_position': 1, 'metadata': {'dish_id': '77'}},
]
for ev in s12_events:
    send_event(client_181, ev)
print("Session 12 enregistrée (User #181).")

print(f"\nTOTAL ÉVÉNEMENTS APRÈS ENRICHISSEMENT : {VideoEventLog.objects.count()}")
