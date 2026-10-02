import os
import sys
import shutil
import django

sys.path.append('c:\\Users\\HP\\Desktop\\Ayyou-backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.catalog.models import Categorie, Etablissement, Produit, VarianteProduit, OptionProduit

print("==================================================")
print("  POPULATION DES PIZZAS ROYALES (CATEGORIE 14)")
print("==================================================")

# Source images
SOURCE_DIR = r"C:\Users\HP\.gemini\antigravity\brain\1f2cd0a4-e39b-4ef8-b924-e7e0bc2d34a3\.user_uploaded"
DEST_DIR = r"C:\Users\HP\Desktop\Ayyou-backend\media\dishes"

os.makedirs(DEST_DIR, exist_ok=True)

IMAGE_MAPPINGS = {
    "pizza_reine_olives_noires.jpg": "media_1790506804518.jpg",
    "pizza_royale_carton_filante.jpg": "media_1790506815201.jpg",
    "pizza_cheesy_crust_saucisse.jpg": "media_1790506830165.jpg",
    "pizza_suprema_champignons_pepperoni.png": "media_1790506852704.png"
}

for dest_name, src_name in IMAGE_MAPPINGS.items():
    src_path = os.path.join(SOURCE_DIR, src_name)
    dest_path = os.path.join(DEST_DIR, dest_name)
    if os.path.exists(src_path):
        shutil.copy(src_path, dest_path)
        print(f"Copied {src_name} -> {dest_name}")
    else:
        print(f"WARNING: {src_path} not found!")

cat_official = Categorie.objects.get(id=14)
print(f"Categorie officielle: {cat_official.nom} (ID {cat_official.id})")

PIZZA_DISHES = [
    {
        "etablissement_nom": "Dakar Pizza",
        "nom": "Pizza Reine Artisanal Mozzarella, Dinde & Olives Noires",
        "description": "Recette classique Reine italienne cuite sur pierre : sauce tomate cuisinée aux herbes fraîches, mozzarella fior di latte fondante couvrante, jambon de dinde fumé & rondelles d'olives noires.",
        "prix_base": 6500.00,
        "image_url": "http://127.0.0.1:8000/media/dishes/pizza_reine_olives_noires.jpg",
        "temps_preparation": "15-20 min",
        "tags": ["Pizza Reine", "Mozzarella", "Dakar Pizza", "Olives Noires", "Artisanale"],
        "variantes": [
            {"titre": "Taille Moyenne (30cm)", "sous_titre": "Pizza 1 à 2 personnes (6 parts)", "surcout_prix": 0.00, "est_requis": True, "ordre": 1},
            {"titre": "Taille Familiale (40cm)", "sous_titre": "Grande pizza 3 à 4 personnes (8 parts)", "surcout_prix": 3500.00, "est_requis": False, "ordre": 2},
        ],
        "options": [
            {"type_option": OptionProduit.TYPE_SAUCE, "titre": "Huile Pimentée à l’Ail", "sous_titre": "Huile d'olive pimentée", "surcout_prix": 0.00, "est_inclus": True, "ordre": 1},
            {"type_option": OptionProduit.TYPE_SUPPLEMENT, "titre": "Supplément Bordure Fromage (Cheesy Crust)", "sous_titre": "Bord fourré à la mozzarella", "surcout_prix": 1500.00, "est_inclus": False, "ordre": 2},
        ]
    },
    {
        "etablissement_nom": "Pizza Teranga",
        "nom": "Pizza Royale Géante au Fromage Étiré & Boulettes de Bœuf",
        "description": "Généreuse Pizza Royale préparée à la commande : pâte levée aérée, sauce tomate relevée, mozzarella fondante ultra-filante, boulettes de viande bœuf, poivrons doux & olives.",
        "prix_base": 7000.00,
        "image_url": "http://127.0.0.1:8000/media/dishes/pizza_royale_carton_filante.jpg",
        "temps_preparation": "15-20 min",
        "tags": ["Pizza Royale", "Pizza Teranga", "Boulettes Bœuf", "Fromage Filant", "Géante"],
        "variantes": [
            {"titre": "Pizza Royale Medium 32cm", "sous_titre": "Pour 2 personnes", "surcout_prix": 0.00, "est_requis": True, "ordre": 1},
            {"titre": "Pizza Royale XXL 42cm", "sous_titre": "Grand format géant familial", "surcout_prix": 4000.00, "est_requis": False, "ordre": 2},
        ],
        "options": [
            {"type_option": OptionProduit.TYPE_SAUCE, "titre": "Sauce Barbecue Nappage", "sous_titre": "Sauce BBQ sur le fromage", "surcout_prix": 200.00, "est_inclus": False, "ordre": 1},
            {"type_option": OptionProduit.TYPE_SUPPLEMENT, "titre": "Extra Champignons Frais", "sous_titre": "Champignons sautés", "surcout_prix": 800.00, "est_inclus": False, "ordre": 2},
        ]
    },
    {
        "etablissement_nom": "Pizza Chez Marième",
        "nom": "Pizza Cheesy Crust Bordure Saucisse & Mozzarella Extrême",
        "description": "La spécialité gourmande de Marième : croûte dorée généreusement fourrée de saucisses de volaille fumées, nappage mozzarella extrême fondu & morceaux de bœuf rôti.",
        "prix_base": 7500.00,
        "image_url": "http://127.0.0.1:8000/media/dishes/pizza_cheesy_crust_saucisse.jpg",
        "temps_preparation": "20-25 min",
        "tags": ["Cheesy Crust", "Saucisse", "Chez Marième", "Mozzarella Extrême", "Gourmet"],
        "variantes": [
            {"titre": "Medium Bordure Saucisse 30cm", "sous_titre": "Cheesy crust saucisse 2 personnes", "surcout_prix": 0.00, "est_requis": True, "ordre": 1},
            {"titre": "Large Bordure Saucisse 40cm", "sous_titre": "Format XXL pour 3-4 personnes", "surcout_prix": 4500.00, "est_requis": False, "ordre": 2},
        ],
        "options": [
            {"type_option": OptionProduit.TYPE_SAUCE, "titre": "Sauce Blanche Aillée Dip", "sous_titre": "Pour tremper les croûtes", "surcout_prix": 300.00, "est_inclus": True, "ordre": 1},
            {"type_option": OptionProduit.TYPE_SUPPLEMENT, "titre": "Extra Double Fromage Mozzarella", "sous_titre": "Double portion de fromage", "surcout_prix": 1200.00, "est_inclus": False, "ordre": 2},
        ]
    },
    {
        "etablissement_nom": "Urban Food Dakar",
        "nom": "Pizza Suprema Pepperoni, Champignons & Viande Hachée",
        "description": "Pizza américaine Suprema garnie à rabord : pepperoni piquant croquant, champignons de Paris frais coupés en lamelles, viande hachée assaisonnée & poivrons verts.",
        "prix_base": 6800.00,
        "image_url": "http://127.0.0.1:8000/media/dishes/pizza_suprema_champignons_pepperoni.png",
        "temps_preparation": "15-20 min",
        "tags": ["Pizza Suprema", "Pepperoni", "Champignons", "Urban Food", "Americaine"],
        "variantes": [
            {"titre": "Suprema Medium 30cm", "sous_titre": "Pepperoni & champignons 1-2 personnes", "surcout_prix": 0.00, "est_requis": True, "ordre": 1},
            {"titre": "Suprema Large 40cm", "sous_titre": "Format géant américain", "surcout_prix": 3800.00, "est_requis": False, "ordre": 2},
        ],
        "options": [
            {"type_option": OptionProduit.TYPE_SAUCE, "titre": "Sauce Piment Rouge Fort", "sous_titre": "Sauce pimentée mexicaine", "surcout_prix": 200.00, "est_inclus": False, "ordre": 1},
            {"type_option": OptionProduit.TYPE_SUPPLEMENT, "titre": "Extra Rondelles de Pepperoni", "sous_titre": "Supplément pepperoni grillé", "surcout_prix": 1000.00, "est_inclus": False, "ordre": 2},
        ]
    }
]

created_count = 0
for d in PIZZA_DISHES:
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
    print(f"OK: Plat Pizza Royale [{produit.id}] '{produit.nom[:30]}...' cree pour {etab.nom}")

print(f"\nTOTAL PLATS PIZZA ROYALE CREES: {created_count}")
