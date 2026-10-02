import os
import sys
import shutil
import django

sys.path.append('c:\\Users\\HP\\Desktop\\Ayyou-backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.catalog.models import Categorie, Etablissement, Produit, VarianteProduit, OptionProduit

print("==================================================")
print("  POPULATION DES PLATS DIBI AGNEAU (DIBITERIE & GRILLADES)")
print("==================================================")

# Source images
SOURCE_DIR = r"C:\Users\HP\.gemini\antigravity\brain\1f2cd0a4-e39b-4ef8-b924-e7e0bc2d34a3\.user_uploaded"
DEST_DIR = r"C:\Users\HP\Desktop\Ayyou-backend\media\dishes"

os.makedirs(DEST_DIR, exist_ok=True)

IMAGE_MAPPINGS = {
    "dibi_agneau_dibi_dakar.jpg": "media_1790475588948.jpg",
    "dibi_agneau_chez_samba.png": "media_1790475599445.png",
    "dibi_agneau_grill_sahel.jpg": "media_1790475611929.jpg",
    "dibi_agneau_teranga.jpg": "media_1790475628395.jpg"
}

for dest_name, src_name in IMAGE_MAPPINGS.items():
    src_path = os.path.join(SOURCE_DIR, src_name)
    dest_path = os.path.join(DEST_DIR, dest_name)
    if os.path.exists(src_path):
        shutil.copy(src_path, dest_path)
        print(f"Copied {src_name} -> {dest_name}")
    else:
        print(f"WARNING: {src_path} not found!")

cat_official = Categorie.objects.get(id=9)
print(f"Categorie officielle: {cat_official.nom} (ID {cat_official.id})")

DIBI_AGNEAU_DISHES = [
    {
        "etablissement_nom": "Dibi Dakar",
        "nom": "Dibi Agneau Haoussa au Feu de Bois & Piment Poudre",
        "description": "Véritable Dibi d'agneau braisé à l'étouffée sur papier kraft : viande d'agneau de choix découpée en côtelettes fondantes, saupoudrée de piment sec Haoussa (Kankankan) et garnie d'oignons émincés.",
        "prix_base": 5500.00,
        "image_url": "http://127.0.0.1:8000/media/dishes/dibi_agneau_dibi_dakar.jpg",
        "temps_preparation": "20-25 min",
        "tags": ["Dibi Agneau", "Feu de Bois", "Haoussa", "Moutarde", "Papier Kraft"],
        "variantes": [
            {"titre": "Portion Kraft 500g", "sous_titre": "Pour 1 gourmand avec oignons", "surcout_prix": 0.00, "est_requis": True, "ordre": 1},
            {"titre": "Portion Kraft 1kg Familiale", "sous_titre": "Pour 2 à 3 personnes", "surcout_prix": 5000.00, "est_requis": False, "ordre": 2},
        ],
        "options": [
            {"type_option": OptionProduit.TYPE_SAUCE, "titre": "Moutarde Forte & Oignons Caramel", "sous_titre": "Sauce oignons moutardée", "surcout_prix": 300.00, "est_inclus": True, "ordre": 1},
            {"type_option": OptionProduit.TYPE_SUPPLEMENT, "titre": "Extra Kankankan (Piment Haoussa)", "sous_titre": "Épice pimentée séchée", "surcout_prix": 200.00, "est_inclus": False, "ordre": 2},
        ]
    },
    {
        "etablissement_nom": "Dibi Chez Samba",
        "nom": "Dibi Agneau Traditionnel aux Oignons & Bananes Alloco",
        "description": "Viande d'agneau fraîche grillée à la perfection sur braises chaudes, nappée de moutarde forte, accompagnée d'oignons croquants et de bananes plantain Alloco frites dorées.",
        "prix_base": 5000.00,
        "image_url": "http://127.0.0.1:8000/media/dishes/dibi_agneau_chez_samba.png",
        "temps_preparation": "15-20 min",
        "tags": ["Dibi Agneau", "Chez Samba", "Alloco", "Moutarde", "Braises"],
        "variantes": [
            {"titre": "Plat Dibi Agneau + Alloco", "sous_titre": "Agneau braisé & portion bananes frites", "surcout_prix": 0.00, "est_requis": True, "ordre": 1},
            {"titre": "Grand Plat Dibi Duo", "sous_titre": "Portion XL pour 2 personnes", "surcout_prix": 4000.00, "est_requis": False, "ordre": 2},
        ],
        "options": [
            {"type_option": OptionProduit.TYPE_SAUCE, "titre": "Moutarde Amora & Piment vert", "sous_titre": "Accompagnement traditionnel", "surcout_prix": 200.00, "est_inclus": True, "ordre": 1},
            {"type_option": OptionProduit.TYPE_SUPPLEMENT, "titre": "Supplément Bananes Alloco", "sous_titre": "Barquette bananes frites", "surcout_prix": 1000.00, "est_inclus": False, "ordre": 2},
        ]
    },
    {
        "etablissement_nom": "Le Grill du Sahel",
        "nom": "Dibi Agneau Spécial aux Oignons Rouges & Piments Colorés",
        "description": "Grillade d'agneau du Sahel assaisonnée de poivre de Selingué et de piment vert-jaune, servie sur plateau avec une pluie d'oignons rouges doux marinés au vinaigre.",
        "prix_base": 6000.00,
        "image_url": "http://127.0.0.1:8000/media/dishes/dibi_agneau_grill_sahel.jpg",
        "temps_preparation": "20-25 min",
        "tags": ["Grill du Sahel", "Dibi Agneau", "Oignons Rouges", "Piments"],
        "variantes": [
            {"titre": "Plateau Grill Sahel 500g", "sous_titre": "Portion agneau aux oignons rouges", "surcout_prix": 0.00, "est_requis": True, "ordre": 1},
            {"titre": "Plateau Sahel 1kg", "sous_titre": "Pour 2-3 personnes", "surcout_prix": 5500.00, "est_requis": False, "ordre": 2},
        ],
        "options": [
            {"type_option": OptionProduit.TYPE_SAUCE, "titre": "Sauce Piment Sahel", "sous_titre": "Sauce piment fort maison", "surcout_prix": 300.00, "est_inclus": True, "ordre": 1},
            {"type_option": OptionProduit.TYPE_SUPPLEMENT, "titre": "Extra Oignons Rouges Vinaigrés", "sous_titre": "Portion oignons marinés", "surcout_prix": 500.00, "est_inclus": False, "ordre": 2},
        ]
    },
    {
        "etablissement_nom": "Teranga Saveurs",
        "nom": "Grand Plateau Dibi Agneau Gourmand, Frites & Baguette",
        "description": "Formule plateau royale : côtelettes d'agneau grillées au feu de bois posées sur lit de salade croquante, servies avec frites dorées croustillantes, demi-baguette chaude et sauce crémeuse.",
        "prix_base": 6500.00,
        "image_url": "http://127.0.0.1:8000/media/dishes/dibi_agneau_teranga.jpg",
        "temps_preparation": "20-25 min",
        "tags": ["Plateau Dibi", "Agneau", "Frites", "Baguette", "Teranga"],
        "variantes": [
            {"titre": "Plateau Individuel Complet", "sous_titre": "Agneau, frites, baguette & salade", "surcout_prix": 0.00, "est_requis": True, "ordre": 1},
            {"titre": "Plateau XL XXL 2 personnes", "sous_titre": "Double portion agneau & frites", "surcout_prix": 5500.00, "est_requis": False, "ordre": 2},
        ],
        "options": [
            {"type_option": OptionProduit.TYPE_SAUCE, "titre": "Sauce Mayonnaise & Ketchup", "sous_titre": "Pour les frites", "surcout_prix": 200.00, "est_inclus": True, "ordre": 1},
            {"type_option": OptionProduit.TYPE_SUPPLEMENT, "titre": "Baguette Chaude Supplémentaire", "sous_titre": "Pain croustillant", "surcout_prix": 300.00, "est_inclus": False, "ordre": 2},
        ]
    }
]

created_count = 0
for d in DIBI_AGNEAU_DISHES:
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
    print(f"OK: Plat Dibi Agneau [{produit.id}] '{produit.nom[:30]}...' cree pour {etab.nom}")

print(f"\nTOTAL PLATS DIBI AGNEAU CREES: {created_count}")
