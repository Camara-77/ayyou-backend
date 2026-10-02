import os
import sys
import shutil
import django

sys.path.append('c:\\Users\\HP\\Desktop\\Ayyou-backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.catalog.models import Categorie, Etablissement, Produit, VarianteProduit, OptionProduit

print("==================================================")
print("  POPULATION DES VIENNOISERIES & PATISSERIES (CATEGORIE 15/16)")
print("==================================================")

# Source images
SOURCE_DIR = r"C:\Users\HP\.gemini\antigravity\brain\1f2cd0a4-e39b-4ef8-b924-e7e0bc2d34a3\.user_uploaded"
DEST_DIR = r"C:\Users\HP\Desktop\Ayyou-backend\media\dishes"

os.makedirs(DEST_DIR, exist_ok=True)

IMAGE_MAPPINGS = {
    "pain_au_chocolat_feuillete.png": "media_1790510012563.png",
    "croissant_fourre_chocolat.jpg": "media_1790510025060.jpg",
    "beignet_fourre_creme_patissiere.jpg": "media_1790510041998.jpg",
    "pancakes_fluffy_sirop_erable.jpg": "media_1790510062269.jpg"
}

for dest_name, src_name in IMAGE_MAPPINGS.items():
    src_path = os.path.join(SOURCE_DIR, src_name)
    dest_path = os.path.join(DEST_DIR, dest_name)
    if os.path.exists(src_path):
        shutil.copy(src_path, dest_path)
        print(f"Copied {src_name} -> {dest_name}")
    else:
        print(f"WARNING: {src_path} not found!")

cat_boulangerie = Categorie.objects.get(id=15)
cat_patisserie = Categorie.objects.get(id=16)

BOULANGERIE_DISHES = [
    {
        "etablissement_nom": "Boulangerie Teranga",
        "nom": "Lot de Pains au Chocolat Feuilletés Pur Beurre AOP",
        "description": "Viennoiseries pur beurre AOP fabriquées chaque matin par nos maîtres boulangers : feuilletage croustillant et doré à souhait, fourré de deux barres généreuses de chocolat Valrhona.",
        "prix_base": 1500.00,
        "image_url": "http://127.0.0.1:8000/media/dishes/pain_au_chocolat_feuillete.png",
        "temps_preparation": "05 min",
        "tags": ["Pain au Chocolat", "Viennoiserie", "Boulangerie Teranga", "Pur Beurre", "Frais"],
        "categorie": cat_boulangerie,
        "variantes": [
            {"titre": "Lot de 2 Pains au Chocolat", "sous_titre": "2 viennoiseries feuilletées au chocolat", "surcout_prix": 0.00, "est_requis": True, "ordre": 1},
            {"titre": "Pack Matin 5 Pains au Chocolat", "sous_titre": "Pack familial 5 pièces", "surcout_prix": 2000.00, "est_requis": False, "ordre": 2},
        ],
        "options": [
            {"type_option": OptionProduit.TYPE_SUPPLEMENT, "titre": "Option Chauffé au Four", "sous_titre": "Servi chaud croustillant", "surcout_prix": 0.00, "est_inclus": True, "ordre": 1},
        ]
    },
    {
        "etablissement_nom": "Au Bon Pain Dakar",
        "nom": "Croissants Feuilletés au Beurre & Nappage Chocolat Coulant",
        "description": "Croissants dorés au feuilletage alvéolé d'exception, fourrés d'une crème onctueuse au chocolat gianduja et saupoudrés d'un voile de sucre glace.",
        "prix_base": 1800.00,
        "image_url": "http://127.0.0.1:8000/media/dishes/croissant_fourre_chocolat.jpg",
        "temps_preparation": "05 min",
        "tags": ["Croissant Chocolat", "Au Bon Pain", "Feuilleté", "Gianduja", "Gourmet"],
        "categorie": cat_boulangerie,
        "variantes": [
            {"titre": "Duo de Croissants Chocolat", "sous_titre": "2 croissants fourrés chocolat", "surcout_prix": 0.00, "est_requis": True, "ordre": 1},
            {"titre": "Boîte de 4 Croissants", "sous_titre": "Boîte fraîcheur 4 pièces", "surcout_prix": 1600.00, "est_requis": False, "ordre": 2},
        ],
        "options": [
            {"type_option": OptionProduit.TYPE_SUPPLEMENT, "titre": "Café Allongé / Espresso Offert", "sous_titre": "Café chaud du matin", "surcout_prix": 500.00, "est_inclus": False, "ordre": 1},
        ]
    },
    {
        "etablissement_nom": "Pain & Délices",
        "nom": "Beignets Soufflés Boules de Berlin à la Crème Pâtissière",
        "description": "Beignets briochés moelleux et aérés saupoudrés de sucre glace, généreusement fourrés à cœur d'une onctueuse crème pâtissière à la vanille Bourbon.",
        "prix_base": 2000.00,
        "image_url": "http://127.0.0.1:8000/media/dishes/beignet_fourre_creme_patissiere.jpg",
        "temps_preparation": "05 min",
        "tags": ["Beignets Berlin", "Pain & Délices", "Crème Pâtissière", "Moelleux", "Sucre Glace"],
        "categorie": cat_patisserie,
        "variantes": [
            {"titre": "Boîte de 3 Beignets Crème", "sous_titre": "3 beignets fourrés crème pâtissière", "surcout_prix": 0.00, "est_requis": True, "ordre": 1},
            {"titre": "Coffret 6 Beignets Assortis", "sous_titre": "6 beignets (crème & chocolat)", "surcout_prix": 1800.00, "est_requis": False, "ordre": 2},
        ],
        "options": [
            {"type_option": OptionProduit.TYPE_SUPPLEMENT, "titre": "Extra Coulis Chocolat", "sous_titre": "Nappage chocolat", "surcout_prix": 200.00, "est_inclus": False, "ordre": 1},
        ]
    },
    {
        "etablissement_nom": "Douceurs de Dakar",
        "nom": "Soufflé Pancakes Fluffy Japonaise & Sirop d'Érable",
        "description": "Pancakes soufflés japonais d'une légèreté et d'un moelleux exceptionnels, saupoudrés de sucre vanillé et nappés d'un filet de pur sirop d'érable du Canada.",
        "prix_base": 2500.00,
        "image_url": "http://127.0.0.1:8000/media/dishes/pancakes_fluffy_sirop_erable.jpg",
        "temps_preparation": "10-15 min",
        "tags": ["Fluffy Pancakes", "Soufflé", "Sirop d'Érable", "Douceurs de Dakar", "Pâtisserie"],
        "categorie": cat_patisserie,
        "variantes": [
            {"titre": "Pile de 3 Fluffy Pancakes", "sous_titre": "3 pancakes soufflés au sirop d'érable", "surcout_prix": 0.00, "est_requis": True, "ordre": 1},
            {"titre": "Pile XXL 5 Fluffy Pancakes + Beurre", "sous_titre": "5 pancakes avec noisette de beurre", "surcout_prix": 1500.00, "est_requis": False, "ordre": 2},
        ],
        "options": [
            {"type_option": OptionProduit.TYPE_SUPPLEMENT, "titre": "Noisette de Beurre Doux", "sous_titre": "Beurre fondu", "surcout_prix": 100.00, "est_inclus": True, "ordre": 1},
            {"type_option": OptionProduit.TYPE_SUPPLEMENT, "titre": "Extra Fraises Fraîches", "sous_titre": "Fraises fraîches tranchées", "surcout_prix": 300.00, "est_inclus": False, "ordre": 2},
        ]
    }
]

created_count = 0
for d in BOULANGERIE_DISHES:
    etab = Etablissement.objects.filter(nom__icontains=d["etablissement_nom"]).first()
    if not etab:
        print(f"Etablissement '{d['etablissement_nom']}' non trouve dans la BD.")
        continue
    
    produit, _ = Produit.objects.update_or_create(
        etablissement=etab,
        nom=d["nom"],
        defaults={
            "categorie": d["categorie"],
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
    print(f"OK: Produit Boulangerie/Pâtisserie [{produit.id}] '{produit.nom[:30]}...' cree pour {etab.nom}")

print(f"\nTOTAL PRODUITS BOULANGERIE/PATISSERIE CREES: {created_count}")
