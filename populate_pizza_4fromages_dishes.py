import os
import sys
import shutil
import django

sys.path.append('c:\\Users\\HP\\Desktop\\Ayyou-backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.catalog.models import Categorie, Etablissement, Produit, VarianteProduit, OptionProduit

print("==================================================")
print("  POPULATION DES PIZZAS 4 FROMAGES (CATEGORIE 14)")
print("==================================================")

# Source images
SOURCE_DIR = r"C:\Users\HP\.gemini\antigravity\brain\1f2cd0a4-e39b-4ef8-b924-e7e0bc2d34a3\.user_uploaded"
DEST_DIR = r"C:\Users\HP\Desktop\Ayyou-backend\media\dishes"

os.makedirs(DEST_DIR, exist_ok=True)

IMAGE_MAPPINGS = {
    "pizza_4_fromages_blanche.jpg": "media_1790507194708.jpg",
    "pizza_4_fromages_tomate_basilic.jpg": "media_1790507216964.jpg",
    "pizza_4_fromages_napolitaine_basilic.jpg": "media_1790507234871.jpg",
    "pizza_4_fromages_origan_planche.jpg": "media_1790507250942.jpg"
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

PIZZA_4FROMAGES_DISHES = [
    {
        "etablissement_nom": "Dakar Pizza",
        "nom": "Pizza 4 Fromages Blanche Gourmet (Mozzarella, Gorgonzola, Chèvre & Ricotta)",
        "description": "L'excellence des fromages italiens sur base crème fraîche : alliance subtile de Mozzarella fior di latte, Gorgonzola D.O.P., bûche de Chèvre affinée & quenelles de Ricotta onctueuse.",
        "prix_base": 7000.00,
        "image_url": "http://127.0.0.1:8000/media/dishes/pizza_4_fromages_blanche.jpg",
        "temps_preparation": "15-20 min",
        "tags": ["Pizza 4 Fromages", "Crème Blanche", "Gorgonzola", "Dakar Pizza", "Chèvre"],
        "variantes": [
            {"titre": "Taille Moyenne (30cm)", "sous_titre": "4 fromages crème 1-2 personnes", "surcout_prix": 0.00, "est_requis": True, "ordre": 1},
            {"titre": "Taille Familiale (40cm)", "sous_titre": "Grand format 4 fromages crème 3-4 personnes", "surcout_prix": 3800.00, "est_requis": False, "ordre": 2},
        ],
        "options": [
            {"type_option": OptionProduit.TYPE_SUPPLEMENT, "titre": "Filet de Miel Bio", "sous_titre": "Pour le fromage de chèvre", "surcout_prix": 300.00, "est_inclus": False, "ordre": 1},
            {"type_option": OptionProduit.TYPE_SAUCE, "titre": "Huile d'Olive Épicée", "sous_titre": "Huile pimentée maison", "surcout_prix": 0.00, "est_inclus": True, "ordre": 2},
        ]
    },
    {
        "etablissement_nom": "Pizza Teranga",
        "nom": "Pizza 4 Fromages Rouge aux Tomates Fraîches & Basilic",
        "description": "Fusion parfaite entre sauce tomate italienne et 4 fromages fondants (Mozzarella, Emmental, Parmesan râpé & Gorgonzola), garnie de rondelles de tomates fraîches & basilic.",
        "prix_base": 6800.00,
        "image_url": "http://127.0.0.1:8000/media/dishes/pizza_4_fromages_tomate_basilic.jpg",
        "temps_preparation": "15-20 min",
        "tags": ["Pizza Teranga", "4 Fromages Rouge", "Basilic", "Tomate Fraîche"],
        "variantes": [
            {"titre": "Medium 30cm", "sous_titre": "4 Fromages rouge & basilic", "surcout_prix": 0.00, "est_requis": True, "ordre": 1},
            {"titre": "Large 40cm", "sous_titre": "Format XXL familial 8 parts", "surcout_prix": 3500.00, "est_requis": False, "ordre": 2},
        ],
        "options": [
            {"type_option": OptionProduit.TYPE_SUPPLEMENT, "titre": "Extra Mozzarella Di Bufala", "sous_titre": "Mozzarella de bufflonne fraîche", "surcout_prix": 1000.00, "est_inclus": False, "ordre": 1},
            {"type_option": OptionProduit.TYPE_SAUCE, "titre": "Pesto de Basilic Frais", "sous_titre": "Nappage sauce pesto vert", "surcout_prix": 200.00, "est_inclus": False, "ordre": 2},
        ]
    },
    {
        "etablissement_nom": "Pizza Chez Marième",
        "nom": "Pizza Napolitaine 4 Fromages Croûte Alvéolée & Basilic",
        "description": "Pâte à pizza napolitaine maturée 48h aux bords alvéolés et alvéoles dorées au feu de bois : coulis de tomates pelées, mélange 4 fromages coulant & feuilles de basilic frais.",
        "prix_base": 7200.00,
        "image_url": "http://127.0.0.1:8000/media/dishes/pizza_4_fromages_napolitaine_basilic.jpg",
        "temps_preparation": "15-20 min",
        "tags": ["Napolitaine", "Pâte Maturée", "Chez Marième", "4 Fromages", "Feu de Bois"],
        "variantes": [
            {"titre": "Pizzetta Napolitaine 30cm", "sous_titre": "Pâte artisanale maturée 48h", "surcout_prix": 0.00, "est_requis": True, "ordre": 1},
            {"titre": "Grande Napolitaine 40cm", "sous_titre": "Format 3-4 personnes", "surcout_prix": 4000.00, "est_requis": False, "ordre": 2},
        ],
        "options": [
            {"type_option": OptionProduit.TYPE_SAUCE, "titre": "Sauce Piment Fort Napolitaine", "sous_titre": "Sauce piquante", "surcout_prix": 200.00, "est_inclus": True, "ordre": 1},
            {"type_option": OptionProduit.TYPE_SUPPLEMENT, "titre": "Bordure Cheesy Mozzarella", "sous_titre": "Bord fourré fromage", "surcout_prix": 1500.00, "est_inclus": False, "ordre": 2},
        ]
    },
    {
        "etablissement_nom": "Urban Food Dakar",
        "nom": "Pizza Quattro Formaggi à l'Origan & Huile d'Olive",
        "description": "Recette Quattro Formaggi découpée sur planche en bois : sauce tomate mijotée aromatisée à l'origan séché, Mozzarella, Chèvre, Emmental & Parmesan gratiné au four.",
        "prix_base": 6500.00,
        "image_url": "http://127.0.0.1:8000/media/dishes/pizza_4_fromages_origan_planche.jpg",
        "temps_preparation": "15-20 min",
        "tags": ["Quattro Formaggi", "Urban Food", "Origan", "Gratiné", "Planche"],
        "variantes": [
            {"titre": "Quattro Formaggi Medium 30cm", "sous_titre": "4 fromages gratinés à l'origan", "surcout_prix": 0.00, "est_requis": True, "ordre": 1},
            {"titre": "Quattro Formaggi Large 40cm", "sous_titre": "Format géant à partager", "surcout_prix": 3500.00, "est_requis": False, "ordre": 2},
        ],
        "options": [
            {"type_option": OptionProduit.TYPE_SUPPLEMENT, "titre": "Supplément Gorgonzola Extra", "sous_titre": "Fromage bleu gorgonzola", "surcout_prix": 800.00, "est_inclus": False, "ordre": 1},
            {"type_option": OptionProduit.TYPE_SAUCE, "titre": "Huile d'Ail & Romarin", "sous_titre": "Assaisonnement parfum ail", "surcout_prix": 150.00, "est_inclus": True, "ordre": 2},
        ]
    }
]

created_count = 0
for d in PIZZA_4FROMAGES_DISHES:
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
    print(f"OK: Plat Pizza 4 Fromages [{produit.id}] '{produit.nom[:30]}...' cree pour {etab.nom}")

print(f"\nTOTAL PLATS PIZZA 4 FROMAGES CREES: {created_count}")
