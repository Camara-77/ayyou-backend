import os
import sys
import shutil
import django

sys.path.append('c:\\Users\\HP\\Desktop\\Ayyou-backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.catalog.models import Categorie, Etablissement, Produit, VarianteProduit, OptionProduit

print("==================================================")
print("  POPULATION DES JUS DE BOUYE (CATEGORIE 11)")
print("==================================================")

# Source images
SOURCE_DIR = r"C:\Users\HP\.gemini\antigravity\brain\1f2cd0a4-e39b-4ef8-b924-e7e0bc2d34a3\.user_uploaded"
DEST_DIR = r"C:\Users\HP\Desktop\Ayyou-backend\media\dishes"

os.makedirs(DEST_DIR, exist_ok=True)

IMAGE_MAPPINGS = {
    "bouye_fraise_paille.jpg": "media_1790502861158.jpg",
    "bouye_cannelle_lait.png": "media_1790502877040.png",
    "bouye_calebasse_tradition.png": "media_1790502886290.png",
    "bouye_verres_givre_pain_singe.jpg": "media_1790502915823.jpg"
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

BOUYE_DISHES = [
    {
        "etablissement_nom": "Jus du Baobab",
        "nom": "Jus de Bouye Crémeux au Lait & Épices Cannelle",
        "description": "Véritable nectar de fruit du Baobab (Pain de Singe) préparé au lait concentré onctueux, parfumé à la cannelle moulue et fleur d'oranger. Un délice gourmand et nutritif.",
        "prix_base": 1500.00,
        "image_url": "http://127.0.0.1:8000/media/dishes/bouye_cannelle_lait.png",
        "temps_preparation": "05 min",
        "tags": ["Bouye", "Baobab", "Lait Concentré", "Cannelle", "Jus du Baobab"],
        "variantes": [
            {"titre": "Grand Verre Bouye 33cl", "sous_titre": "Nectar de baobab au lait & cannelle", "surcout_prix": 0.00, "est_requis": True, "ordre": 1},
            {"titre": "Bouteille 1 Litre", "sous_titre": "Pour déguster en famille (1L)", "surcout_prix": 2000.00, "est_requis": False, "ordre": 2},
        ],
        "options": [
            {"type_option": OptionProduit.TYPE_SUPPLEMENT, "titre": "Extra Fleur d'Oranger", "sous_titre": "Parfum oriental délicat", "surcout_prix": 100.00, "est_inclus": True, "ordre": 1},
            {"type_option": OptionProduit.TYPE_SUPPLEMENT, "titre": "Supplément Lait de Coco", "sous_titre": "Au lait de coco frais", "surcout_prix": 300.00, "est_inclus": False, "ordre": 2},
        ]
    },
    {
        "etablissement_nom": "Teranga Saveurs",
        "nom": "Jus de Bouye Traditionnel servi en Calebasse & Louche Bois",
        "description": "Service authentique du terroir : jus de pain de singe naturel battu à la louche en calebasse avec gros glaçons, sucre de canne pur et zeste de vanille naturelle.",
        "prix_base": 1800.00,
        "image_url": "http://127.0.0.1:8000/media/dishes/bouye_calebasse_tradition.png",
        "temps_preparation": "05 min",
        "tags": ["Bouye Calebasse", "Teranga", "Tradition", "Baobab", "Glaçons"],
        "variantes": [
            {"titre": "Calebasse Individuelle", "sous_titre": "Servie fraîche avec louche", "surcout_prix": 0.00, "est_requis": True, "ordre": 1},
            {"titre": "Grande Calebasse de Table", "sous_titre": "Service traditionnel pour 3 personnes", "surcout_prix": 3000.00, "est_requis": False, "ordre": 2},
        ],
        "options": [
            {"type_option": OptionProduit.TYPE_SUPPLEMENT, "titre": "Glaçons Supplémentaires", "sous_titre": "Accompagnement fraîcheur", "surcout_prix": 0.00, "est_inclus": True, "ordre": 1},
        ]
    },
    {
        "etablissement_nom": "Fruits Frais Dakar",
        "nom": "Smoothie Bouye Cocktail Nectar & Fraise Fraîche",
        "description": "Création fruitée originale : jus de baobab velouté servi dans un verre élégant avec paille et fraise fraîche parfumée posée en garniture.",
        "prix_base": 1600.00,
        "image_url": "http://127.0.0.1:8000/media/dishes/bouye_fraise_paille.jpg",
        "temps_preparation": "05 min",
        "tags": ["Bouye Fraise", "Smoothie", "Fruits Frais", "Gourmand"],
        "variantes": [
            {"titre": "Verre Cocktail Bouye 35cl", "sous_titre": "Avec fraise fraîche & paille", "surcout_prix": 0.00, "est_requis": True, "ordre": 1},
            {"titre": "Format Maxi XL 50cl", "sous_titre": "Grand verre gourmand", "surcout_prix": 800.00, "est_requis": False, "ordre": 2},
        ],
        "options": [
            {"type_option": OptionProduit.TYPE_SUPPLEMENT, "titre": "Nappage Coulis de Fraise", "sous_titre": "Extra coulis gourmand", "surcout_prix": 200.00, "est_inclus": False, "ordre": 1},
        ]
    },
    {
        "etablissement_nom": "Jus Chez Fatou",
        "nom": "Duo de Verres Bouye Givrés au Sucre & Pain de Singe Bio",
        "description": "Deux verres de jus de bouye faits maison au bord givré au sucre roux, présentés sur sous-plat traditionnel entouré de vraies pépites de pain de singe bio.",
        "prix_base": 1400.00,
        "image_url": "http://127.0.0.1:8000/media/dishes/bouye_verres_givre_pain_singe.jpg",
        "temps_preparation": "05 min",
        "tags": ["Jus Chez Fatou", "Bouye Bio", "Pain de Singe", "Givré"],
        "variantes": [
            {"titre": "Verre Givré 30cl", "sous_titre": "Servi avec bordure sucrée", "surcout_prix": 0.00, "est_requis": True, "ordre": 1},
            {"titre": "Duo 2 Verres Givrés", "sous_titre": "Pack 2 verres rafraîchissants", "surcout_prix": 1200.00, "est_requis": False, "ordre": 2},
        ],
        "options": [
            {"type_option": OptionProduit.TYPE_SUPPLEMENT, "titre": "Touche de Sirop de Banane", "sous_titre": "Subtil parfum banane", "surcout_prix": 150.00, "est_inclus": False, "ordre": 1},
        ]
    }
]

created_count = 0
for d in BOUYE_DISHES:
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
    print(f"OK: Produit Jus de Bouye [{produit.id}] '{produit.nom[:30]}...' cree pour {etab.nom}")

print(f"\nTOTAL PRODUITS JUS DE BOUYE CREES: {created_count}")
