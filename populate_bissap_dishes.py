import os
import sys
import shutil
import django

sys.path.append('c:\\Users\\HP\\Desktop\\Ayyou-backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.catalog.models import Categorie, Etablissement, Produit, VarianteProduit, OptionProduit

print("==================================================")
print("  POPULATION DES JUS DE BISSAP (CATEGORIE 11)")
print("==================================================")

# Source images
SOURCE_DIR = r"C:\Users\HP\.gemini\antigravity\brain\1f2cd0a4-e39b-4ef8-b924-e7e0bc2d34a3\.user_uploaded"
DEST_DIR = r"C:\Users\HP\Desktop\Ayyou-backend\media\dishes"

os.makedirs(DEST_DIR, exist_ok=True)

IMAGE_MAPPINGS = {
    "bissap_glace_menthe.jpg": "media_1790502514186.jpg",
    "bissap_bouteille_artisanale.png": "media_1790502550258.png",
    "bissap_carafe_service.png": "media_1790502568640.png",
    "bissap_verres_mousse.png": "media_1790502580226.png"
}

for dest_name, src_name in IMAGE_MAPPINGS.items():
    src_path = os.path.join(SOURCE_DIR, src_name)
    dest_path = os.path.join(DEST_DIR, dest_name)
    if os.path.exists(src_path):
        shutil.copy(src_path, dest_path)
        print(f"Copied {src_name} -> {dest_name}")
    else:
        print(f"WARNING: {src_path} not found!")

cat_official = Categorie.objects.get(id=11)
print(f"Categorie officielle: {cat_official.nom} (ID {cat_official.id})")

BISSAP_DISHES = [
    {
        "etablissement_nom": "Jus du Baobab",
        "nom": "Jus de Bissap Rouge Glacé à la Menthe Fraîche & Glaçons",
        "description": "Infusion artisanale de fleurs d'hibiscus rouge (Bissap) relevée de feuilles de menthe fraîche, vanille des îles et glaçons cristallins. Servie glacée en carafe ou grands verres.",
        "prix_base": 1200.00,
        "image_url": "http://127.0.0.1:8000/media/dishes/bissap_glace_menthe.jpg",
        "temps_preparation": "05 min",
        "tags": ["Bissap Rouge", "Menthe Fraîche", "Hibiscus", "Jus du Baobab", "Glacé"],
        "variantes": [
            {"titre": "Grand Verre 33cl", "sous_titre": "Jus de bissap glacé à la menthe", "surcout_prix": 0.00, "est_requis": True, "ordre": 1},
            {"titre": "Carafe 1 Litre", "sous_titre": "Pour partager à table (1L)", "surcout_prix": 1800.00, "est_requis": False, "ordre": 2},
        ],
        "options": [
            {"type_option": OptionProduit.TYPE_SUPPLEMENT, "titre": "Extra Menthe & Glaçons", "sous_titre": "Supplément fraîcheur menthée", "surcout_prix": 100.00, "est_inclus": True, "ordre": 1},
            {"type_option": OptionProduit.TYPE_SUPPLEMENT, "titre": "Version Allégée en Sucre", "sous_titre": "Moins de sucre naturel", "surcout_prix": 0.00, "est_inclus": False, "ordre": 2},
        ]
    },
    {
        "etablissement_nom": "Jus Chez Fatou",
        "nom": "Bouteille Artisanale de Jus de Bissap Rouge Pur",
        "description": "Bouteille nomade 50cl de jus de bissap fait maison selon la recette de Fatou : saveur intense, sucrée juste ce qu'il faut avec une touche de fleur d'oranger.",
        "prix_base": 1000.00,
        "image_url": "http://127.0.0.1:8000/media/dishes/bissap_bouteille_artisanale.png",
        "temps_preparation": "05 min",
        "tags": ["Bissap Bouteille", "Chez Fatou", "Artisanal", "50cl", "Fleur d'Oranger"],
        "variantes": [
            {"titre": "Bouteille 50cl", "sous_titre": "Format individuel 50cl scellé", "surcout_prix": 0.00, "est_requis": True, "ordre": 1},
            {"titre": "Bouteille 1.5 Litre", "sous_titre": "Grand format familial 1.5L", "surcout_prix": 1500.00, "est_requis": False, "ordre": 2},
        ],
        "options": [
            {"type_option": OptionProduit.TYPE_SUPPLEMENT, "titre": "Servi Ultra Frais / Congelé", "sous_titre": "Température sous zéro", "surcout_prix": 0.00, "est_inclus": True, "ordre": 1},
        ]
    },
    {
        "etablissement_nom": "Teranga Saveurs",
        "nom": "Infusion de Bissap Rouge Traditionnel au Versage Carafe",
        "description": "Jus de bissap traditionnel préparé chaque matin avec des fleurs de bissap séchées biologiques du Sénégal, servi au verre avec arôme naturel de muscade et vanille.",
        "prix_base": 1500.00,
        "image_url": "http://127.0.0.1:8000/media/dishes/bissap_carafe_service.png",
        "temps_preparation": "05 min",
        "tags": ["Bissap Teranga", "Bio", "Infusion", "Vanille", "Muscade"],
        "variantes": [
            {"titre": "Verre Teranga 40cl", "sous_titre": "Grand verre de bissap au parfum vanille", "surcout_prix": 0.00, "est_requis": True, "ordre": 1},
            {"titre": "Pitcher 1.5 Litre", "sous_titre": "Carafe pour toute la table", "surcout_prix": 2500.00, "est_requis": False, "ordre": 2},
        ],
        "options": [
            {"type_option": OptionProduit.TYPE_SUPPLEMENT, "titre": "Zeste de Citron Vert", "sous_titre": "Touche acidulée", "surcout_prix": 100.00, "est_inclus": False, "ordre": 1},
        ]
    },
    {
        "etablissement_nom": "Fruits Frais Dakar",
        "nom": "Duo de Verres Bissap Mousseux Frais & Parfumé",
        "description": "Nectar de bissap mixé frais avec mousse délicate en surface, parfait pour se rafraîchir en journée sous le soleil dakarois.",
        "prix_base": 1100.00,
        "image_url": "http://127.0.0.1:8000/media/dishes/bissap_verres_mousse.png",
        "temps_preparation": "05 min",
        "tags": ["Fruits Frais Dakar", "Bissap Mousseux", "Verre Frais", "Duo"],
        "variantes": [
            {"titre": "Verre Bissap Mousseux 35cl", "sous_titre": "Servi bien frappé avec mousse", "surcout_prix": 0.00, "est_requis": True, "ordre": 1},
            {"titre": "Pack 2 Verres Duo Bissap", "sous_titre": "Deux verres rafraîchissants", "surcout_prix": 900.00, "est_requis": False, "ordre": 2},
        ],
        "options": [
            {"type_option": OptionProduit.TYPE_SUPPLEMENT, "titre": "Sirop de Gingembre Extra", "sous_titre": "Touche piquante gingembre", "surcout_prix": 200.00, "est_inclus": False, "ordre": 1},
        ]
    }
]

created_count = 0
for d in BISSAP_DISHES:
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
    print(f"OK: Produit Jus de Bissap [{produit.id}] '{produit.nom[:30]}...' cree pour {etab.nom}")

print(f"\nTOTAL PRODUITS JUS DE BISSAP CREES: {created_count}")
