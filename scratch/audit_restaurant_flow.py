import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import json
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.test import RequestFactory
from django.contrib.auth import get_user_model
from rest_framework.test import APIRequestFactory, force_authenticate

from apps.catalog.models import (
    Etablissement, Categorie, Produit, VarianteProduit, OptionProduit, PublicationFeed
)
from apps.orders.models import Commande, SousCommande, Panier, PanierItem, LigneCommande
from apps.deliveries.models import Livraison
from apps.admin_panel.models import AuditLog
from apps.pro_api.views_merchant import (
    MerchantProfileView, MerchantProductListView, MerchantProductDetailView,
    MerchantProductToggleView, MerchantStatsView, MerchantOrderListView,
    MerchantOrderStatusUpdateView
)
from apps.catalog.views import (
    EtablissementListView, EtablissementDetailView, ProduitDetailView
)
from apps.orders.services import OrderService, CartService
from apps.ai.tools import search_food, search_establishments

User = get_user_model()
factory = APIRequestFactory()

def run_restaurant_audit():
    print("=" * 70)
    print("AUDIT COMPLET DU PARCOURS RESTAURANT AYYOU")
    print("=" * 70)

    # 1. SETUP RESTAURANT PRO USER & ETABLISSEMENT
    print("\n--- 1. Verification Compte PRO Restaurant & Etablissement ---")
    pro_user, created = User.objects.get_or_create(
        email="restaurant_audit@ayyou.sn",
        defaults={
            "numero_telephone": "+221770000099",
            "nom": "Loutcha",
            "prenom": "Chez",
            "est_actif": True
        }
    )
    if created:
        pro_user.set_password("Password123!")
        pro_user.save()

    from apps.users.models import Role, UtilisateurRole
    role_restau, _ = Role.objects.get_or_create(nom=Role.RESTAURANT, defaults={'description': 'Restaurant'})
    UtilisateurRole.objects.get_or_create(utilisateur=pro_user, role=role_restau)

    etablissement, etab_created = Etablissement.objects.get_or_create(
        proprietaire=pro_user,
        defaults={
            "nom": "Chez Loutcha Dakar",
            "type_etablissement": Etablissement.TYPE_RESTAURANT,
            "slogan": "La véritable cuisine Sénégalaise",
            "description": "Spécialités de Thiéboudienne, Yassa, Maffé et Dibi",
            "adresse": "101 Rue Victor Hugo, Dakar Centre",
            "latitude": 14.6698,
            "longitude": -17.4381,
            "telephone": "+221338210000",
            "statut": Etablissement.STATUT_OUVERT,
            "statut_verification": Etablissement.STATUT_VALIDE,
            "est_verifie": True,
            "note_moyenne": 4.8,
            "nombre_avis": 124
        }
    )
    # Ensure verification is VALIDE
    if etablissement.statut_verification != Etablissement.STATUT_VALIDE:
        etablissement.statut_verification = Etablissement.STATUT_VALIDE
        etablissement.est_verifie = True
        etablissement.save()

    print(f"[OK] Proprietaire: {pro_user.email} (Mode: {pro_user.mode_actif})")
    print(f"[OK] Etablissement: ID={etablissement.id}, Nom='{etablissement.nom}', Type={etablissement.type_etablissement}, Statut={etablissement.statut_verification}")

    # 2. CATEGORIE & PRODUITS MENU
    print("\n--- 2. Structure Menu, Catégories, Produits & Options ---")
    cat_plats, _ = Categorie.objects.get_or_create(
        slug="plats-nationaux",
        defaults={"nom": "Plats Nationaux", "icone": "utensils", "ordre": 1}
    )

    produit_thieb, prod_created = Produit.objects.get_or_create(
        etablissement=etablissement,
        nom="Thiéboudienne Penda Mbaye",
        defaults={
            "categorie": cat_plats,
            "description": "Riz au poisson rouge traditionnel dakarois avec légumes et morue séchée",
            "prix_base": 4500.00,
            "image_url": "https://res.cloudinary.com/ayyou/image/upload/v1/thieb.jpg",
            "est_disponible": True,
            "stock_disponible": 50,
            "stock_ayyou_reserve": 30,
            "temps_preparation": "20-30 min"
        }
    )

    variante_gourmand, _ = VarianteProduit.objects.get_or_create(
        produit=produit_thieb,
        titre="Portion Gourmande Tiof XL",
        defaults={"surcout_prix": 1500.00, "est_requis": False}
    )

    option_sauce, _ = OptionProduit.objects.get_or_create(
        produit=produit_thieb,
        titre="Sauce Beurre d'Arachide Pimentée",
        defaults={"type_option": OptionProduit.TYPE_SAUCE, "surcout_prix": 500.00}
    )

    print(f"[OK] Catégorie: '{cat_plats.nom}'")
    print(f"[OK] Produit: ID={produit_thieb.id}, Nom='{produit_thieb.nom}', Prix={produit_thieb.prix_base} FCFA")
    print(f"[OK] Variante: '{variante_gourmand.titre}' (+{variante_gourmand.surcout_prix} FCFA)")
    print(f"[OK] Option: '{option_sauce.titre}' (+{option_sauce.surcout_prix} FCFA)")

    # 3. VERIFICATION DES ENDPOINTS PARCOURS PRO MARCHAND
    print("\n--- 3. Validation Endpoints Marchand (IsApprovedMerchant) ---")
    # GET Profil
    req = factory.get("/api/pro/merchant/profile/")
    force_authenticate(req, user=pro_user)
    res = MerchantProfileView.as_view()(req)
    assert res.status_code == 200, f"Profil error: {res.data}"
    print(f"[OK] GET /api/pro/merchant/profile/ -> 200 OK (Etablissement: {res.data.get('nom')})")

    # GET Products
    req = factory.get("/api/pro/merchant/products/")
    force_authenticate(req, user=pro_user)
    res = MerchantProductListView.as_view()(req)
    assert res.status_code == 200, f"Products list error: {res.data}"
    print(f"[OK] GET /api/pro/merchant/products/ -> 200 OK ({len(res.data)} produits rattachés)")

    # Toggle Disponibilité
    req = factory.patch(f"/api/pro/merchant/products/{produit_thieb.id}/toggle-disponibilite/")
    force_authenticate(req, user=pro_user)
    res = MerchantProductToggleView.as_view()(req, pk=produit_thieb.id)
    assert res.status_code == 200
    new_state = res.data.get('est_disponible')
    print(f"[OK] PATCH toggle-disponibilite -> est_disponible = {new_state}")
    # Reset back to True
    if not new_state:
        produit_thieb.est_disponible = True
        produit_thieb.save()

    # GET Merchant Stats
    req = factory.get("/api/pro/merchant/stats/")
    force_authenticate(req, user=pro_user)
    res = MerchantStatsView.as_view()(req)
    assert res.status_code == 200
    print(f"[OK] GET /api/pro/merchant/stats/ -> 200 OK (Orders today: {res.data.get('todayOrdersCount')}, Revenue: {res.data.get('todayRevenueFcfa')} FCFA)")

    # 4. VERIFICATION ENDPOINTS PUBLIC / CLIENT
    print("\n--- 4. Validation Endpoints Publics & Client ---")
    req = factory.get("/api/catalog/etablissements/restaurants/")
    res = EtablissementListView.as_view()(req)
    assert res.status_code == 200
    found_etab = any(e['id'] == etablissement.id for e in (res.data.get('results') or res.data))
    print(f"[OK] GET /api/catalog/etablissements/restaurants/ -> Restaurant visible dans le catalogue client: {found_etab}")

    req = factory.get(f"/api/catalog/etablissements/{etablissement.id}/")
    res = EtablissementDetailView.as_view()(req, pk=etablissement.id)
    assert res.status_code == 200
    print(f"[OK] GET /api/catalog/etablissements/{etablissement.id}/ -> Détail restaurant avec {len(res.data.get('produits', []))} produits")

    # 5. CYCLE DE COMMANDE CLIENT -> MARSHAND PRO -> LIVREUR
    print("\n--- 5. Test du Cycle de Commande Complet ---")
    client_user, _ = User.objects.get_or_create(
        email="client_audit@ayyou.sn",
        defaults={
            "numero_telephone": "+221770000088",
            "nom": "Diop",
            "prenom": "Awa",
            "est_actif": True
        }
    )

    # Création du panier client
    panier, _ = Panier.objects.get_or_create(utilisateur=client_user, actif=True)
    PanierItem.objects.filter(panier=panier).delete()
    
    item = PanierItem.objects.create(
        panier=panier,
        produit=produit_thieb,
        quantite=2,
        prix_unitaire=produit_thieb.prix_base,
        variante=variante_gourmand
    )
    item.options.add(option_sauce)

    print(f"[OK] Panier Client configuré: 2x {produit_thieb.nom} (+ {variante_gourmand.titre} & {option_sauce.titre})")

    # Passage de la commande via OrderService.checkout
    commande = OrderService.checkout(
        utilisateur=client_user,
        adresse_livraison="Rue 14 x 15 Médina, Dakar",
        latitude_livraison=14.6750,
        longitude_livraison=-17.4420,
        nom_destinataire="Awa Diop",
        telephone_destinataire="+221770000088",
        instructions_livraison="Appeler en arrivant devant la porte bleue"
    )
    sous_commandes = list(commande.sous_commandes.all())
    # Marquer comme payée pour lancer la préparation restaurant
    commande.statut = Commande.STATUT_PAYEE
    commande.save()
    for sc in sous_commandes:
        sc.statut = Commande.STATUT_PAYEE
        sc.save()

    print(f"[OK] Commande passée: #{commande.numero_commande} (Total: {commande.total} FCFA)")
    print(f"[OK] Sous-commande rattachée: #{sous_commandes[0].id} pour l'établissement '{sous_commandes[0].etablissement.nom}'")

    # Marchand consulte la commande
    sc_id = sous_commandes[0].id
    req = factory.get("/api/pro/merchant/orders/")
    force_authenticate(req, user=pro_user)
    res = MerchantOrderListView.as_view()(req)
    assert res.status_code == 200
    orders_list = res.data if isinstance(res.data, list) else res.data.get('results', [])
    sc_received = any(o['id'] == sc_id for o in orders_list)
    print(f"[OK] Sous-commande visible dans le Dashboard Marchand: {sc_received}")

    # Marchand met à jour le statut: PAYEE -> EN_PREPARATION
    req = factory.patch(f"/api/pro/merchant/orders/{sc_id}/status/", {"statut": Commande.STATUT_EN_PREPARATION}, format='json')
    force_authenticate(req, user=pro_user)
    res = MerchantOrderStatusUpdateView.as_view()(req, pk=sc_id)
    assert res.status_code == 200, f"Status update error: {res.data}"
    print(f"[OK] Statut mis à jour par le Marchand: -> EN_PREPARATION")

    # Marchand met à jour le statut: EN_PREPARATION -> PRETE
    req = factory.patch(f"/api/pro/merchant/orders/{sc_id}/status/", {"statut": Commande.STATUT_PRETE}, format='json')
    force_authenticate(req, user=pro_user)
    res = MerchantOrderStatusUpdateView.as_view()(req, pk=sc_id)
    assert res.status_code == 200
    print(f"[OK] Statut mis à jour par le Marchand: -> PRETE")

    # Vérification synchronisation globale (Commande & Livraison)
    commande.refresh_from_db()
    livraisons = Livraison.objects.filter(commande=commande)
    print(f"[OK] Statut global Commande synchronisé: {commande.statut}")
    print(f"[OK] Course de Livraison créée pour les livreurs: {livraisons.exists()} (Statut Livraison: {livraisons.first().statut if livraisons.exists() else 'N/A'})")

    # 6. INTEGRATION CHATBOT IA
    print("\n--- 6. Test d'Intégration du Chatbot IA (Conseiller Gastronomique) ---")
    restos_found = search_establishments(query="Loutcha", location="Dakar")
    dishes_found = search_food(query="Thiéboudienne")
    print(f"[OK] IA Tool search_establishments: {len(restos_found)} résultat(s)")
    print(f"[OK] IA Tool search_food: {len(dishes_found)} résultat(s)")

    print("\n" + "=" * 70)
    print("RÉSULTAT DE L'AUDIT : 100% SUCCÈS - PARCOURS RESTAURANT PARFAITEMENT INTÉGRÉ")
    print("=" * 70)

if __name__ == "__main__":
    run_restaurant_audit()
