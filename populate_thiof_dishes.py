import os
import sys
import shutil
import django

sys.path.append('c:\\Users\\HP\\Desktop\\Ayyou-backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.catalog.models import Categorie, Etablissement, Produit, VarianteProduit, OptionProduit

print("==================================================")
print("  POPULATION DES THIOFS GRILLES (CATEGORIE 12)")
print("==================================================")

# Source images
SOURCE_DIR = r"C:\Users\HP\.gemini\antigravity\brain\1f2cd0a4-e39b-4ef8-b924-e7e0bc2d34a3\.user_uploaded"
DEST_DIR = r"C:\Users\HP\Desktop\Ayyou-backend\media\dishes"

os.makedirs(DEST_DIR, exist_ok=True)

IMAGE_MAPPINGS = {
    "thiof_grille_epices_aubergines.jpg": "media_1790503279849.jpg",
    "thiof_grille_citron_salade.jpg": "media_1790503313862.jpg",
    "thiof_grille_attieke_ardoise.png": "media_1790503335249.png",
    "thiof_frit_aloco_sauce.jpg": "media_1790503354196.jpg"
}

for dest_name, src_name in IMAGE_MAPPINGS.items():
    src_path = os.path.join(SOURCE_DIR, src_name)
    dest_path = os.path.join(DEST_DIR, dest_name)
    if os.path.exists(src_path):
        shutil.copy(src_path, dest_path)
        print(f"Copied {src_name} -> {dest_name}")
    else:
        print(f"WARNING: {src_path} not found!")

cat_official = Categorie.objects.get(id=12)
print(f"Categorie officielle: {cat_official.nom} (ID {cat_official.id})")

THIOF_DISHES = [
    {
        "etablissement_nom": "Le Poisson de Dakar",
        "nom": "Mérou Thiof Entier Braisé aux Épices & Aubergines Africaines",
        "description": "Thiof (Mérou blanc royal) entier fraîchement pêché, marinée à la persillade d'ail et piment sec, braisé au four avec incisures. Servi garni d'aubergines violets étuvées, oignons et sauces maison.",
        "prix_base": 7500.00,
        "image_url": "http://127.0.0.1:8000/media/dishes/thiof_grille_epices_aubergines.jpg",
        "temps_preparation": "25-30 min",
        "tags": ["Thiof Royal", "Mérou Entier", "Braisé au Four", "Le Poisson de Dakar", "Aubergines"],
        "variantes": [
            {"titre": "Thiof Moyen (800g)", "sous_titre": "Pour 1-2 personnes avec garniture", "surcout_prix": 0.00, "est_requis": True, "ordre": 1},
            {"titre": "Thiof Géant (1.2kg)", "sous_titre": "Grand poisson royal pour 2-3 personnes", "surcout_prix": 4500.00, "est_requis": False, "ordre": 2},
        ],
        "options": [
            {"type_option": OptionProduit.TYPE_SAUCE, "titre": "Sauce Oignon Vinaigrée", "sous_titre": "Accompagnement traditionnel", "surcout_prix": 300.00, "est_inclus": True, "ordre": 1},
            {"type_option": OptionProduit.TYPE_SUPPLEMENT, "titre": "Portion de Frites Maison", "sous_titre": "Frites croustillantes", "surcout_prix": 1000.00, "est_inclus": False, "ordre": 2},
        ]
    },
    {
        "etablissement_nom": "Poisson Frais Chez Ali",
        "nom": "Duo de Thiofs Grillés au Citron Vert & Salade Fraîche",
        "description": "Deux poissons Thiof entiers grillés aux rondelles de citron vert et herbes de Provence, servis sur un lit de salade croquante garnie de concombres et sauce tomate mijotée.",
        "prix_base": 6800.00,
        "image_url": "http://127.0.0.1:8000/media/dishes/thiof_grille_citron_salade.jpg",
        "temps_preparation": "20-25 min",
        "tags": ["Duo Thiof", "Chez Ali", "Citron Vert", "Salade Fraîche", "Grillé"],
        "variantes": [
            {"titre": "Plat Duo Thiof Grillé", "sous_titre": "2 poissons Thiof avec salade & sauce", "surcout_prix": 0.00, "est_requis": True, "ordre": 1},
            {"titre": "Formule XL Trio Thiof", "sous_titre": "3 poissons grillés pour partager", "surcout_prix": 3500.00, "est_requis": False, "ordre": 2},
        ],
        "options": [
            {"type_option": OptionProduit.TYPE_SAUCE, "titre": "Sauce Tomate Pimentée", "sous_titre": "Sauce tomate maison aux épices", "surcout_prix": 200.00, "est_inclus": True, "ordre": 1},
            {"type_option": OptionProduit.TYPE_SUPPLEMENT, "titre": "Extra Rondelles de Citron", "sous_titre": "Citrons verts frais", "surcout_prix": 100.00, "est_inclus": False, "ordre": 2},
        ]
    },
    {
        "etablissement_nom": "Saveurs de Ndar",
        "nom": "Thiof Grillé Prestige sur Ardoise & Dôme d'Attiéké",
        "description": "Présentation gastronomique de Saint-Louis : poisson Thiof braisé au charbon avec croûte croustillante, servi sur plaque d'ardoise noire avec dôme d'Attiéké vapeur et beurré au citron.",
        "prix_base": 8000.00,
        "image_url": "http://127.0.0.1:8000/media/dishes/thiof_grille_attieke_ardoise.png",
        "temps_preparation": "25-30 min",
        "tags": ["Thiof Prestige", "Saveurs de Ndar", "Attiéké", "Ardoise", "Beurre Citron"],
        "variantes": [
            {"titre": "Assiette Thiof & Attiéké", "sous_titre": "Thiof braisé sur ardoise avec dôme d'attiéké", "surcout_prix": 0.00, "est_requis": True, "ordre": 1},
            {"titre": "Format Royal Saint-Louis", "sous_titre": "Thiof XXL avec double portion d'attiéké", "surcout_prix": 4000.00, "est_requis": False, "ordre": 2},
        ],
        "options": [
            {"type_option": OptionProduit.TYPE_SAUCE, "titre": "Sauce Beurre-Citron & Ail", "sous_titre": "Sauce onctueuse pour poisson", "surcout_prix": 400.00, "est_inclus": True, "ordre": 1},
            {"type_option": OptionProduit.TYPE_SUPPLEMENT, "titre": "Extra Dôme d'Attiéké", "sous_titre": "Portion d'attiéké au beurre", "surcout_prix": 1000.00, "est_inclus": False, "ordre": 2},
        ]
    },
    {
        "etablissement_nom": "Teranga Saveurs",
        "nom": "Thiof Croustillant Frit aux Bananes Alloco & Piment Rouge",
        "description": "Poisson Thiof entier mariné à la sénégalaise et frit à la perfection dorée et croustillante, servi avec de généreuses rondelles de bananes Alloco frites et ramequin de sauce piquante.",
        "prix_base": 7200.00,
        "image_url": "http://127.0.0.1:8000/media/dishes/thiof_frit_aloco_sauce.jpg",
        "temps_preparation": "20-25 min",
        "tags": ["Thiof Frit", "Alloco", "Teranga Saveurs", "Piment Rouge", "Croustillant"],
        "variantes": [
            {"titre": "Thiof Frit + Alloco Standard", "sous_titre": "Thiof frit entiers & bananes frites", "surcout_prix": 0.00, "est_requis": True, "ordre": 1},
            {"titre": "Plat Thiof Frit Familial", "sous_titre": "Grand format avec extra Alloco", "surcout_prix": 3800.00, "est_requis": False, "ordre": 2},
        ],
        "options": [
            {"type_option": OptionProduit.TYPE_SAUCE, "titre": "Sauce Piment Végétalien", "sous_titre": "Piment pilé rouge", "surcout_prix": 200.00, "est_inclus": True, "ordre": 1},
            {"type_option": OptionProduit.TYPE_SUPPLEMENT, "titre": "Portion Bananes Alloco Extra", "sous_titre": "Supplément bananes frites", "surcout_prix": 1000.00, "est_inclus": False, "ordre": 2},
        ]
    }
]

created_count = 0
for d in THIOF_DISHES:
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
    print(f"OK: Plat Thiof Grillé [{produit.id}] '{produit.nom[:30]}...' cree pour {etab.nom}")

print(f"\nTOTAL PLATS THIOF GRILLE CREES: {created_count}")
