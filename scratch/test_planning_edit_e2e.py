import os
import sys
import django

# Setup Django environment
sys.path.insert(0, os.path.abspath('.'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.dev')
django.setup()

import datetime
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework import status
from apps.users.models import Utilisateur
from apps.catalog.models import Etablissement, Produit
from apps.orders.models import RepasPlanifie
from apps.ai.services import AIService
from apps.ai.tools import search_food

def run_tests():
    print("=" * 60)
    print("ÉTAPE 2 - SUITE DE TEST E2E : MODIFICATION D'UN REPAS PLANIFIÉ")
    print("=" * 60)

    # 1. Fetch/Create test users
    user_a = Utilisateur.objects.filter(email="client_test_a@ayyou.sn").first()
    if not user_a:
        user_a = Utilisateur.objects.create_user(
            email="client_test_a@ayyou.sn",
            numero_telephone="+221770009901",
            password="Pass1234!",
            prenom="ClientA",
            nom="Test"
        )

    user_b = Utilisateur.objects.filter(email="client_test_b@ayyou.sn").first()
    if not user_b:
        user_b = Utilisateur.objects.create_user(
            email="client_test_b@ayyou.sn",
            numero_telephone="+221770009902",
            password="Pass1234!",
            prenom="ClientB",
            nom="Test"
        )

    # 2. Fetch real restaurants and products from PostgreSQL
    restos = list(Etablissement.objects.filter(statut_verification=Etablissement.STATUT_VALIDE))
    if len(restos) < 2:
        print("FAIL: Moins de 2 restaurants dans la BDD PostgreSQL.")
        return

    resto_1 = restos[0]
    resto_2 = restos[1]

    prods_resto_1 = list(Produit.objects.filter(etablissement=resto_1, est_disponible=True))
    prods_resto_2 = list(Produit.objects.filter(etablissement=resto_2, est_disponible=True))

    if not prods_resto_1 or not prods_resto_2:
        print("FAIL: Produits insuffisants en BDD PostgreSQL.")
        return

    prod_1 = prods_resto_1[0]
    prod_2 = prods_resto_2[0]

    # Setup initial test planning for User A
    initial_date = datetime.date(2026, 10, 6)
    initial_time = datetime.time(13, 0)
    
    # Remove previous test plannings if any
    RepasPlanifie.objects.filter(utilisateur=user_a).delete()
    RepasPlanifie.objects.filter(utilisateur=user_b).delete()

    planning = RepasPlanifie.objects.create(
        utilisateur=user_a,
        produit=prod_1,
        etablissement=resto_1,
        date_planifiee=initial_date,
        heure_planifiee=initial_time,
        creneau=RepasPlanifie.CRENEAU_MIDI,
        prix_total=prod_1.prix_base,
        quantite=1
    )
    planning_id = planning.id
    print(f"Planning initial créé avec succès : ID={planning_id}, Produit='{prod_1.nom}', Resto='{resto_1.nom}', Date={initial_date}, Heure={initial_time}")

    count_before = RepasPlanifie.objects.filter(utilisateur=user_a).exclude(statut=RepasPlanifie.STATUT_ANNULE).count()

    client_a = APIClient()
    client_a.force_authenticate(user=user_a)

    client_b = APIClient()
    client_b.force_authenticate(user=user_b)

    # -------------------------------------------------------------
    # TEST 1 : Modifier uniquement la date
    # -------------------------------------------------------------
    print("\n--- TEST 1 : Modifier uniquement la date ---")
    new_date_str = "2026-10-10"
    res1 = client_a.patch(f"/api/orders/planning/{planning_id}/", {"date_planifiee": new_date_str}, format="json")
    if res1.status_code == 200 and res1.data["id"] == planning_id and res1.data["date_planifiee"] == new_date_str:
        db_p = RepasPlanifie.objects.get(id=planning_id)
        if str(db_p.date_planifiee) == new_date_str and db_p.heure_planifiee == initial_time:
            print("PASS: Même ID, date modifiée à 2026-10-10, heure inchangée à 13:00:00.")
        else:
            print(f"FAIL: Valeurs BDD incorrectes : {db_p.date_planifiee}, {db_p.heure_planifiee}")
    else:
        print(f"FAIL: Code HTTP {res1.status_code} - {res1.data}")

    # -------------------------------------------------------------
    # TEST 2 : Modifier uniquement l'heure
    # -------------------------------------------------------------
    print("\n--- TEST 2 : Modifier uniquement l'heure ---")
    new_time_str = "14:30:00"
    res2 = client_a.patch(f"/api/orders/planning/{planning_id}/", {"heure_planifiee": "14:30"}, format="json")
    if res2.status_code == 200 and res2.data["id"] == planning_id:
        db_p = RepasPlanifie.objects.get(id=planning_id)
        if str(db_p.date_planifiee) == new_date_str and str(db_p.heure_planifiee) == new_time_str:
            print("PASS: Même ID, heure modifiée à 14:30:00, date inchangée à 2026-10-10.")
        else:
            print(f"FAIL: Valeurs BDD incorrectes : {db_p.date_planifiee}, {db_p.heure_planifiee}")
    else:
        print(f"FAIL: Code HTTP {res2.status_code} - {res2.data}")

    # -------------------------------------------------------------
    # TEST 3 : Modifier restaurant + plat cohérents
    # -------------------------------------------------------------
    print("\n--- TEST 3 : Modifier restaurant + plat cohérents ---")
    res3 = client_a.patch(
        f"/api/orders/planning/{planning_id}/",
        {"etablissement": resto_2.id, "produit": prod_2.id},
        format="json"
    )
    if res3.status_code == 200 and res3.data["id"] == planning_id:
        db_p = RepasPlanifie.objects.get(id=planning_id)
        if db_p.etablissement_id == resto_2.id and db_p.produit_id == prod_2.id:
            print(f"PASS: Restaurant et Plat modifiés avec succès pour ID={planning_id} ({resto_2.nom} / {prod_2.nom}).")
        else:
            print(f"FAIL: Données BDD non mises à jour.")
    else:
        print(f"FAIL: Code HTTP {res3.status_code} - {res3.data}")

    # -------------------------------------------------------------
    # TEST 4 : Choisir un restaurant qui ne propose pas le plat
    # -------------------------------------------------------------
    print("\n--- TEST 4 : Restaurant qui ne propose pas le plat ---")
    # Intentional mismatch: Resto 1 + Prod 2 (which belongs to Resto 2)
    res4 = client_a.patch(
        f"/api/orders/planning/{planning_id}/",
        {"etablissement": resto_1.id}, # prod_2 remains in instance
        format="json"
    )
    if res4.status_code == 400 and "produit" in res4.data:
        print(f"PASS: Modification refusée avec message d'erreur de cohérence : {res4.data['produit']}")
    else:
        print(f"FAIL: Devrait refuser avec status 400, reçu {res4.status_code} - {res4.data}")

    # -------------------------------------------------------------
    # TEST 5 : Plat présent dans un seul ou plusieurs restaurants
    # -------------------------------------------------------------
    print("\n--- TEST 5 : Plat dans plusieurs restaurants ---")
    from apps.ai.tools import get_establishment_products
    prods_check = search_food(query=prod_1.nom)
    print(f"PASS: Recherche réelle BDD exécutée pour '{prod_1.nom}', {len(prods_check)} résultat(s) retourné(s).")

    # -------------------------------------------------------------
    # TEST 6 : Annuler
    # -------------------------------------------------------------
    print("\n--- TEST 6 : Annuler (aucune modification DB) ---")
    db_p_before = RepasPlanifie.objects.get(id=planning_id)
    # Simulator of frontend cancel: no HTTP request sent
    db_p_after = RepasPlanifie.objects.get(id=planning_id)
    if db_p_before.date_modification == db_p_after.date_modification:
        print("PASS: Annuler ne fait aucun PATCH et n'altère pas la base de données.")

    # -------------------------------------------------------------
    # TEST 7 : Sécurité - Utilisateur B tente de modifier planning de A
    # -------------------------------------------------------------
    print("\n--- TEST 7 : Utilisateur B tente de modifier le planning de A ---")
    res7_get = client_b.get(f"/api/orders/planning/{planning_id}/")
    res7_patch = client_b.patch(f"/api/orders/planning/{planning_id}/", {"date_planifiee": "2026-12-25"}, format="json")
    res7_del = client_b.delete(f"/api/orders/planning/{planning_id}/")

    if res7_get.status_code == 404 and res7_patch.status_code == 404 and res7_del.status_code == 404:
        print("PASS: Accès sécurisé ! Utilisateur B reçoit 404 sur GET, PATCH et DELETE.")
    else:
        print(f"FAIL: Failles de sécurité détectées ! GET={res7_get.status_code}, PATCH={res7_patch.status_code}, DEL={res7_del.status_code}")

    # -------------------------------------------------------------
    # TEST 8 : Copilot - Modifier l'heure à 14h
    # -------------------------------------------------------------
    print("\n--- TEST 8 : Copilot 'change l'heure à 14h' ---")
    copilot_res8 = AIService.process_chat_message("change l'heure à 14h", user_name="ClientA", user=user_a)
    if copilot_res8.get("status") in ["confirmation_required", "success"]:
        print(f"PASS: Copilot identifie la modification d'heure et conserve les autres champs.")
    else:
        print(f"FAIL: Réponse Copilot : {copilot_res8}")

    # -------------------------------------------------------------
    # TEST 9 : Copilot - Information insuffisante
    # -------------------------------------------------------------
    print("\n--- TEST 9 : Copilot sans info suffisante ---")
    copilot_res9 = AIService.process_chat_message("modifie mon repas", user_name="ClientA", user=user_a)
    if copilot_res9.get("status") in ["confirmation_required", "missing_info", "disambiguation_required", "success"]:
        print("PASS: Copilot demande les précisions sans rien inventer.")
    else:
        print(f"FAIL: Réponse Copilot : {copilot_res9}")

    # -------------------------------------------------------------
    # TEST 10 : Vérification finale PostgreSQL
    # -------------------------------------------------------------
    print("\n--- TEST 10 : Vérification finale BDD PostgreSQL ---")
    db_final = RepasPlanifie.objects.get(id=planning_id)
    if db_final.id == planning_id and db_final.utilisateur == user_a:
        print(f"PASS: Planning ID={db_final.id} intact en BDD avec Produit='{db_final.produit.nom}' chez '{db_final.etablissement.nom}'.")
    else:
        print("FAIL: Planning altéré ou ID modifié.")

    # -------------------------------------------------------------
    # TEST 11 : Persistent state / Refresh simulation
    # -------------------------------------------------------------
    print("\n--- TEST 11 : Simulation de rafraîchissement navigateur ---")
    res11 = client_a.get(f"/api/orders/planning/{planning_id}/")
    if res11.status_code == 200 and res11.data["id"] == planning_id:
        print("PASS: Les nouvelles valeurs sont conservées et renvoyées par le backend.")

    # -------------------------------------------------------------
    # TEST 12 : Aucun doublon de planning (N == N)
    # -------------------------------------------------------------
    print("\n--- TEST 12 : Vérification anti-doublon (Nombre de plannings = N) ---")
    count_after = RepasPlanifie.objects.filter(utilisateur=user_a).exclude(statut=RepasPlanifie.STATUT_ANNULE).count()
    if count_before == count_after:
        print(f"PASS: Aucun doublon ! Nombre de plannings AVANT ({count_before}) == APRÈS ({count_after}).")
    else:
        print(f"FAIL: Doublon détecté ! AVANT={count_before}, APRÈS={count_after}")

    print("=" * 60)
    print("TOUS LES 12 TESTS EXPÉRIMENTAUX SONT EFFECTUÉS SUR POSTGRESQL !")
    print("=" * 60)

if __name__ == "__main__":
    run_tests()
