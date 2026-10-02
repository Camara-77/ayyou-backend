import os
import sys
import shutil
import django

sys.path.append('c:\\Users\\HP\\Desktop\\Ayyou-backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.catalog.models import Categorie, Etablissement, Produit, VarianteProduit, OptionProduit

print("==================================================")
print("  POPULATION DES BURGERS GOURMET (CATEGORIE 2)")
print("==================================================")

# Source images
SOURCE_DIR = r"C:\Users\HP\.gemini\antigravity\brain\1f2cd0a4-e39b-4ef8-b924-e7e0bc2d34a3\.user_uploaded"
DEST_DIR = r"C:\Users\HP\Desktop\Ayyou-backend\media\dishes"

os.makedirs(DEST_DIR, exist_ok=True)

IMAGE_MAPPINGS = {
    "burger_double_smash_cheddar.jpg": "media_1790505651131.jpg",
    "burger_double_sesame_frites.jpg": "media_1790505665831.jpg",
    "burger_gourmet_classic_cola.png": "media_1790505698114.png",
    "burger_duo_panier_frites.png": "media_1790505717742.png"
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

BURGER_DISHES = [
    {
        "etablissement_nom": "Dakar Fast",
        "nom": "Double Smash Cheeseburger Pur Bœuf & Cheddar Coulant",
        "description": "Double steak haché pur bœuf de 150g snaké façon Smash Burger, double tranche de véritable cheddar américain fondu coulant, sauce spéciale Dakar Fast, pickles et frites fraîches croustillantes.",
        "prix_base": 4500.00,
        "image_url": "http://127.0.0.1:8000/media/dishes/burger_double_smash_cheddar.jpg",
        "temps_preparation": "10-15 min",
        "tags": ["Smash Burger", "Double Cheeseburger", "Dakar Fast", "Frites", "Pur Bœuf"],
        "variantes": [
            {"titre": "Menu Double Smash + Frites", "sous_titre": "Double steak 150g, cheddar & frites maison", "surcout_prix": 0.00, "est_requis": True, "ordre": 1},
            {"titre": "Menu Triple Smash XL + Boisson", "sous_titre": "Triple steak, triple fromage & canette 33cl", "surcout_prix": 1800.00, "est_requis": False, "ordre": 2},
        ],
        "options": [
            {"type_option": OptionProduit.TYPE_SUPPLEMENT, "titre": "Supplément Bacon Grillé (x2)", "sous_titre": "Bacon de dinde croustillant", "surcout_prix": 500.00, "est_inclus": False, "ordre": 1},
            {"type_option": OptionProduit.TYPE_SAUCE, "titre": "Sauce Burger Maison Dakar Fast", "sous_titre": "Sauce piquante fumée", "surcout_prix": 200.00, "est_inclus": True, "ordre": 2},
        ]
    },
    {
        "etablissement_nom": "Urban Food Dakar",
        "nom": "Double Cheeseburger Buns Sésame & Salade Craquante",
        "description": "Pain brioché aux graines de sésame doré au beurre, deux steaks hachés juteux grillés à la flamme, tranches de cheddar fondant, sauce ketchup/mayo classique, salade verte & frites dorées.",
        "prix_base": 4200.00,
        "image_url": "http://127.0.0.1:8000/media/dishes/burger_double_sesame_frites.jpg",
        "temps_preparation": "10-15 min",
        "tags": ["Urban Food", "Double Cheese", "Sésame", "Ketchup", "Frites"],
        "variantes": [
            {"titre": "Menu Cheeseburger Sésame Standard", "sous_titre": "Double steak sésame & barquette frites", "surcout_prix": 0.00, "est_requis": True, "ordre": 1},
            {"titre": "Formule Urban Max + Boisson 50cl", "sous_titre": "Burger, frites & boisson fraîche", "surcout_prix": 1200.00, "est_requis": False, "ordre": 2},
        ],
        "options": [
            {"type_option": OptionProduit.TYPE_SUPPLEMENT, "titre": "Supplément Œuf au Plat", "sous_titre": "Œuf coulant sur le steak", "surcout_prix": 400.00, "est_inclus": False, "ordre": 1},
            {"type_option": OptionProduit.TYPE_SAUCE, "titre": "Sauce Algérienne Épicée", "sous_titre": "Sauce piquante aux oignons", "surcout_prix": 200.00, "est_inclus": False, "ordre": 2},
        ]
    },
    {
        "etablissement_nom": "Snack Teranga",
        "nom": "Classic Cheeseburger Gourmet sur Planche & Cola Glacé",
        "description": "Steak haché gourmet assaisonné au poivre moulu, tranche de cheddar fondant, tomate fraîche, salade frisée et sauce teranga crémeuse sur planche de bois. Servi avec frites & verre de soda.",
        "prix_base": 3900.00,
        "image_url": "http://127.0.0.1:8000/media/dishes/burger_gourmet_classic_cola.png",
        "temps_preparation": "10-15 min",
        "tags": ["Snack Teranga", "Classic Cheese", "Menu Burger", "Cola Glacé", "Gourmet"],
        "variantes": [
            {"titre": "Menu Classic Teranga", "sous_titre": "Cheeseburger gourmet, frites & soda", "surcout_prix": 0.00, "est_requis": True, "ordre": 1},
            {"titre": "Menu Double Teranga Cheese", "sous_titre": "Double steak haché & frites géantes", "surcout_prix": 1500.00, "est_requis": False, "ordre": 2},
        ],
        "options": [
            {"type_option": OptionProduit.TYPE_SUPPLEMENT, "titre": "Supplément Oignons Caramélisés", "sous_titre": "Oignons confits doux", "surcout_prix": 300.00, "est_inclus": False, "ordre": 1},
            {"type_option": OptionProduit.TYPE_SAUCE, "titre": "Sauce Samouraï", "sous_titre": "Sauce forte pimentée", "surcout_prix": 200.00, "est_inclus": False, "ordre": 2},
        ]
    },
    {
        "etablissement_nom": "Fast Chez Awa",
        "nom": "Duo de Cheeseburgers Artisanaux au Panier Métal de Frites",
        "description": "Formule duo irrésistible : deux burgers artisanaux généreusement garnis de steak bœuf grillé, cheddar râpé fondu, sauce blanche ail-fines herbes, présentés avec panier à frites en métal et jus d'orange.",
        "prix_base": 5000.00,
        "image_url": "http://127.0.0.1:8000/media/dishes/burger_duo_panier_frites.png",
        "temps_preparation": "15-20 min",
        "tags": ["Fast Chez Awa", "Duo Burgers", "Panier Frites", "Jus Orange", "Artisanal"],
        "variantes": [
            {"titre": "Pack Duo 2 Cheeseburgers", "sous_titre": "2 burgers + panier métal frites", "surcout_prix": 0.00, "est_requis": True, "ordre": 1},
            {"titre": "Pack Duo XL avec 2 Boissons", "sous_titre": "2 burgers, frites & 2 canettes 33cl", "surcout_prix": 1600.00, "est_requis": False, "ordre": 2},
        ],
        "options": [
            {"type_option": OptionProduit.TYPE_SAUCE, "titre": "Sauce Blanche Ail & Fines Herbes", "sous_titre": "Sauce fraîcheur maison", "surcout_prix": 150.00, "est_inclus": True, "ordre": 1},
            {"type_option": OptionProduit.TYPE_SUPPLEMENT, "titre": "Frites de Sweet Potato", "sous_titre": "Patate douce frite", "surcout_prix": 500.00, "est_inclus": False, "ordre": 2},
        ]
    }
]

created_count = 0
for d in BURGER_DISHES:
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
    print(f"OK: Plat Burger Gourmet [{produit.id}] '{produit.nom[:30]}...' cree pour {etab.nom}")

print(f"\nTOTAL PLATS BURGERS GOURMET CREES: {created_count}")
