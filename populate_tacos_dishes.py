import os
import sys
import shutil
import django

sys.path.append('c:\\Users\\HP\\Desktop\\Ayyou-backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.catalog.models import Categorie, Etablissement, Produit, VarianteProduit, OptionProduit

print("==================================================")
print("  POPULATION DES TACOS FRANCAIS (CATEGORIE 2)")
print("==================================================")

# Source images
SOURCE_DIR = r"C:\Users\HP\.gemini\antigravity\brain\1f2cd0a4-e39b-4ef8-b924-e7e0bc2d34a3\.user_uploaded"
DEST_DIR = r"C:\Users\HP\Desktop\Ayyou-backend\media\dishes"

os.makedirs(DEST_DIR, exist_ok=True)

IMAGE_MAPPINGS = {
    "tacos_viande_hachee_sauce_fromagere.png": "media_1790506322325.png",
    "tacos_poulet_sauce_blanche.jpg": "media_1790506341273.jpg",
    "tacos_viande_fromage_etire.jpg": "media_1790506357629.jpg",
    "tacos_trio_poulet_fromage.jpg": "media_1790506394279.jpg"
}

for dest_name, src_name in IMAGE_MAPPINGS.items():
    src_path = os.path.join(SOURCE_DIR, src_name)
    dest_path = os.path.join(DEST_DIR, dest_name)
    if os.path.exists(src_path):
        shutil.copy(src_path, dest_path)
        print(f"Copied {src_name} -> {dest_name}")
    else:
        print(f"WARNING: {src_path} not found!")

cat_official = Categorie.objects.get(id=2)
print(f"Categorie officielle: {cat_official.nom} (ID {cat_official.id})")

TACOS_DISHES = [
    {
        "etablissement_nom": "Dakar Fast",
        "nom": "French Tacos Double Viande Hachée & Sauce Fromagère Maison",
        "description": "Véritable French Tacos garni de viande hachée pur bœuf braisée, frites croustillantes à l'intérieur, nappé de notre légendaire sauce fromagère crémeuse maison et toasté à la presse.",
        "prix_base": 4800.00,
        "image_url": "http://127.0.0.1:8000/media/dishes/tacos_viande_hachee_sauce_fromagere.png",
        "temps_preparation": "10-15 min",
        "tags": ["French Tacos", "Double Viande", "Sauce Fromagère", "Dakar Fast", "Frites"],
        "variantes": [
            {"titre": "Tacos L (Double Viande Bœuf)", "sous_titre": "2 portions de viande bœuf, frites & sauce fromagère", "surcout_prix": 0.00, "est_requis": True, "ordre": 1},
            {"titre": "Tacos XL (Triple Viande + Boisson)", "sous_titre": "3 viandes au choix & canette 33cl", "surcout_prix": 1700.00, "est_requis": False, "ordre": 2},
        ],
        "options": [
            {"type_option": OptionProduit.TYPE_SAUCE, "titre": "Sauce Algérienne & Fromagère", "sous_titre": "Nappage double sauce", "surcout_prix": 200.00, "est_inclus": True, "ordre": 1},
            {"type_option": OptionProduit.TYPE_SUPPLEMENT, "titre": "Gratinage Fromage Emmental", "sous_titre": "Fromage gratiné sur le dessus", "surcout_prix": 500.00, "est_inclus": False, "ordre": 2},
        ]
    },
    {
        "etablissement_nom": "Urban Food Dakar",
        "nom": "Tacos Poulet Mariné Juteux & Sauce Creamy Blanche",
        "description": "Tortilla de blé dorée fourrée de morceaux de poulet mariné aux épices douces, salade frisée, frites dorées et coulée généreuse de sauce creamy blanche crémeuse.",
        "prix_base": 4500.00,
        "image_url": "http://127.0.0.1:8000/media/dishes/tacos_poulet_sauce_blanche.jpg",
        "temps_preparation": "10-15 min",
        "tags": ["Tacos Poulet", "Urban Food", "Sauce Blanche", "Creamy", "Tortilla"],
        "variantes": [
            {"titre": "Tacos Poulet L Standard", "sous_titre": "Poulet mariné & sauce blanche", "surcout_prix": 0.00, "est_requis": True, "ordre": 1},
            {"titre": "Tacos Mixte XL Poulet & Viande Hachée", "sous_titre": "Double viande poulet + bœuf haché", "surcout_prix": 1500.00, "est_requis": False, "ordre": 2},
        ],
        "options": [
            {"type_option": OptionProduit.TYPE_SAUCE, "titre": "Sauce Samouraï Épicée", "sous_titre": "Sauce pimentée", "surcout_prix": 200.00, "est_inclus": False, "ordre": 1},
            {"type_option": OptionProduit.TYPE_SUPPLEMENT, "titre": "Extra Cheddar Fondu", "sous_titre": "Fromage cheddar fondu", "surcout_prix": 400.00, "est_inclus": False, "ordre": 2},
        ]
    },
    {
        "etablissement_nom": "Snack Teranga",
        "nom": "Tacos Gourmet Viande Braisée & Mozzarella Étirée au Four",
        "description": "Tacos géant cuit au four avec cœur fondant de mozzarella étirée, dés de viande bovine braisée aux petits légumes croquants, poivrons rouges & sauce fromagère onctueuse.",
        "prix_base": 5200.00,
        "image_url": "http://127.0.0.1:8000/media/dishes/tacos_viande_fromage_etire.jpg",
        "temps_preparation": "15-20 min",
        "tags": ["Tacos Gourmet", "Mozzarella Étirée", "Viande Braisée", "Snack Teranga"],
        "variantes": [
            {"titre": "Tacos Gourmet Mozzarella L", "sous_titre": "Viande braisée & fromage étiré", "surcout_prix": 0.00, "est_requis": True, "ordre": 1},
            {"titre": "Tacos XXL 3 Viandes & Double Fromage", "sous_titre": "Format géant gourmand", "surcout_prix": 2000.00, "est_requis": False, "ordre": 2},
        ],
        "options": [
            {"type_option": OptionProduit.TYPE_SAUCE, "titre": "Sauce BBQ & Fromagère", "sous_titre": "Mélange barbecue-fromage", "surcout_prix": 200.00, "est_inclus": True, "ordre": 1},
            {"type_option": OptionProduit.TYPE_SUPPLEMENT, "titre": "Extra Bacon & Jalapeños", "sous_titre": "Piments doux jalapeños & bacon", "surcout_prix": 600.00, "est_inclus": False, "ordre": 2},
        ]
    },
    {
        "etablissement_nom": "Fast Chez Awa",
        "nom": "Trio de Mini-Tacos Dorés au Poulet Effiloché & Fromage",
        "description": "Formule originale à partager : trois rouleaux de mini-tacos dorés et croustillants garnis de poulet effiloché, fromage cheddar fondu, servis avec ramequin de dip sauce blanche.",
        "prix_base": 4200.00,
        "image_url": "http://127.0.0.1:8000/media/dishes/tacos_trio_poulet_fromage.jpg",
        "temps_preparation": "10-15 min",
        "tags": ["Trio Tacos", "Fast Chez Awa", "Poulet Effiloché", "Dip Sauce", "Partager"],
        "variantes": [
            {"titre": "Assiette Trio 3 Mini-Tacos", "sous_titre": "3 mini tacos dorés & sauce dip", "surcout_prix": 0.00, "est_requis": True, "ordre": 1},
            {"titre": "Plateau Party 6 Mini-Tacos", "sous_titre": "6 mini tacos pour 2-3 personnes", "surcout_prix": 3800.00, "est_requis": False, "ordre": 2},
        ],
        "options": [
            {"type_option": OptionProduit.TYPE_SAUCE, "titre": "Sauce Dip Guacamole & Fromagère", "sous_titre": "Sauce spéciale dip", "surcout_prix": 300.00, "est_inclus": True, "ordre": 1},
            {"type_option": OptionProduit.TYPE_SUPPLEMENT, "titre": "Portion Frites de Sweet Potato", "sous_titre": "Frites patate douce", "surcout_prix": 800.00, "est_inclus": False, "ordre": 2},
        ]
    }
]

created_count = 0
for d in TACOS_DISHES:
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
    print(f"OK: Plat Tacos Français [{produit.id}] '{produit.nom[:30]}...' cree pour {etab.nom}")

print(f"\nTOTAL PLATS TACOS FRANCAIS CREES: {created_count}")
