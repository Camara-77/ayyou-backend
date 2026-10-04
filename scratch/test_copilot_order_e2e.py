import os
import sys
import django

# Setup Django environment
sys.path.append('c:\\Users\\HP\\Desktop\\Ayyou-backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.test import RequestFactory
from rest_framework.test import APIClient
from apps.users.models import Utilisateur
from apps.catalog.models import Etablissement, Produit, Categorie
from apps.orders.models import Panier, PanierItem, Commande
from apps.orders.services import CartService
from apps.ai.views_planning_ai import AIPlanningParseView
from apps.ai.models import AIConversation
from decimal import Decimal

def run_e2e_tests():
    print("=" * 60)
    print("ETAPE 3 - SUITE DE TEST E2E : COMMANDER DEPUIS LE COPILOT -> VRAI PANIER")
    print("=" * 60)

    # Setup test data in real PostgreSQL DB
    user_a = Utilisateur.objects.filter(email="client_a_order_test@ayyou.sn").first()
    if not user_a:
        user_a = Utilisateur.objects.filter(numero_telephone="+221770000088").first()
    if not user_a:
        user_a = Utilisateur.objects.create(
            email="client_a_order_test@ayyou.sn",
            numero_telephone="+221770000088",
            mode_actif=Utilisateur.MODE_CLIENT,
            nom="Arona",
            prenom="Client A"
        )

    user_b = Utilisateur.objects.filter(email="client_b_order_test@ayyou.sn").first()
    if not user_b:
        user_b = Utilisateur.objects.filter(numero_telephone="+221770000099").first()
    if not user_b:
        user_b = Utilisateur.objects.create(
            email="client_b_order_test@ayyou.sn",
            numero_telephone="+221770000099",
            mode_actif=Utilisateur.MODE_CLIENT,
            nom="Binta",
            prenom="Client B"
        )

    resto_a, _ = Etablissement.objects.get_or_create(
        nom="Chez Fatou Test",
        defaults={
            "statut": Etablissement.STATUT_OUVERT,
            "adresse": "Almadies, Dakar",
            "statut_abonnement": Etablissement.STATUT_ABONNEMENT_ACTIF
        }
    )
    resto_b, _ = Etablissement.objects.get_or_create(
        nom="Chez Loutcha Test",
        defaults={
            "statut": Etablissement.STATUT_OUVERT,
            "adresse": "Plateau, Dakar",
            "statut_abonnement": Etablissement.STATUT_ABONNEMENT_ACTIF
        }
    )

    prod_a1, _ = Produit.objects.get_or_create(
        nom="Thiéboudienne Rouge Royale E2E",
        etablissement=resto_a,
        defaults={
            "prix_base": Decimal("4500.00"),
            "est_disponible": True
        }
    )
    prod_a2, _ = Produit.objects.get_or_create(
        nom="Yassa Poulet Dakar E2E",
        etablissement=resto_a,
        defaults={
            "prix_base": Decimal("4000.00"),
            "est_disponible": True
        }
    )
    prod_b1, _ = Produit.objects.get_or_create(
        nom="Dibi Agneau Plateau E2E",
        etablissement=resto_b,
        defaults={
            "prix_base": Decimal("6000.00"),
            "est_disponible": True
        }
    )
    prod_indispo, _ = Produit.objects.get_or_create(
        nom="Jus de Bouye Rupture E2E",
        etablissement=resto_a,
        defaults={
            "prix_base": Decimal("1500.00"),
            "est_disponible": False
        }
    )

    client_a = APIClient()
    client_a.force_authenticate(user=user_a)

    client_b = APIClient()
    client_b.force_authenticate(user=user_b)

    # Nettoyage préalable des paniers de test
    CartService.clear_cart(user_a)
    CartService.clear_cart(user_b)

    # TEST 1: Produit réel → ajout au panier via API POST /api/orders/cart/items/
    print("\n--- TEST 1 : Produit réel -> ajout au panier ---")
    resp = client_a.post('/api/orders/cart/items/', {'produit': prod_a1.id, 'quantite': 1})
    assert resp.status_code == 201, f"Échec ajout panier: {resp.data}"
    panier_a = CartService.get_or_create_active_cart(user_a)
    assert panier_a.items.count() == 1, "Le panier devrait contenir 1 article"
    item = panier_a.items.first()
    assert item.produit_id == prod_a1.id
    assert item.quantite == 1
    print("PASS: Produit réel ajouté avec succès au panier AYYOU.")

    # TEST 2: Prix envoyé par frontend est ignoré, prix réel PostgreSQL utilisé
    print("\n--- TEST 2 : Sécurité prix -> backend utilise le prix réel PostgreSQL ---")
    resp = client_a.post('/api/orders/cart/items/', {'produit': prod_a1.id, 'quantite': 1, 'prix': 100})
    item.refresh_from_db()
    assert item.prix_unitaire == prod_a1.prix_base, f"Prix unitaire altéré: {item.prix_unitaire} vs {prod_a1.prix_base}"
    print(f"PASS: Le prix est strictement verrouillé sur le prix PostgreSQL ({item.prix_unitaire} FCFA).")

    # TEST 3: Produit inexistant -> refus (400)
    print("\n--- TEST 3 : Produit inexistant -> refus ---")
    resp = client_a.post('/api/orders/cart/items/', {'produit': 999999, 'quantite': 1})
    assert resp.status_code == 400
    print("PASS: Refus d'ajout pour un produit inexistant.")

    # TEST 4: Produit indisponible (est_disponible=False) -> refus
    print("\n--- TEST 4 : Produit indisponible -> refus ---")
    resp = client_a.post('/api/orders/cart/items/', {'produit': prod_indispo.id, 'quantite': 1})
    assert resp.status_code == 400
    assert "disponible" in str(resp.data).lower()
    print(f"PASS: Refus propre d'ajout pour produit indisponible: {resp.data['detail']}")

    # TEST 5 & 6: Quantité par défaut (1) et quantité explicite (2)
    print("\n--- TEST 5 & 6 : Validation de la quantité (1 par défaut, 2 explicite) ---")
    CartService.clear_cart(user_a)
    item1 = CartService.add_item_to_cart(user_a, prod_a1.id, quantite=1)
    assert item1.quantite == 1
    item2 = CartService.add_item_to_cart(user_a, prod_a2.id, quantite=2)
    assert item2.quantite == 2
    print("PASS: Quantité par défaut=1 et quantité explicite=2 validées.")

    # TEST 7, 8, 9: Règle du panier mono-établissement (Resto A vs Resto B)
    print("\n--- TEST 7, 8, 9 : Règle mono-établissement (Resto A vs Resto B) ---")
    # Panier contient Resto A (prod_a1 et prod_a2). Tentative d'ajout prod_b1 (Resto B)
    resp = client_a.post('/api/orders/cart/items/', {'produit': prod_b1.id, 'quantite': 1})
    assert resp.status_code == 400
    assert resp.data.get('code') == 'CART_DIFFERENT_ESTABLISHMENT', f"Code d'erreur inattendu: {resp.data}"
    print(f"PASS: Ajout inter-établissement refusé avec le code CART_DIFFERENT_ESTABLISHMENT: {resp.data['detail']}")

    # TEST 10: Isolation multi-utilisateur
    print("\n--- TEST 10 : Isolation multi-utilisateur ---")
    panier_b = CartService.get_or_create_active_cart(user_b)
    # Utilisateur B ne voit pas le panier de l'utilisateur A
    assert panier_b.items.count() == 0
    resp_b_get = client_b.get('/api/orders/cart/')
    assert len(resp_b_get.data.get('items', [])) == 0
    print("PASS: Isolation totale entre le panier de l'utilisateur A et l'utilisateur B.")

    # TEST 11: Détection d'intention Copilot "commande-le" avec anaphore
    print("\n--- TEST 11 : Copilot intent 'commande-le' via AIPlanningParseView ---")
    conv = AIConversation.objects.create(
        utilisateur=user_a,
        context_data={
            "selected_product": {
                "id": prod_a1.id,
                "nom": prod_a1.nom,
                "prix": float(prod_a1.prix_base),
                "etablissement_id": resto_a.id,
                "etablissement_nom": resto_a.nom
            },
            "last_selected_product_id": prod_a1.id
        }
    )

    resp_ai1 = client_a.post('/api/ai/planning-parse/', {
        'prompt': 'commande-le',
        'conversation_id': conv.id
    }, format='json')

    assert resp_ai1.status_code == 200, f"Erreur AIPlanningParseView: {resp_ai1.data}"
    assert resp_ai1.data.get('status') == 'order_requested'
    assert resp_ai1.data.get('intent') == 'ADD_TO_CART'
    assert resp_ai1.data['detected_product']['id'] == prod_a1.id
    print("PASS: Copilot identifie l'intention 'commande-le' et retourne le payload d'ajout au panier.")

    # TEST 12: Copilot intent "j'en prends 2" (quantité explicite = 2)
    print("\n--- TEST 12 : Copilot intent 'j'en prends 2' ---")
    resp_ai2 = client_a.post('/api/ai/planning-parse/', {
        'prompt': "j'en prends 2",
        'conversation_id': conv.id
    }, format='json')
    assert resp_ai2.status_code == 200
    assert resp_ai2.data.get('quantite') == 2
    print("PASS: Copilot extrait correctement la quantité 2 de la demande en langage naturel.")

    print("=" * 60)
    print("TOUS LES 12 TESTS E2E COMMANDER COPILOT SONT EFFECTUÉS SUR POSTGRESQL !")
    print("=" * 60)

if __name__ == '__main__':
    run_e2e_tests()
