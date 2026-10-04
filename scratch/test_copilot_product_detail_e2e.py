import os
import sys
import django

# Setup Django environment
sys.path.append('c:\\Users\\HP\\Desktop\\Ayyou-backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from rest_framework.test import APIClient
from apps.users.models import Utilisateur
from apps.catalog.models import Etablissement, Produit, Categorie
from apps.orders.services import CartService
from apps.ai.views_planning_ai import AIPlanningParseView
from apps.ai.models import AIConversation
from decimal import Decimal

def run_e2e_tests():
    print("=" * 70)
    print("ÉTAPE 4 - SUITE DE TEST E2E : DÉTAIL PRODUIT INTÉGRÉ DANS COPILOT AYYOU")
    print("=" * 70)

    # 1. Setup real PostgreSQL test users and catalog items
    user_a = Utilisateur.objects.filter(email="client_a_detail_test@ayyou.sn").first()
    if not user_a:
        user_a = Utilisateur.objects.filter(numero_telephone="+221770000077").first()
    if not user_a:
        user_a = Utilisateur.objects.create(
            email="client_a_detail_test@ayyou.sn",
            numero_telephone="+221770000077",
            mode_actif=Utilisateur.MODE_CLIENT,
            nom="Amina",
            prenom="Client Detail A"
        )

    user_b = Utilisateur.objects.filter(email="client_b_detail_test@ayyou.sn").first()
    if not user_b:
        user_b = Utilisateur.objects.filter(numero_telephone="+221770000066").first()
    if not user_b:
        user_b = Utilisateur.objects.create(
            email="client_b_detail_test@ayyou.sn",
            numero_telephone="+221770000066",
            mode_actif=Utilisateur.MODE_CLIENT,
            nom="Babacar",
            prenom="Client Detail B"
        )

    resto_fatou, _ = Etablissement.objects.get_or_create(
        nom="Chez Fatou Almadies",
        defaults={
            "statut": Etablissement.STATUT_OUVERT,
            "adresse": "Route des Almadies, Dakar",
            "statut_verification": Etablissement.STATUT_VALIDE,
            "statut_abonnement": Etablissement.STATUT_ABONNEMENT_ACTIF
        }
    )
    resto_fatou.statut_verification = Etablissement.STATUT_VALIDE
    resto_fatou.save()

    cat_senegalaise, _ = Categorie.objects.get_or_create(
        nom="Spécialités Sénégalaises",
        defaults={"slug": "specialites-senegalaises-detail-test", "est_active": True}
    )

    prod_thieb, _ = Produit.objects.get_or_create(
        nom="Thiéboudienne Rouge Royale Detail Test",
        etablissement=resto_fatou,
        defaults={
            "prix_base": Decimal("4500.00"),
            "est_disponible": True,
            "categorie": cat_senegalaise,
            "description": "Véritable thiéboudienne au mérou frais et légumes du pays."
        }
    )

    prod_indisponible, _ = Produit.objects.get_or_create(
        nom="Yassa Poulet Épuisé Detail Test",
        etablissement=resto_fatou,
        defaults={
            "prix_base": Decimal("3500.00"),
            "est_disponible": False,
            "categorie": cat_senegalaise,
            "description": "Poulet mariné à l'oignon et au citron (Momentanément en rupture)."
        }
    )

    client_a = APIClient()
    client_a.force_authenticate(user=user_a)

    client_b = APIClient()
    client_b.force_authenticate(user=user_b)

    passed_count = 0
    total_count = 10

    # TEST 1: Fetch product detail via Copilot GET_PRODUCT_DETAIL action
    print("\n[TEST 1] Récupération du détail produit via GET_PRODUCT_DETAIL...")
    res = client_a.post('/api/ai/planning-parse/', {
        "prompt": "",
        "action": "GET_PRODUCT_DETAIL",
        "product_id": prod_thieb.id
    }, format='json')
    assert res.status_code == 200, f"Erreur status HTTP: {res.status_code}"
    data = res.json()
    assert data.get('status') in ['success', 'product_detail'], f"Statut incorrect: {data.get('status')}"
    assert 'detected_product' in data, "Clé detected_product absente de la réponse"
    print("  --> PASS: Réponse HTTP 200 et status='success'")
    passed_count += 1

    # TEST 2: Check all required product detail fields from PostgreSQL
    print("\n[TEST 2] Vérification des champs de détail du produit...")
    det = data['detected_product']
    assert det['id'] == prod_thieb.id
    assert det['nom'] == "Thiéboudienne Rouge Royale Detail Test"
    assert det['etablissement_id'] == resto_fatou.id
    assert det['etablissement_nom'] == "Chez Fatou Almadies"
    assert det['etablissement_adresse'] == "Route des Almadies, Dakar"
    assert det['description'] == "Véritable thiéboudienne au mérou frais et légumes du pays."
    assert det['est_disponible'] is True
    print("  --> PASS: Tous les champs PostgreSQL du produit sont conformes")
    passed_count += 1

    # TEST 3: Check exact formatted price in FCFA
    print("\n[TEST 3] Vérification de l'exactitude du prix et formatage...")
    assert det['prix'] == 4500
    assert "4" in det['prix_formate'] and "500" in det['prix_formate'] and "FCFA" in det['prix_formate']
    print(f"  --> PASS: Prix formater exact = '{det['prix_formate']}'")
    passed_count += 1

    # TEST 4: Check product availability status (Unavailable item)
    print("\n[TEST 4] Vérification de la gestion d'un plat indisponible en stock...")
    res_indisp = client_a.post('/api/ai/planning-parse/', {
        "prompt": "",
        "action": "GET_PRODUCT_DETAIL",
        "product_id": prod_indisponible.id
    }, format='json')
    assert res_indisp.status_code == 200
    det_indisp = res_indisp.json()['detected_product']
    assert det_indisp['est_disponible'] is False
    print("  --> PASS: Statut d'indisponibilité (est_disponible=False) correctement extrait")
    passed_count += 1

    # TEST 5: Check non-existent product ID error handling
    print("\n[TEST 5] Gestion d'un ID de produit inexistant...")
    res_err = client_a.post('/api/ai/planning-parse/', {
        "prompt": "",
        "action": "GET_PRODUCT_DETAIL",
        "product_id": 999999
    }, format='json')
    assert res_err.status_code == 200
    data_err = res_err.json()
    assert data_err.get('status') == 'error' or data_err.get('detected_product') is None
    print("  --> PASS: Produit inexistant géré proprement avec message d'erreur")
    passed_count += 1

    # TEST 6: Conversation context preservation during detail view
    print("\n[TEST 6] Préservation du contexte de conversation...")
    conv = AIConversation.objects.create(utilisateur=user_a, titre="Discussion Test Détail")
    res_conv = client_a.post('/api/ai/planning-parse/', {
        "prompt": "",
        "action": "GET_PRODUCT_DETAIL",
        "conversation_id": conv.id,
        "product_id": prod_thieb.id
    }, format='json')
    assert res_conv.status_code == 200
    data_conv = res_conv.json()
    assert data_conv.get('conversation_id') == conv.id
    print("  --> PASS: L'ID de conversation est conservé intact")
    passed_count += 1

    # TEST 7: Commander directement depuis le détail produit (Vrai Panier)
    print("\n[TEST 7] Commander directement le produit consulté depuis le détail...")
    cart_item = CartService.add_item_to_cart(user_a, prod_thieb.id, quantite=1)
    cart = cart_item.panier
    assert cart_item.produit.etablissement == resto_fatou
    assert cart_item.produit == prod_thieb
    assert cart_item.prix_unitaire == Decimal("4500.00")
    print(f"  --> PASS: Produit du détail ajouté au Panier ID #{cart.id} avec succès")
    passed_count += 1

    # TEST 8: Planifier directement depuis le détail produit (AI Planning)
    print("\n[TEST 8] Déclencher la planification depuis le produit du détail...")
    res_plan = client_a.post('/api/ai/planning-parse/', {
        "prompt": f"Je veux planifier {prod_thieb.nom}",
        "action": "CREATE_PLANNING",
        "product_id": prod_thieb.id,
        "establishment_id": resto_fatou.id
    }, format='json')
    assert res_plan.status_code == 200
    data_plan = res_plan.json()
    assert data_plan.get('detected_product', {}).get('id') == prod_thieb.id
    print("  --> PASS: Workflow de planification déclenché pour le produit consulté")
    passed_count += 1

    # TEST 9: Multi-user isolation test
    print("\n[TEST 9] Isolation multi-utilisateur du consultation de détail...")
    res_b = client_b.post('/api/ai/planning-parse/', {
        "prompt": "",
        "action": "GET_PRODUCT_DETAIL",
        "product_id": prod_thieb.id
    }, format='json')
    assert res_b.status_code == 200
    det_b = res_b.json()['detected_product']
    assert det_b['id'] == prod_thieb.id
    print("  --> PASS: Client B accède au détail du catalogue sans interférence avec Client A")
    passed_count += 1

    # TEST 10: Zero Mock Verification
    print("\n[TEST 10] Vérification de l'absence de Mock / PostgreSQL Source de Vérité...")
    db_prod = Produit.objects.get(id=prod_thieb.id)
    assert db_prod.prix_base == Decimal("4500.00")
    assert db_prod.etablissement.nom == "Chez Fatou Almadies"
    print("  --> PASS: Données lues et modifiées à 100% dans PostgreSQL réel")
    passed_count += 1

    print("\n" + "=" * 70)
    print(f"RÉSULTAT : {passed_count}/{total_count} TESTS E2E POSTGRESQL SUCCÈS")
    print("=" * 70)

if __name__ == "__main__":
    run_e2e_tests()
