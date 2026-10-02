import os
import sys
import shutil
import django

sys.path.append('c:\\Users\\HP\\Desktop\\Ayyou-backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.catalog.models import Categorie, Etablissement, Produit, VarianteProduit, OptionProduit

print("==================================================")
print("  POPULATION DES PLATS MBAKHALOU SALOUM")
print("==================================================")

# Source images
SOURCE_DIR = r"C:\Users\HP\.gemini\antigravity\brain\1f2cd0a4-e39b-4ef8-b924-e7e0bc2d34a3\.user_uploaded"
DEST_DIR = r"C:\Users\HP\Desktop\Ayyou-backend\media\dishes"

os.makedirs(DEST_DIR, exist_ok=True)

IMAGE_MAPPINGS = {
    "mbakhal_teranga.png": "media_1790474905830.png",
    "mbakhal_chez_penda.jpg": "media_1790474917678.jpg",
    "mbakhal_royal_baobab.jpg": "media_1790474933321.jpg",
    "mbakhal_ndar.jpg": "media_1790474957438.jpg"
}

for dest_name, src_name in IMAGE_MAPPINGS.items():
    src_path = os.path.join(SOURCE_DIR, src_name)
    dest_path = os.path.join(DEST_DIR, dest_name)
    if os.path.exists(src_path):
        shutil.copy(src_path, dest_path)
        print(f"Copied {src_name} -> {dest_name}")
    else:
        print(f"WARNING: {src_path} not found!")

cat_official = Categorie.objects.get(id=8)
print(f"Categorie officielle: {cat_official.nom} (ID {cat_official.id})")

MBAKHAL_DISHES = [
    {
        "etablissement_nom": "Teranga Saveurs",
        "nom": "Mbakhalou Saloum Royal au Niébé, Viande Séchée & Citron Vert",
        "description": "Spécialité authentique et généreuse du Saloum : riz rouge/millet savoureusement cuit avec du niébé fondant, morceaux de viande séchée (Khonkh) et poisson fumé Kétiakh, garni de poivrons colorés, piment frais et rondelle de citron vert.",
        "prix_base": 4200.00,
        "image_url": "http://127.0.0.1:8000/media/dishes/mbakhal_teranga.png",
        "temps_preparation": "15-20 min",
        "tags": ["Mbakhalou Saloum", "Niébé", "Viande Séchée", "Kétiakh", "Tradition"],
        "variantes": [
            {"titre": "Assiette Mbakhal Teranga 1 Personne", "sous_titre": "Riz niébé, viande séchée & piment", "surcout_prix": 0.00, "est_requis": True, "ordre": 1},
            {"titre": "Bol Saloum XL Familial", "sous_titre": "Portion généreuse 2 personnes", "surcout_prix": 2500.00, "est_requis": False, "ordre": 2},
        ],
        "options": [
            {"type_option": OptionProduit.TYPE_SAUCE, "titre": "Rondelle de Citron Vert Extra", "sous_titre": "Fraîcheur acidulée", "surcout_prix": 100.00, "est_inclus": True, "ordre": 1},
            {"type_option": OptionProduit.TYPE_SUPPLEMENT, "titre": "Supplément Niébé & Viande", "sous_titre": "Portion extra viande & haricots", "surcout_prix": 1000.00, "est_inclus": False, "ordre": 2},
        ]
    },
    {
        "etablissement_nom": "Chez Penda",
        "nom": "Mbakhalou Saloum Traditionnel au Niébé & Agneau Tendre",
        "description": "Préparation traditionnelle fait maison à la pâte d'arachide légère, niébé tendre, morceaux d'agneau braisés et kéthiakh séché, relevée par un piment jaune-rouge et du citron vert pur.",
        "prix_base": 3800.00,
        "image_url": "http://127.0.0.1:8000/media/dishes/mbakhal_chez_penda.jpg",
        "temps_preparation": "15-20 min",
        "tags": ["Mbakhal", "Chez Penda", "Agneau", "Niébé", "Piment"],
        "variantes": [
            {"titre": "Plat Individuel Tradition", "sous_titre": "Riz niébé & agneau tendre", "surcout_prix": 0.00, "est_requis": True, "ordre": 1},
            {"titre": "Plat Duo Terroir", "sous_titre": "2 personnes avec double viande", "surcout_prix": 2200.00, "est_requis": False, "ordre": 2},
        ],
        "options": [
            {"type_option": OptionProduit.TYPE_SAUCE, "titre": "Piment Jaune Entier", "sous_titre": "Piment fort du jardin", "surcout_prix": 200.00, "est_inclus": True, "ordre": 1},
            {"type_option": OptionProduit.TYPE_SUPPLEMENT, "titre": "Supplément Agneau Braisé", "sous_titre": "Morceau d'agneau supplémentaire", "surcout_prix": 1200.00, "est_inclus": False, "ordre": 2},
        ]
    },
    {
        "etablissement_nom": "Le Baobab Gourmand",
        "nom": "Mbakhalou Saloum Prestige au Faitout & Viande Bovine",
        "description": "Magnifique dôme de Mbakhal préparé avec soin : grains de riz concassé d'arachide, niébé cuit à cœur et morceaux généreux de viande bovine mijotée.",
        "prix_base": 4500.00,
        "image_url": "http://127.0.0.1:8000/media/dishes/mbakhal_royal_baobab.jpg",
        "temps_preparation": "20-25 min",
        "tags": ["Mbakhal Prestige", "Baobab Gourmand", "Viande Bovine", "Niébé"],
        "variantes": [
            {"titre": "Assiette Gourmande Individual", "sous_titre": "Servie sur grande assiette porcelainée", "surcout_prix": 0.00, "est_requis": True, "ordre": 1},
            {"titre": "Plat Faitout Familial 3-4 personnes", "sous_titre": "Grand faitout garni de viande & niébé", "surcout_prix": 4500.00, "est_requis": False, "ordre": 2},
        ],
        "options": [
            {"type_option": OptionProduit.TYPE_SAUCE, "titre": "Sauce Piment Rouge Maison", "sous_titre": "Extra piquante", "surcout_prix": 300.00, "est_inclus": False, "ordre": 1},
            {"type_option": OptionProduit.TYPE_SUPPLEMENT, "titre": "Extra Niébé & Kétiakh", "sous_titre": "Accompagnement haricots & poisson séché", "surcout_prix": 800.00, "est_inclus": False, "ordre": 2},
        ]
    },
    {
        "etablissement_nom": "Saveurs de Ndar",
        "nom": "Mbakhalou Saloum Fait Maison Saint-Louisian au Niébé",
        "description": "Recette mijotée dans la plus pure tradition saint-louisienne : riz au niébé, morceaux de viande juteux et kéthiakh assaisonné d'épices douces et poivre local.",
        "prix_base": 3900.00,
        "image_url": "http://127.0.0.1:8000/media/dishes/mbakhal_ndar.jpg",
        "temps_preparation": "15-20 min",
        "tags": ["Mbakhal Ndar", "Saint-Louis", "Fait Maison", "Niébé"],
        "variantes": [
            {"titre": "Assiette Ndar Standard", "sous_titre": "Portion classique 1 personne", "surcout_prix": 0.00, "est_requis": True, "ordre": 1},
            {"titre": "Assiette XL Saint-Louis", "sous_titre": "Grand format avec supplément viande", "surcout_prix": 1800.00, "est_requis": False, "ordre": 2},
        ],
        "options": [
            {"type_option": OptionProduit.TYPE_SAUCE, "titre": "Citron Pressé Frais", "sous_titre": "Jus de citron vert naturel", "surcout_prix": 100.00, "est_inclus": True, "ordre": 1},
            {"type_option": OptionProduit.TYPE_SUPPLEMENT, "titre": "Supplément Viande Juteuse", "sous_titre": "Morceaux de viande mijotée", "surcout_prix": 1000.00, "est_inclus": False, "ordre": 2},
        ]
    }
]

created_count = 0
for d in MBAKHAL_DISHES:
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
    print(f"OK: Plat Mbakhalou Saloum [{produit.id}] '{produit.nom[:30]}...' cree pour {etab.nom}")

print(f"\nTOTAL PLATS MBAKHALOU SALOUM CREES: {created_count}")
