import os
import sys
import shutil
import django

sys.path.append('c:\\Users\\HP\\Desktop\\Ayyou-backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.catalog.models import Categorie, Etablissement, Produit, VarianteProduit, OptionProduit

print("==================================================")
print("  POPULATION DES SANDWICHS TANGANA (CATEGORIE 10)")
print("==================================================")

# Source images
SOURCE_DIR = r"C:\Users\HP\.gemini\antigravity\brain\1f2cd0a4-e39b-4ef8-b924-e7e0bc2d34a3\.user_uploaded"
DEST_DIR = r"C:\Users\HP\Desktop\Ayyou-backend\media\dishes"

os.makedirs(DEST_DIR, exist_ok=True)

IMAGE_MAPPINGS = {
    "sandwich_tangana_mame.png": "media_1790502163799.png",
    "sandwich_tangana_petit.png": "media_1790502182253.png",
    "sandwich_tangana_centre.png": "media_1790502202840.png",
    "sandwich_tangana_express.png": "media_1790502234373.png"
}

for dest_name, src_name in IMAGE_MAPPINGS.items():
    src_path = os.path.join(SOURCE_DIR, src_name)
    dest_path = os.path.join(DEST_DIR, dest_name)
    if os.path.exists(src_path):
        shutil.copy(src_path, dest_path)
        print(f"Copied {src_name} -> {dest_name}")
    else:
        print(f"WARNING: {src_path} not found!")

cat_official = Categorie.objects.get(id=10)
print(f"Categorie officielle: {cat_official.nom} (ID {cat_official.id})")

TANGANA_SANDWICH_DISHES = [
    {
        "etablissement_nom": "Tangana Chez Mame",
        "nom": "Sandwich Tangana Viande, Œuf Dur & Frites Croquantes",
        "description": "Demi-baguette croustillante généreusement garnie de dés de viande sautée, quartiers d'œufs durs frais, frites dorées croquantes, salade verte, mayonnaise & sauce moutarde piquante.",
        "prix_base": 2500.00,
        "image_url": "http://127.0.0.1:8000/media/dishes/sandwich_tangana_mame.png",
        "temps_preparation": "10-15 min",
        "tags": ["Sandwich Tangana", "Œuf Dur", "Frites", "Chez Mame", "Mayonnaise"],
        "variantes": [
            {"titre": "Demi-Baguette Tangana Mame", "sous_titre": "Garni de viande, œuf dur & frites", "surcout_prix": 0.00, "est_requis": True, "ordre": 1},
            {"titre": "Baguette Entière XXL Mame", "sous_titre": "Format géant avec double portion de viande", "surcout_prix": 1500.00, "est_requis": False, "ordre": 2},
        ],
        "options": [
            {"type_option": OptionProduit.TYPE_SAUCE, "titre": "Sauce Mayonnaise & Moutarde", "sous_titre": "Mélange traditionnel Tangana", "surcout_prix": 100.00, "est_inclus": True, "ordre": 1},
            {"type_option": OptionProduit.TYPE_SUPPLEMENT, "titre": "Supplément Œuf Dur (x1)", "sous_titre": "Œuf dur entier supplémentaire", "surcout_prix": 300.00, "est_inclus": False, "ordre": 2},
        ]
    },
    {
        "etablissement_nom": "Le Petit Tangana",
        "nom": "Sandwich Viande Hachée Épicée, Oignons & Tomates",
        "description": "Baguette artisanale bien dorée fourrée à la viande hachée pur bœuf assaisonnée aux herbes et poivre noir, oignons crus émincés, tranches de tomates et persil frais.",
        "prix_base": 2200.00,
        "image_url": "http://127.0.0.1:8000/media/dishes/sandwich_tangana_petit.png",
        "temps_preparation": "10-15 min",
        "tags": ["Viande Hachée", "Petit Tangana", "Oignons", "Tomates", "Épicé"],
        "variantes": [
            {"titre": "Sandwich Viande Hachée Standard", "sous_titre": "Demi-baguette garnie de viande hachée", "surcout_prix": 0.00, "est_requis": True, "ordre": 1},
            {"titre": "Sandwich Viande Hachée + Frites", "sous_titre": "Formule complète avec frites à l'intérieur", "surcout_prix": 800.00, "est_requis": False, "ordre": 2},
        ],
        "options": [
            {"type_option": OptionProduit.TYPE_SAUCE, "titre": "Piment Fort Maison", "sous_titre": "Sauce piquante rouge", "surcout_prix": 100.00, "est_inclus": True, "ordre": 1},
            {"type_option": OptionProduit.TYPE_SUPPLEMENT, "titre": "Supplément Viande Hachée Extra", "sous_titre": "Portion supplémentaire de viande", "surcout_prix": 500.00, "est_inclus": False, "ordre": 2},
        ]
    },
    {
        "etablissement_nom": "Tangana Dakar Centre",
        "nom": "Sandwich Foie & Viande Sautée aux Oignons & Mayonnaise Crème",
        "description": "Le secret du centre-ville : morceaux de foie de bœuf et viande tendre sautés à la poêle avec oignons caramélisés et poivrons, nappés de sauce mayonnaise onctueuse.",
        "prix_base": 2800.00,
        "image_url": "http://127.0.0.1:8000/media/dishes/sandwich_tangana_centre.png",
        "temps_preparation": "10-15 min",
        "tags": ["Sandwich Foie", "Dakar Centre", "Oignons Sautés", "Mayonnaise"],
        "variantes": [
            {"titre": "Demie Baguette Foie & Viande", "sous_titre": "Garni de foie, viande & oignons sautés", "surcout_prix": 0.00, "est_requis": True, "ordre": 1},
            {"titre": "Baguette Royale Foie & Viande", "sous_titre": "Grand format avec frites intégrées", "surcout_prix": 1200.00, "est_requis": False, "ordre": 2},
        ],
        "options": [
            {"type_option": OptionProduit.TYPE_SAUCE, "titre": "Sauce Oignon Caramélisée", "sous_titre": "Extra sauce oignons", "surcout_prix": 200.00, "est_inclus": True, "ordre": 1},
            {"type_option": OptionProduit.TYPE_SUPPLEMENT, "titre": "Portion Foie de Bœuf Supplémentaire", "sous_titre": "Supplément foie de bœuf", "surcout_prix": 700.00, "est_inclus": False, "ordre": 2},
        ]
    },
    {
        "etablissement_nom": "Tangana Express",
        "nom": "Sandwich Tangana Express Viande & Œufs Durs Alignés",
        "description": "Préparation à la chaîne traditionnelle Tangana : baguettes chaudes garnies d'une montagne de viande assaisonnée sautée aux oignons, surmontée de lamelles d'œufs durs.",
        "prix_base": 2300.00,
        "image_url": "http://127.0.0.1:8000/media/dishes/sandwich_tangana_express.png",
        "temps_preparation": "05-10 min",
        "tags": ["Tangana Express", "Viande Sautée", "Œufs Durs", "Rapide"],
        "variantes": [
            {"titre": "Sandwich Express Formule Duo", "sous_titre": "Baguette garnie viande & œufs durs", "surcout_prix": 0.00, "est_requis": True, "ordre": 1},
            {"titre": "Formule XL Express avec Boisson", "sous_titre": "Grand sandwich + canette au choix", "surcout_prix": 1000.00, "est_requis": False, "ordre": 2},
        ],
        "options": [
            {"type_option": OptionProduit.TYPE_SAUCE, "titre": "Moutarde & Piment Vert", "sous_titre": "Sauce traditionnelle", "surcout_prix": 100.00, "est_inclus": True, "ordre": 1},
            {"type_option": OptionProduit.TYPE_SUPPLEMENT, "titre": "Double Œuf Dur", "sous_titre": "Deux œufs durs entiers", "surcout_prix": 400.00, "est_inclus": False, "ordre": 2},
        ]
    }
]

created_count = 0
for d in TANGANA_SANDWICH_DISHES:
    etab = Etablissement.objects.filter(nom__icontains=d["etablissement_nom"]).first()
    if not etab:
        print(f"Etablissement '{d['etablissement_nom']}' non trouve dans la BD.")
        continue
    
    produit, _ = Produit.objects.update_or_create(
        etablissement=etab,
        nom=d["nom"],
        defaults={
            "categorie": cat_official,
            "description": d["description"],
            "prix_base": d["prix_base"],
            "image_url": d["image_url"],
            "temps_preparation": d["temps_preparation"],
            "tags": d["tags"],
            "est_disponible": True,
            "stock_disponible": 100,
            "stock_ayyou_reserve": 50,
        }
    )
    
    produit.variantes.all().delete()
    for v in d["variantes"]:
        VarianteProduit.objects.create(
            produit=produit,
            titre=v["titre"],
            sous_titre=v["sous_titre"],
            surcout_prix=v["surcout_prix"],
            est_requis=v["est_requis"],
            ordre=v["ordre"]
        )
        
    produit.options.all().delete()
    for opt in d["options"]:
        OptionProduit.objects.create(
            produit=produit,
            type_option=opt["type_option"],
            titre=opt["titre"],
            sous_titre=opt["sous_titre"],
            surcout_prix=opt["surcout_prix"],
            est_inclus=opt["est_inclus"],
            ordre=opt["ordre"]
        )
        
    created_count += 1
    print(f"OK: Plat Sandwich Tangana [{produit.id}] '{produit.nom[:30]}...' cree pour {etab.nom}")

print(f"\nTOTAL PLATS SANDWICH TANGANA CREES: {created_count}")
