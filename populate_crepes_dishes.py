import os
import sys
import shutil
import django

sys.path.append('c:\\Users\\HP\\Desktop\\Ayyou-backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.catalog.models import Categorie, Etablissement, Produit, VarianteProduit, OptionProduit

print("==================================================")
print("  POPULATION DES CREPES GOURMANDES (CATEGORIE 17)")
print("==================================================")

# Source images
SOURCE_DIR = r"C:\Users\HP\.gemini\antigravity\brain\1f2cd0a4-e39b-4ef8-b924-e7e0bc2d34a3\.user_uploaded"
DEST_DIR = r"C:\Users\HP\Desktop\Ayyou-backend\media\dishes"

os.makedirs(DEST_DIR, exist_ok=True)

IMAGE_MAPPINGS = {
    "crepe_rouleaux_zebres_vanille_chocolat.jpg": "media_1790509217802.jpg",
    "crepe_rouleaux_nutella_fondant.jpg": "media_1790509232606.jpg",
    "crepe_triangle_nutella_banane.png": "media_1790509244892.png",
    "crepe_supreme_kinder_bueno_glace.jpg": "media_1790509257782.jpg"
}

for dest_name, src_name in IMAGE_MAPPINGS.items():
    src_path = os.path.join(SOURCE_DIR, src_name)
    dest_path = os.path.join(DEST_DIR, dest_name)
    if os.path.exists(src_path):
        shutil.copy(src_path, dest_path)
        print(f"Copied {src_name} -> {dest_name}")
    else:
        print(f"WARNING: {src_path} not found!")

cat_official = Categorie.objects.get(id=17)
print(f"Categorie officielle: {cat_official.nom} (ID {cat_official.id})")

CREPE_DISHES = [
    {
        "etablissement_nom": "Douceurs de Dakar",
        "nom": "Plateau de Rouleaux de Crêpes Zébrées Vanille & Cacao",
        "description": "Plateau gourmand de rouleaux de crêpes artisanales bicolores zébrées à la vanille et au cacao maigre, servies tièdes sur ardoise noire avec sirop de chocolat.",
        "prix_base": 2500.00,
        "image_url": "http://127.0.0.1:8000/media/dishes/crepe_rouleaux_zebres_vanille_chocolat.jpg",
        "temps_preparation": "10-15 min",
        "tags": ["Crêpes Zébrées", "Douceurs de Dakar", "Pâte Artisanal", "Chocolat & Vanille"],
        "variantes": [
            {"titre": "Assiette 3 Rouleaux Zébrés", "sous_titre": "3 rouleaux tièdes vanille-chocolat", "surcout_prix": 0.00, "est_requis": True, "ordre": 1},
            {"titre": "Plateau Maxi 6 Rouleaux", "sous_titre": "6 rouleaux à partager", "surcout_prix": 1800.00, "est_requis": False, "ordre": 2},
        ],
        "options": [
            {"type_option": OptionProduit.TYPE_SUPPLEMENT, "titre": "Nappage Sucre Glace & Beurre", "sous_titre": "Finition classique", "surcout_prix": 100.00, "est_inclus": True, "ordre": 1},
            {"type_option": OptionProduit.TYPE_SUPPLEMENT, "titre": "Supplément Nutella Chaud", "sous_titre": "Nutella fondu", "surcout_prix": 300.00, "est_inclus": False, "ordre": 2},
        ]
    },
    {
        "etablissement_nom": "Glaces Dakar",
        "nom": "Rouleaux de Crêpes Moelleuses Cœur Généreux Nutella",
        "description": "Crêpes ultra moelleuses roulées et fourrées à cœur de véritable Nutella fondu coulant, nappées de zébrures de chocolat noir sur planche en bois.",
        "prix_base": 2800.00,
        "image_url": "http://127.0.0.1:8000/media/dishes/crepe_rouleaux_nutella_fondant.jpg",
        "temps_preparation": "10-15 min",
        "tags": ["Crêpe Nutella", "Glaces Dakar", "Gourmand", "Fondant", "Cœur Coulant"],
        "variantes": [
            {"titre": "Portion 3 Rouleaux Nutella", "sous_titre": "3 crêpes roulées au Nutella", "surcout_prix": 0.00, "est_requis": True, "ordre": 1},
            {"titre": "Portion XL 5 Rouleaux Nutella", "sous_titre": "5 crêpes roulées pour grands gourmands", "surcout_prix": 1500.00, "est_requis": False, "ordre": 2},
        ],
        "options": [
            {"type_option": OptionProduit.TYPE_SUPPLEMENT, "titre": "Boule de Glace Vanille", "sous_titre": "Boule de glace artisanale", "surcout_prix": 400.00, "est_inclus": False, "ordre": 1},
            {"type_option": OptionProduit.TYPE_SUPPLEMENT, "titre": "Chantilly Maison", "sous_titre": "Crème chantilly", "surcout_prix": 250.00, "est_inclus": False, "ordre": 2},
        ]
    },
    {
        "etablissement_nom": "Teranga Saveurs",
        "nom": "Crêpe Triangle Nappée Nutella & Bananes Fraîches",
        "description": "Grand classique de la crêperie : grande crêpe bretonne pliée en triangle, nappée d'une pluie de traits de Nutella chaud et surmontée de rondelles de banane fraîche.",
        "prix_base": 3000.00,
        "image_url": "http://127.0.0.1:8000/media/dishes/crepe_triangle_nutella_banane.png",
        "temps_preparation": "10-15 min",
        "tags": ["Crêpe Banane Nutella", "Teranga Saveurs", "Triangle", "Fruits Frais"],
        "variantes": [
            {"titre": "Crêpe Triangle Nutella-Banane", "sous_titre": "Pliée en triangle avec bananes fraîches", "surcout_prix": 0.00, "est_requis": True, "ordre": 1},
            {"titre": "Double Crêpe Triangle", "sous_titre": "Deux grandes crêpes Nutella-banane", "surcout_prix": 2200.00, "est_requis": False, "ordre": 2},
        ],
        "options": [
            {"type_option": OptionProduit.TYPE_SUPPLEMENT, "titre": "Extra Fraises Fraîches", "sous_titre": "Lamelles de fraises", "surcout_prix": 300.00, "est_inclus": False, "ordre": 1},
            {"type_option": OptionProduit.TYPE_SUPPLEMENT, "titre": "Éclats de Noisettes Grillées", "sous_titre": "Noisettes concassées", "surcout_prix": 200.00, "est_inclus": False, "ordre": 2},
        ]
    },
    {
        "etablissement_nom": "Chez Penda",
        "nom": "Crêpe Suprême Kinder Bueno, Glace Vanille & Chantilly",
        "description": "Dessert d'exception : grande crêpe fourrée au Nutella, surmontée de morceaux de Kinder Bueno croustillants, d'une boule de glace vanille, crème chantilly & framboises.",
        "prix_base": 3800.00,
        "image_url": "http://127.0.0.1:8000/media/dishes/crepe_supreme_kinder_bueno_glace.jpg",
        "temps_preparation": "10-15 min",
        "tags": ["Crêpe Suprême", "Kinder Bueno", "Chez Penda", "Glace Vanille", "Luxe"],
        "variantes": [
            {"titre": "Crêpe Suprême Kinder Bueno", "sous_titre": "Nutella, Kinder Bueno, glace & chantilly", "surcout_prix": 0.00, "est_requis": True, "ordre": 1},
            {"titre": "Crêpe Suprême XXL 2 Kinder Bueno", "sous_titre": "Double Kinder Bueno & 2 boules de glace", "surcout_prix": 1800.00, "est_requis": False, "ordre": 2},
        ],
        "options": [
            {"type_option": OptionProduit.TYPE_SUPPLEMENT, "titre": "Sauce Chocolat Chaud Extra", "sous_titre": "Chocolat noir coulant", "surcout_prix": 300.00, "est_inclus": True, "ordre": 1},
        ]
    }
]

created_count = 0
for d in CREPE_DISHES:
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
    print(f"OK: Plat Crêpe Gourmande [{produit.id}] '{produit.nom[:30]}...' cree pour {etab.nom}")

print(f"\nTOTAL PLATS CREPES GOURMANDES CREES: {created_count}")
