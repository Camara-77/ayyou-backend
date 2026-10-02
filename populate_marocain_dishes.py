import os
import sys
import shutil
import django

# Configuration environnement Django
sys.path.append(r'C:\Users\HP\Desktop\Ayyou-backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.catalog.models import Categorie, Etablissement, Produit, VarianteProduit, OptionProduit

MEDIA_DIR = r'C:\Users\HP\Desktop\Ayyou-backend\media\dishes'
os.makedirs(MEDIA_DIR, exist_ok=True)

USER_UPLOADED_DIR = r'C:\Users\HP\.gemini\antigravity\brain\1f2cd0a4-e39b-4ef8-b924-e7e0bc2d34a3\.user_uploaded'

# Plats Cuisine marocaine (ID 19)
dishes_data = [
    {
        "cat_id": 19,
        "etab_id": 116, # Délices du Maroc
        "src_image": "media_1790513402155.jpg",
        "dest_image": "poulet_mhammar_citron_confit_olives.jpg",
        "nom": "Poulet M'hammar aux Citrons Confits & Olives Vertes",
        "description": "Poulet rôti à la marocaine mariné au safran pur, gingembre, ail et coriandre, nappé de sauce Dghmira onctueuse aux oignons caramélisés, citron confit et olives vertes. Servi avec pain marocain chaud.",
        "prix_base": 6500,
        "temps_prep": 25,
        "tags": "Cuisine marocaine, Poulet M'hammar, Dghmira, Citron Confit, Olives",
        "variantes": [
            {"titre": "Portion Poulet", "sous_titre": "Demi-Poulet M'hammar (1 Pers)", "surcout_prix": 0, "est_requis": True, "ordre": 1},
            {"titre": "Portion Poulet", "sous_titre": "Poulet Entier M'hammar (2-3 Pers)", "surcout_prix": 5500, "est_requis": True, "ordre": 2},
        ],
        "options": [
            {"type_option": "Accompagnement", "titre": "Pain Khobz Marocain", "sous_titre": "Pain tradition chaud cuit au four", "surcout_prix": 0, "est_inclus": True, "ordre": 1},
            {"type_option": "Extra", "titre": "Extra Sauce Dghmira", "sous_titre": "Ramequin de sauce oignons caramélisés & abats", "surcout_prix": 1000, "est_inclus": False, "ordre": 2},
            {"type_option": "Boisson", "titre": "Thé à la menthe fraiche", "sous_titre": "Verre de thé vert marocain pignon/menthe", "surcout_prix": 1000, "est_inclus": False, "ordre": 3}
        ]
    },
    {
        "cat_id": 19,
        "etab_id": 114, # Le Riad Dakar
        "src_image": "media_1790513413990.jpg",
        "dest_image": "poulet_roti_harissa_citron_amandes.jpg",
        "nom": "Poulet Rôti Harissa, Citrons Sculptés & Amandes Mondées",
        "description": "Poulet fermier rôti au four façon Riad marocain, accompagné de citrons sculptés garnis de harissa rouge artisanale et piment vert, servi avec son ramequin d'amandes mondées grillées.",
        "prix_base": 7000,
        "temps_prep": 25,
        "tags": "Cuisine marocaine, Poulet Rôti, Harissa, Amandes, Riad",
        "variantes": [
            {"titre": "Portion", "sous_titre": "Demi-Poulet Rôti Harissa", "surcout_prix": 0, "est_requis": True, "ordre": 1},
            {"titre": "Portion", "sous_titre": "Poulet Entier Rôti Harissa", "surcout_prix": 5000, "est_requis": True, "ordre": 2},
        ],
        "options": [
            {"type_option": "Sauce", "titre": "Duo Harissa Rouge & Verte", "sous_titre": "Piments doux et fort servis dans citrons", "surcout_prix": 0, "est_inclus": True, "ordre": 1},
            {"type_option": "Extra", "titre": "Extra Amandes Frites", "sous_titre": "Portion d'amandes mondées croustillantes", "surcout_prix": 1500, "est_inclus": False, "ordre": 2}
        ]
    },
    {
        "cat_id": 19,
        "etab_id": 113, # Saveurs de Marrakech
        "src_image": "media_1790513427486.png",
        "dest_image": "poulet_mhammar_royal_amandes_dghmira.png",
        "nom": "Poulet M'hammar Royal aux Amandes & Dghmira",
        "description": "Spécialité cérémoniale marocaine : Poulet rôti croustillant sur lit de sauce dghmira riche aux oignons, foie et épices de Marrakech, généreusement saupoudré d'amandes dorées et d'olives.",
        "prix_base": 7500,
        "temps_prep": 30,
        "tags": "Cuisine marocaine, Poulet Royal, Marrakech, Amandes Frites, Dghmira",
        "variantes": [
            {"titre": "Format Servie", "sous_titre": "Portion Individuelle Royale", "surcout_prix": 0, "est_requis": True, "ordre": 1},
            {"titre": "Format Servie", "sous_titre": "Grand Plat Festif (Poulet Entier + Amandes)", "surcout_prix": 6500, "est_requis": True, "ordre": 2},
        ],
        "options": [
            {"type_option": "Accompagnement", "titre": "Pain Khobz Traditionnel", "sous_titre": "Pain marocain fait maison", "surcout_prix": 0, "est_inclus": True, "ordre": 1},
            {"type_option": "Extra", "titre": "Portion Amandes Frites Extra", "sous_titre": "Amandes croquantes salées", "surcout_prix": 1500, "est_inclus": False, "ordre": 2}
        ]
    }
]

print("==================================================")
print("  POPULATION CUISINE MAROCAINE (CAT 19)")
print("==================================================")

created_count = 0
for item in dishes_data:
    cat = Categorie.objects.get(id=item["cat_id"])
    etab = Etablissement.objects.get(id=item["etab_id"])
    
    # Copy file to media/dishes
    src_path = os.path.join(USER_UPLOADED_DIR, item["src_image"])
    dest_path = os.path.join(MEDIA_DIR, item["dest_image"])
    
    if os.path.exists(src_path):
        shutil.copy(src_path, dest_path)
        print(f"Copied {item['src_image']} -> {item['dest_image']}")
    else:
        print(f"WARNING: File {src_path} not found!")

    image_url = f"http://127.0.0.1:8000/media/dishes/{item['dest_image']}"

    # Supprimer les anciens produits identiques s'ils existent pour éviter doublon
    Produit.objects.filter(etablissement=etab, nom=item["nom"]).delete()

    produit = Produit.objects.create(
        etablissement=etab,
        categorie=cat,
        nom=item["nom"],
        description=item["description"],
        prix_base=item["prix_base"],
        temps_preparation=item["temps_prep"],
        image_url=image_url,
        est_disponible=True,
        stock_disponible=50,
        stock_ayyou_reserve=10,
        tags=item["tags"]
    )
    created_count += 1
    print(f"OK: Plat [{produit.id}] '{produit.nom[:35]}...' créé pour '{etab.nom}' dans Categorie {cat.nom}")

    # Variantes
    for v_data in item["variantes"]:
        VarianteProduit.objects.create(
            produit=produit,
            titre=v_data["titre"],
            sous_titre=v_data["sous_titre"],
            surcout_prix=v_data["surcout_prix"],
            est_requis=v_data["est_requis"],
            ordre=v_data["ordre"]
        )

    # Options
    for o_data in item["options"]:
        OptionProduit.objects.create(
            produit=produit,
            type_option=o_data["type_option"],
            titre=o_data["titre"],
            sous_titre=o_data["sous_titre"],
            surcout_prix=o_data["surcout_prix"],
            est_inclus=o_data["est_inclus"],
            ordre=o_data["ordre"]
        )

print(f"\nTOTAL PLATS CREES: {created_count}")
